#!/usr/bin/env python3

import argparse
import json
import sys
import time
from pathlib import Path

from .harness import Harness

# Polling interval (seconds) while waiting for agent evidence to appear.
EVIDENCE_POLL_INTERVAL = 2.0


def load_agent_predictions(results_dir: Path, scenario_id: str, scenario_name: str):
    from .prediction import AgentPrediction

    predictions = {}
    errors = []

    for agent_dir in sorted(results_dir.glob("agent_*")):
        evidence = agent_dir / f"prediction_{scenario_id}.json"
        if not evidence.exists():
            continue

        try:
            data = json.loads(evidence.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{evidence}: unreadable or malformed JSON ({exc})")
            continue

        agent_id = data.get("agent_id") or agent_dir.name.replace("agent_", "")

        try:
            predictions[agent_id] = AgentPrediction(
                agent_id=agent_id,
                scenario_name=data.get("scenario_name", scenario_name),
                timestamp=data.get("timestamp", ""),
                estimated_files_changed=int(data["estimated_files_changed"]),
                estimated_lines_added=int(data["estimated_lines_added"]),
                estimated_lines_deleted=int(data["estimated_lines_deleted"]),
                estimated_tokens=int(data["estimated_tokens"]),
                implementation_approach=data.get("implementation_approach", ""),
                likely_files=data.get("likely_files", []),
                complexity_level=str(data["complexity_level"]),
                coupling_observations=data.get("coupling_observations", ""),
                duplication_observations=data.get("duplication_observations", ""),
                responsibility_observations=data.get("responsibility_observations", ""),
                changeability_observations=data.get("changeability_observations", ""),
                analysis_notes=data.get("analysis_notes", ""),
            )
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(f"{evidence}: missing or invalid field ({exc})")

    return predictions, errors


def count_agent_evidence(results_dir: Path, scenario_id: str) -> int:
    """이 시나리오에 대해 현재 존재하는 에이전트 근거 파일 수."""
    if not results_dir.exists():
        return 0

    return sum(
        1
        for agent_dir in results_dir.glob("agent_*")
        if (agent_dir / f"prediction_{scenario_id}.json").exists()
    )


def wait_for_agent_evidence(
    results_dir: Path,
    scenario_id: str,
    expect_agents: int,
    timeout: float,
) -> int:
    """에이전트가 근거 JSON을 다 쓸 때까지 대기.

    Blocks until `expect_agents` evidence files exist or `timeout` seconds pass,
    and returns how many were found. Lets the report command be launched right
    after the agents instead of as a separate step a caller can forget.
    """
    deadline = time.monotonic() + timeout
    found = count_agent_evidence(results_dir, scenario_id)

    if found < expect_agents:
        print(
            f"Waiting for agent evidence: {found}/{expect_agents} "
            f"(timeout {int(timeout)}s)",
            file=sys.stderr,
        )

    while found < expect_agents and time.monotonic() < deadline:
        time.sleep(EVIDENCE_POLL_INTERVAL)
        found = count_agent_evidence(results_dir, scenario_id)

    return found


def run_predict_report(
    results_dir: Path,
    scenario_id: str,
    scenario_name: str,
    expect_agents: int = 0,
    wait_timeout: float = 0.0,
) -> int:
    """예측 보고서 렌더링"""
    from .prediction import PredictionOrchestrator
    from .prediction_report import print_prediction_result

    if expect_agents > 0 and wait_timeout > 0:
        found = wait_for_agent_evidence(
            results_dir, scenario_id, expect_agents, wait_timeout
        )
        if found < expect_agents:
            print(
                f"Error: timed out waiting for agent evidence "
                f"({found}/{expect_agents} files under {results_dir})",
                file=sys.stderr,
            )
            return 1

    if not results_dir.exists():
        print(f"Error: results directory not found: {results_dir}", file=sys.stderr)
        return 1

    predictions, errors = load_agent_predictions(results_dir, scenario_id, scenario_name)

    for error in errors:
        print(f"Error: {error}", file=sys.stderr)

    if errors:
        return 1

    if not predictions:
        print(
            f"Error: no prediction evidence for scenario '{scenario_id}' under "
            f"{results_dir} (expected agent_*/prediction_{scenario_id}.json)",
            file=sys.stderr,
        )
        return 1

    orchestrator = PredictionOrchestrator(
        repo_path=str(Path.cwd()),
        scenario_id=scenario_id,
        scenario_name=scenario_name,
        scenario_prompt="",
        num_agents=len(predictions),
        results_dir=str(results_dir),
    )
    orchestrator.predictions = predictions

    print_prediction_result(orchestrator.analyze_predictions(), scenario_name)
    return 0


def confirm_experiment(repo_path: Path, scenario: dict) -> bool:
    """user permission 예측 진행"""
    print("=" * 60)
    print("EXPERIMENT PLAN")
    print("=" * 60)
    print("")
    print(f"Scenario:     {scenario['name']}")
    print(f"ID:           {scenario['id']}")
    print(f"Repository:   {repo_path}")
    print(f"Description:  {scenario['description']}")
    print("")
    print("An isolated Git worktree will be created for this experiment.")
    print("All changes will be in the worktree and will be analyzed.")
    print("The worktree will be cleaned up after the experiment completes.")
    print("")
    print("=" * 60)
    print("")

    response = input("Continue with this experiment? (yes/no): ").strip().lower()
    return response in ("yes", "y")


def main():
    parser = argparse.ArgumentParser(
        description="Execute a controlled change drill experiment"
    )
    parser.add_argument(
        "--repo-path",
        type=Path,
        default=Path.cwd(),
        help="Path to target Git repository (default: current directory)",
    )
    parser.add_argument(
        "--phase",
        type=str,
        choices=["setup", "measure", "full"],
        default="full",
        help="Execution phase: setup (create worktree), measure (run verification), or full (both)",
    )
    parser.add_argument(
        "--worktree-path",
        type=Path,
        help="Path to existing worktree (used with --phase measure)",
    )
    parser.add_argument(
        "--base-commit",
        type=str,
        help="Base commit for measurement (used with --phase measure)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate setup without executing experiment",
    )
    parser.add_argument(
        "--parallel",
        type=int,
        default=2,
        help="Number of parallel agents (1 = single agent, 2+ = parallel mode)",
    )
    parser.add_argument(
        "--scenario-json",
        type=str,
        default=None,
        help="Scenario as JSON string (required; generated from the user's request)",
    )
    parser.add_argument(
        "--predict",
        action="store_true",
        help="Prediction-only mode: validate the repo and prepare read-only agents "
             "(no worktrees, no modifications, no report)",
    )
    parser.add_argument(
        "--predict-report",
        action="store_true",
        help="Render the prediction report from saved agent evidence "
             "(requires --scenario-id; no agents, no worktrees)",
    )
    parser.add_argument(
        "--scenario-id",
        type=str,
        default=None,
        help="Scenario ID whose prediction evidence should be rendered "
             "(used with --predict-report)",
    )
    parser.add_argument(
        "--scenario-name",
        type=str,
        default=None,
        help="Scenario title shown in the prediction report "
             "(used with --predict-report; defaults to the scenario ID)",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=None,
        help="Directory to store results (default: results/ in codeStress repo)",
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="With --predict-report: block until every agent has written its "
             "prediction JSON, then render the report",
    )
    parser.add_argument(
        "--expect-agents",
        type=int,
        default=None,
        help="Number of agent evidence files to wait for "
             "(used with --predict-report --wait; defaults to --parallel)",
    )
    parser.add_argument(
        "--wait-timeout",
        type=float,
        default=600.0,
        help="Seconds to wait for agent evidence before giving up "
             "(used with --predict-report --wait; default: 600)",
    )

    args = parser.parse_args()

    try:
        codestress_root = Path(__file__).parent.parent

        results_dir = args.results_dir or (codestress_root / "results")

        # Report-only mode: render saved evidence. Runs standalone, so it must
        # not touch scenario catalogs, agents, worktrees or the target repo.
        if args.predict_report:
            if not args.scenario_id:
                print(
                    "Error: --predict-report requires --scenario-id",
                    file=sys.stderr,
                )
                return 1

            expect_agents = args.expect_agents if args.expect_agents is not None else args.parallel

            return run_predict_report(
                results_dir=Path(results_dir),
                scenario_id=args.scenario_id,
                scenario_name=args.scenario_name or args.scenario_id,
                expect_agents=expect_agents if args.wait else 0,
                wait_timeout=args.wait_timeout if args.wait else 0.0,
            )

        # Scenarios come from natural-language input only; there is no catalog.
        if not args.scenario_json:
            print(
                "Error: --scenario-json is required "
                "(scenarios are generated from your natural-language request)",
                file=sys.stderr,
            )
            return 1

        try:
            scenario = json.loads(args.scenario_json)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in --scenario-json: {e}", file=sys.stderr)
            return 1

        # 병렬모드 확인 전 예측 전용 모드부터
        if args.predict:
            from .prediction import PredictionOrchestrator

            print("")
            print("PREDICTION MODE")
            print("=" * 60)
            print(f"Scenario: {scenario.get('name', 'Unknown')}")
            print(f"Agents: {args.parallel} (read-only analysis)")
            print("=" * 60)
            print("")

            orchestrator = PredictionOrchestrator(
                repo_path=str(args.repo_path),
                scenario_id=scenario["id"],
                scenario_name=scenario["name"],
                scenario_prompt=scenario.get("prompt", ""),
                num_agents=args.parallel,
                results_dir=str(results_dir),
            )

            # Validate repository
            if not orchestrator.validate_repo():
                return 1

            print("")
            print("Repository validated. Ready for prediction agents.")
            print("")
            print("(Agents will analyze code without modifying anything)")
            print("")

            # Save orchestrator state for skill to use
            state_file = Path(results_dir) / f"prediction_{scenario['id']}_state.json"
            state_file.parent.mkdir(parents=True, exist_ok=True)
            state_file.write_text(json.dumps({
                "scenario_id": scenario["id"],
                "scenario_name": scenario["name"],
                "repo_path": str(args.repo_path),
                "results_dir": str(results_dir),
                "num_agents": args.parallel,
            }))

            print(f"State saved to: {state_file}")
            print("Awaiting agent predictions...")
            print("")
            print("REQUIRED NEXT STEP - launch the agents, then run:")
            print(
                f"  python3 -m src.cli --predict-report --wait"
                f" --results-dir {results_dir}"
                f" --scenario-id {scenario['id']}"
                f" --scenario-name \"{scenario['name']}\""
                f" --expect-agents {args.parallel}"
            )
            print("")
            print("It blocks until every agent's JSON exists, then prints the report.")
            print("")
            return 0

        # Check if parallel mode
        if args.parallel > 1:
            # Parallel mode
            from .parallel import ParallelDrill

            if args.phase in ("setup", "full"):
                if args.phase == "full" and not args.dry_run:
                    if not confirm_experiment(args.repo_path, scenario):
                        print("Experiment cancelled.")
                        return 0
                elif args.dry_run:
                    print("DRY RUN MODE - Skipping confirmation")
                    print()

                print("")
                print(f"Starting parallel experiment with {args.parallel} agents...")
                print("")

                parallel_drill = ParallelDrill(
                    repo_path=str(args.repo_path),
                    scenario_id=scenario["id"],
                    scenario_name=scenario["name"],
                    scenario_prompt=scenario.get("prompt", ""),
                    num_agents=args.parallel,
                    results_dir=str(results_dir),
                )

                if args.phase == "setup":
                    result = parallel_drill.setup_worktrees()
                else:  # full
                    result = parallel_drill.setup_worktrees()
                    if result["status"] == "setup_complete":
                        print(
                            "NOTE: Parallel mode setup complete. Agents must be invoked separately."
                        )
                        print(
                            "Use the skill to invoke agents, then run measure phase."
                        )
                        return 0

            else:  # measure phase
                if not args.worktree_path or not args.base_commit:
                    print("Error: --measure phase requires --worktree-path and --base-commit")
                    return 1

                parallel_drill = ParallelDrill(
                    repo_path=str(args.repo_path),
                    scenario_id=scenario["id"] if scenario else "unknown",
                    scenario_name=scenario["name"] if scenario else "Unknown",
                    scenario_prompt="",
                    num_agents=args.parallel,
                    results_dir=str(results_dir),
                    base_commit=args.base_commit,
                )

                result = parallel_drill.measure_all()

        else:
            # Single-agent mode
            if args.phase in ("setup", "full"):
                # Skip confirmation if running in phase mode (orchestrated by skill)
                # or in dry-run mode
                if args.phase == "full" and not args.dry_run:
                    if not confirm_experiment(args.repo_path, scenario):
                        print("Experiment cancelled.")
                        return 0
                elif args.dry_run:
                    print("DRY RUN MODE - Skipping confirmation")
                    print()

                print("")
                print("Starting experiment...")
                print("")

                harness = Harness(
                    repo_path=str(args.repo_path),
                    scenario_id=scenario["id"],
                    scenario_name=scenario["name"],
                    results_dir=str(results_dir),
                )

                if args.phase == "setup":
                    result = harness.setup()
                else:  # full
                    result = harness.run(dry_run=args.dry_run)
            else:  # measure phase (single-agent)
                if not args.worktree_path or not args.base_commit:
                    print("Error: --measure phase requires --worktree-path and --base-commit")
                    return 1

                harness = Harness(
                    repo_path=str(args.repo_path),
                    scenario_id=scenario["id"] if scenario else "unknown",
                    scenario_name=scenario["name"] if scenario else "Unknown",
                    results_dir=str(results_dir),
                )
                harness.worktree = __import__("src.worktree", fromlist=["Worktree"]).Worktree(
                    str(args.repo_path), scenario["id"] if scenario else "unknown"
                )
                harness.worktree.worktree_path = args.worktree_path
                harness.base_commit = args.base_commit

                result = harness.measure_and_report()

        print("")
        print("=" * 60)
        print("EXPERIMENT COMPLETE")
        print("=" * 60)
        print("")

        if result["status"] in ("success", "dry_run_success", "setup_complete"):
            if result["status"] == "success":
                # Check if parallel or single-agent mode
                if "agents" in result:
                    # Parallel mode
                    print(f"Status:           Completed (parallel mode)")
                    print(f"Scenario:         {result.get('scenario_id', 'unknown')}")
                    print(f"Agents:           {result.get('num_agents', '?')}")
                    print("")
                    for agent_id, agent_result in result.get("agents", {}).items():
                        print(f"Agent {agent_id}:")
                        print(f"  Completed:       {'✓' if agent_result.get('completed') else '✗'}")
                        print(f"  Files changed:   {agent_result.get('files_changed', '?')}")
                        print(f"  Lines added:     {agent_result.get('lines_added', '?')}")
                        print(f"  Build success:   {'✓' if agent_result.get('build_success') else '✗'}")
                        print(f"  Tests passed:    {'✓' if agent_result.get('test_success') else '✗'}")
                    print("")
                    if result.get('comparison_markdown'):
                        print(f"Comparison Report: {result.get('comparison_markdown')}")
                        print(f"Comparison JSON:   {result.get('comparison_json')}")
                else:
                    # Single-agent mode
                    print(f"Status:           Completed")
                    print(f"Files changed:    {result['files_changed']}")
                    print(f"Lines added:      {result['lines_added']}")
                    print(f"Build success:    {'✓' if result['build_success'] else '✗'}")
                    print(f"Tests passed:     {'✓' if result['test_success'] else '✗'}")
                    print("")
                    print(f"Results JSON:     {result['results_json']}")
                    print(f"Results Markdown: {result['results_markdown']}")
                    print(f"Results Diff:     {result['results_diff']}")
            elif result["status"] == "setup_complete":
                if "agents" in result and result["agents"]:
                    # Parallel mode
                    print(f"Status:           Setup complete (parallel mode)")
                    print(f"Agents:           {len(result['agents'])}")
                    print(f"Base commit:      {result['base_commit']}")
                    print("")
                    for agent_id, info in result.get("agents", {}).items():
                        print(f"Agent {agent_id}:")
                        print(f"  Worktree: {info['worktree_path']}")
                else:
                    # Single-agent mode
                    print(f"Status:           Setup complete")
                    print(f"Worktree:         {result['worktree_path']}")
                    print(f"Base commit:      {result['base_commit']}")
            else:
                print(f"Status:           Dry run successful (setup validated)")
            return 0
        else:
            print(f"Status: {result['status']}")
            if "error" in result:
                print(f"Error:  {result['error']}")
            return 1

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nExperiment cancelled by user.")
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
