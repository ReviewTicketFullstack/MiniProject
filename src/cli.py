#!/usr/bin/env python3
"""CLI entry point for change-drill experiments.

사용자 인터페이스: 시나리오 선택, phase 구분(setup/measure/full), 병렬 모드 설정.
두 harness 프로세스(setup → measure)를 순차로 호출하고 결과를 출력. 단일/병렬 모드 모두 지원.
"""

import argparse
import json
import sys
from pathlib import Path

from .harness import Harness


def load_scenarios(scenarios_path: Path) -> dict:
    """Load scenario catalog from JSON file."""
    if not scenarios_path.exists():
        raise FileNotFoundError(f"Scenarios file not found: {scenarios_path}")

    with open(scenarios_path) as f:
        data = json.load(f)
    return data.get("scenarios", [])


def interactive_scenario_selection(scenarios: list) -> str:
    """Prompt user to select a scenario."""
    print("Available scenarios:")
    print("")
    for i, scenario in enumerate(scenarios, 1):
        print(f"{i}. {scenario['name']}")
        print(f"   ID: {scenario['id']}")
        print(f"   {scenario['description']}")
        print("")

    while True:
        selection = input("Select scenario (number or ID): ").strip()
        try:
            idx = int(selection) - 1
            if 0 <= idx < len(scenarios):
                return scenarios[idx]["id"]
        except ValueError:
            for scenario in scenarios:
                if scenario["id"] == selection:
                    return scenario["id"]

        print("Invalid selection. Try again.")


def get_scenario_by_id(scenarios: list, scenario_id: str) -> dict:
    """Find scenario by ID."""
    for s in scenarios:
        if s["id"] == scenario_id:
            return s
    raise ValueError(f"Scenario not found: {scenario_id}")


def confirm_experiment(repo_path: Path, scenario: dict) -> bool:
    """Get user confirmation to proceed with experiment."""
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
        "--scenario",
        type=str,
        help="Scenario ID to run (default: interactive selection)",
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
        default=1,
        help="Number of parallel agents (1 = single agent, 2+ = parallel mode)",
    )
    parser.add_argument(
        "--scenarios-file",
        type=Path,
        default=None,
        help="Path to scenarios.json (default: auto-detect from codeStress repo)",
    )
    parser.add_argument(
        "--scenario-json",
        type=str,
        default=None,
        help="Scenario as JSON string (overrides scenarios.json loading)",
    )
    parser.add_argument(
    "--predict",
    action="store_true",
    help="Prediction-only mode: analyze without implementing (no worktrees, no modifications)",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=None,
        help="Directory to store results (default: results/ in codeStress repo)",
    )

    args = parser.parse_args()

    try:
        codestress_root = Path(__file__).parent.parent

        results_dir = args.results_dir or (codestress_root / "results")

        # Load scenario from JSON string or predefined catalog
        if args.scenario_json:
            try:
                scenario = json.loads(args.scenario_json)
            except json.JSONDecodeError as e:
                print(f"Error: Invalid JSON in --scenario-json: {e}", file=sys.stderr)
                return 1
        else:
            scenarios_file = args.scenarios_file or (codestress_root / "src" / "scenarios.json")
            scenarios = load_scenarios(scenarios_file)

            if not args.scenario:
                scenario_id = interactive_scenario_selection(scenarios)
            else:
                scenario_id = args.scenario

            scenario = get_scenario_by_id(scenarios, scenario_id)

        # Handle prediction-only mode first (before parallel mode check)
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
