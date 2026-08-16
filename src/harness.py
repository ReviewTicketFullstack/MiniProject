"""Main harness orchestrator for change drills."""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

from .worktree import Worktree, WorktreeError
from .measurement import (
    ExperimentEvidence,
    ChangeCost,
    FileDiff,
    parse_diff,
    run_verification,
)
from .report import save_experiment_results


class Harness:
    """Orchestrates a complete change drill experiment."""

    def __init__(
        self,
        repo_path: str,
        scenario_id: str,
        scenario_name: str,
        results_dir: str = "results",
    ):
        """
        Initialize the harness.

        Args:
            repo_path: Path to target repository
            scenario_id: Unique scenario identifier
            scenario_name: Human-readable scenario name
            results_dir: Directory to store results
        """
        self.repo_path = Path(repo_path).resolve()
        self.scenario_id = scenario_id
        self.scenario_name = scenario_name
        self.results_dir = Path(results_dir).resolve()
        self.worktree: Optional[Worktree] = None
        self.base_commit: Optional[str] = None
        self.evidence: Optional[ExperimentEvidence] = None

    def setup(self) -> Dict[str, Any]:
        """
        Set up the worktree without running verification/measurement.

        Called before Coding Agent makes changes. Returns worktree path.

        Returns:
            Dictionary with setup status and worktree_path
        """
        try:
            print(f"Setting up experiment: {self.scenario_id}")
            print(f"Repository: {self.repo_path}")
            print(f"Scenario: {self.scenario_name}")
            print("")

            self.worktree = Worktree(str(self.repo_path), self.scenario_id)
            self.worktree.validate_repo()
            self.base_commit = self.worktree.get_base_commit()

            print(f"Base commit: {self.base_commit[:8]}")
            print(f"Creating worktree...")

            self.worktree.create()
            print(f"✓ Worktree ready at: {self.worktree.worktree_path}")
            print("")
            print("Awaiting Coding Agent to make changes...")
            print("")

            return {
                "status": "setup_complete",
                "worktree_path": str(self.worktree.worktree_path),
                "base_commit": self.base_commit,
            }

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

    def measure_and_report(self) -> Dict[str, Any]:
        """
        Measure changes and generate report.

        Called after Coding Agent has made changes in the worktree.
        Expects self.worktree and self.base_commit to be set.

        Returns:
            Dictionary with measurement and reporting results
        """
        if not self.worktree or not self.base_commit:
            return {
                "status": "error",
                "error": "Harness not properly initialized. Call setup() first.",
            }

        try:
            print("Measuring changes...")
            timestamp = datetime.now().isoformat()

            git_status = self.worktree.get_status()
            diff = self.worktree.get_diff(self.base_commit)

            if not diff.strip():
                print("⚠ No changes detected in worktree")

            print("Running verification...")
            verification = run_verification(self.worktree.worktree_path, self.repo_path)

            print(f"Build: {'✓' if verification.build_success else '✗'}")
            print(f"Tests: {'✓' if verification.test_success else '✗'}")
            print("")

            completed = verification.build_success and verification.test_success

            change_cost = parse_diff(diff) if diff.strip() else ChangeCost(
                total_files_changed=0,
                total_lines_added=0,
                total_lines_deleted=0,
                files_changed_list=[],
                test_files_changed=0,
                unrelated_files_modified=0,
            )

            evidence = ExperimentEvidence(
                scenario_id=self.scenario_id,
                scenario_name=self.scenario_name,
                timestamp=timestamp,
                base_commit=self.base_commit,
                completed=completed,
                change_cost=change_cost,
                verification=verification,
                diff=diff,
                git_status=git_status,
            )

            print("Saving results...")
            json_path, md_path, diff_path = save_experiment_results(
                evidence, diff, self.results_dir
            )

            print(f"Results saved:")
            print(f"  JSON: {json_path}")
            print(f"  Markdown: {md_path}")
            print(f"  Diff: {diff_path}")
            print("")

            print("Cleaning up worktree...")
            if self.worktree.cleanup():
                print("✓ Worktree cleaned up")
            else:
                print("⚠ Worktree cleanup had warnings (but experiment completed)")

            return {
                "status": "success",
                "scenario_id": self.scenario_id,
                "completed": completed,
                "files_changed": change_cost.total_files_changed,
                "lines_added": change_cost.total_lines_added,
                "lines_deleted": change_cost.total_lines_deleted,
                "build_success": verification.build_success,
                "test_success": verification.test_success,
                "results_json": str(json_path),
                "results_markdown": str(md_path),
                "results_diff": str(diff_path),
            }

        except Exception as e:
            print(f"✗ Error during measurement: {e}")
            import traceback
            traceback.print_exc()
            if self.worktree:
                self.worktree.cleanup()
            return {
                "status": "error",
                "error": str(e),
            }

    def run(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        Execute a complete change drill.

        Args:
            dry_run: If True, only validate setup, don't run the experiment

        Returns:
            Dictionary with result summary
        """
        try:
            print(f"Setting up experiment: {self.scenario_id}")
            print(f"Repository: {self.repo_path}")
            print(f"Scenario: {self.scenario_name}")
            print("")

            worktree = Worktree(str(self.repo_path), self.scenario_id)
            worktree.validate_repo()
            base_commit = worktree.get_base_commit()

            print(f"Base commit: {base_commit[:8]}")
            print(f"Creating worktree...")

            worktree.create()
            print(f"Worktree created: {worktree.worktree_path}")
            print("")

            if dry_run:
                print("[DRY RUN] Would execute change in worktree")
                worktree.cleanup()
                return {
                    "status": "dry_run_success",
                    "message": "Worktree setup validated",
                }

            print("Ready for coding agent to make changes in worktree.")
            print(f"Worktree path: {worktree.worktree_path}")
            print("")

            timestamp = datetime.now().isoformat()

            git_status = worktree.get_status()
            diff = worktree.get_diff(base_commit)

            print("Running verification...")
            verification = run_verification(worktree.worktree_path, self.repo_path)

            print(f"Build: {'✓' if verification.build_success else '✗'}")
            print(f"Tests: {'✓' if verification.test_success else '✗'}")
            print("")

            completed = verification.build_success and verification.test_success

            change_cost = parse_diff(diff) if diff.strip() else ChangeCost(
                total_files_changed=0,
                total_lines_added=0,
                total_lines_deleted=0,
                files_changed_list=[],
                test_files_changed=0,
                unrelated_files_modified=0,
            )

            self.evidence = ExperimentEvidence(
                scenario_id=self.scenario_id,
                scenario_name=self.scenario_name,
                timestamp=timestamp,
                base_commit=base_commit,
                completed=completed,
                change_cost=change_cost,
                verification=verification,
                diff=diff,
                git_status=git_status,
            )

            print("Saving results...")
            json_path, md_path, diff_path = save_experiment_results(
                self.evidence, diff, self.results_dir
            )

            print(f"Results saved:")
            print(f"  JSON: {json_path}")
            print(f"  Markdown: {md_path}")
            print(f"  Diff: {diff_path}")
            print("")

            print("Cleaning up worktree...")
            if worktree.cleanup():
                print("✓ Worktree cleaned up")
            else:
                print("⚠ Worktree cleanup had warnings (but experiment completed)")

            return {
                "status": "success",
                "scenario_id": self.scenario_id,
                "completed": completed,
                "files_changed": change_cost.total_files_changed,
                "lines_added": change_cost.total_lines_added,
                "lines_deleted": change_cost.total_lines_deleted,
                "build_success": verification.build_success,
                "test_success": verification.test_success,
                "results_json": str(json_path),
                "results_markdown": str(md_path),
                "results_diff": str(diff_path),
            }

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
