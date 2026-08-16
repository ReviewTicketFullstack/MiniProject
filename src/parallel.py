"""Parallel change drill orchestration for multiple agents."""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

from .worktree import Worktree, WorktreeError
from .measurement import parse_diff, run_verification, ExperimentEvidence
from .report import save_experiment_results
from .analysis import (
    ExperimentAnalyzer,
    AgentMetrics,
    ComparisonReportGenerator,
)


class ParallelDrill:
    """Orchestrates parallel change drills with multiple agents."""

    def __init__(
        self,
        repo_path: str,
        scenario_id: str,
        scenario_name: str,
        scenario_prompt: str,
        num_agents: int = 2,
        results_dir: str = "results",
    ):
        """
        Initialize parallel drill coordinator.

        Args:
            repo_path: Target repository path
            scenario_id: Scenario identifier
            scenario_name: Scenario name
            scenario_prompt: Full scenario prompt for agents
            num_agents: Number of concurrent agents (default 2)
            results_dir: Results directory
        """
        self.repo_path = Path(repo_path).resolve()
        self.scenario_id = scenario_id
        self.scenario_name = scenario_name
        self.scenario_prompt = scenario_prompt
        self.num_agents = num_agents
        self.results_dir = Path(results_dir).resolve()

        self.worktrees: Dict[str, Worktree] = {}
        self.base_commit: Optional[str] = None
        self.agent_results: Dict[str, Dict[str, Any]] = {}

    def setup_worktrees(self) -> Dict[str, Any]:
        """
        Create isolated worktrees for each agent.

        Returns:
            Dictionary with setup info for all agents
        """
        try:
            print(f"Setting up parallel drill: {self.scenario_id}")
            print(f"Repository: {self.repo_path}")
            print(f"Agents: {self.num_agents}")
            print("")

            # Create first worktree to establish base commit
            agent_0 = Worktree(str(self.repo_path), f"{self.scenario_id}-0")
            agent_0.validate_repo()
            self.base_commit = agent_0.get_base_commit()

            print(f"Base commit: {self.base_commit[:8]}")
            print(f"Creating {self.num_agents} isolated worktrees...")
            print("")

            for i in range(self.num_agents):
                agent_id = chr(65 + i)  # A, B, C, ...
                worktree = Worktree(str(self.repo_path), f"{self.scenario_id}-{i}")
                worktree.create()
                self.worktrees[agent_id] = worktree
                print(f"✓ Agent {agent_id}: {worktree.worktree_path}")

            print("")
            print("All worktrees ready. Awaiting agents...")
            print("")

            # Return setup info for each agent
            setup_info = {
                "status": "setup_complete",
                "base_commit": self.base_commit,
                "agents": {},
            }

            for agent_id, worktree in self.worktrees.items():
                setup_info["agents"][agent_id] = {
                    "id": agent_id,
                    "worktree_path": str(worktree.worktree_path),
                    "scenario_prompt": self.scenario_prompt,
                }

            return setup_info

        except WorktreeError as e:
            print(f"✗ Worktree error: {e}")
            return {
                "status": "worktree_error",
                "error": str(e),
            }
        except Exception as e:
            print(f"✗ Unexpected error: {e}")
            import traceback

            traceback.print_exc()
            return {
                "status": "error",
                "error": str(e),
            }

    def record_agent_completion(self, agent_id: str, completion_data: Dict[str, Any]) -> None:
        """
        Record that an agent has completed its work.

        Args:
            agent_id: Agent identifier (A, B, C, ...)
            completion_data: Data from agent (e.g., files modified count)
        """
        self.agent_results[agent_id] = completion_data
        print(f"Agent {agent_id} completion recorded")

    def measure_all(self) -> Dict[str, Any]:
        """
        Measure results for all agents.

        Returns:
            Combined results dictionary
        """
        if not self.worktrees or not self.base_commit:
            return {
                "status": "error",
                "error": "Harness not properly initialized. Call setup_worktrees() first.",
            }

        try:
            print("Measuring all agent results...")
            print("")

            timestamp = datetime.now().isoformat()
            all_evidence = {}

            for agent_id, worktree in self.worktrees.items():
                print(f"Measuring Agent {agent_id}...")

                git_status = worktree.get_status()
                diff = worktree.get_diff(self.base_commit)

                verification = run_verification(worktree.worktree_path, self.repo_path)

                completed = verification.build_success and verification.test_success

                change_cost = parse_diff(diff) if diff.strip() else None

                if change_cost:
                    print(
                        f"  Files: {change_cost.total_files_changed}, "
                        f"Lines: +{change_cost.total_lines_added}"
                    )
                else:
                    print("  No changes detected")

                print(f"  Build: {'✓' if verification.build_success else '✗'}")
                print(f"  Tests: {'✓' if verification.test_success else '✗'}")

                evidence = ExperimentEvidence(
                    scenario_id=self.scenario_id,
                    scenario_name=self.scenario_name,
                    timestamp=timestamp,
                    base_commit=self.base_commit,
                    completed=completed,
                    change_cost=change_cost
                    or {
                        "total_files_changed": 0,
                        "total_lines_added": 0,
                        "total_lines_deleted": 0,
                        "files_changed_list": [],
                        "test_files_changed": 0,
                        "unrelated_files_modified": 0,
                    },
                    verification=verification,
                    diff=diff,
                    git_status=git_status,
                )

                all_evidence[agent_id] = evidence
                print("")

            print("Saving individual results...")
            for agent_id, evidence in all_evidence.items():
                json_path, md_path, diff_path = save_experiment_results(
                    evidence, evidence.diff, self.results_dir / f"agent_{agent_id}"
                )
                print(f"  Agent {agent_id}: {json_path.parent.name}")

            print("")
            print("Analyzing results across agents...")

            # Create comparison analysis
            analyzer = ExperimentAnalyzer(self.scenario_id, self.scenario_name)

            for agent_id, evidence in all_evidence.items():
                metrics = AgentMetrics(
                    agent_id=agent_id,
                    files_changed=evidence.change_cost.total_files_changed
                    if evidence.change_cost
                    else 0,
                    lines_added=evidence.change_cost.total_lines_added
                    if evidence.change_cost
                    else 0,
                    lines_deleted=evidence.change_cost.total_lines_deleted
                    if evidence.change_cost
                    else 0,
                    test_files_changed=evidence.change_cost.test_files_changed
                    if evidence.change_cost
                    else 0,
                    build_success=evidence.verification.build_success,
                    test_success=evidence.verification.test_success,
                    files_list=[f.path for f in evidence.change_cost.files_changed_list]
                    if evidence.change_cost
                    else [],
                    diff=evidence.diff,
                )
                analyzer.add_agent_result(agent_id, metrics)

            comparison = analyzer.analyze()

            # Generate comparison reports
            comparison_md = ComparisonReportGenerator.generate_markdown(comparison)
            comparison_json = ComparisonReportGenerator.generate_json(comparison)

            # Save comparison reports
            comparison_dir = self.results_dir / "comparison"
            comparison_dir.mkdir(parents=True, exist_ok=True)

            comparison_md_path = comparison_dir / f"comparison_{timestamp.replace(':', '-').replace('.', '-')}.md"
            comparison_json_path = comparison_dir / f"comparison_{timestamp.replace(':', '-').replace('.', '-')}.json"

            comparison_md_path.write_text(comparison_md)
            comparison_json_path.write_text(comparison_json)

            print(f"  Comparison: {comparison_md_path.parent.name}/")

            print("")
            print("Cleaning up worktrees...")
            for agent_id, worktree in self.worktrees.items():
                if worktree.cleanup():
                    print(f"✓ Agent {agent_id} cleaned up")
                else:
                    print(f"⚠ Agent {agent_id} cleanup had warnings")

            print("")

            return {
                "status": "success",
                "scenario_id": self.scenario_id,
                "num_agents": self.num_agents,
                "agents": {
                    agent_id: {
                        "id": agent_id,
                        "completed": evidence.completed,
                        "files_changed": evidence.change_cost.total_files_changed
                        if evidence.change_cost
                        else 0,
                        "lines_added": evidence.change_cost.total_lines_added
                        if evidence.change_cost
                        else 0,
                        "lines_deleted": evidence.change_cost.total_lines_deleted
                        if evidence.change_cost
                        else 0,
                        "build_success": evidence.verification.build_success,
                        "test_success": evidence.verification.test_success,
                    }
                    for agent_id, evidence in all_evidence.items()
                },
                "base_commit": self.base_commit,
                "timestamp": timestamp,
                "comparison_markdown": str(comparison_md_path),
                "comparison_json": str(comparison_json_path),
            }

        except Exception as e:
            print(f"✗ Error during measurement: {e}")
            import traceback

            traceback.print_exc()
            for worktree in self.worktrees.values():
                worktree.cleanup()
            return {
                "status": "error",
                "error": str(e),
            }
