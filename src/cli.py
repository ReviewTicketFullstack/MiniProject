#!/usr/bin/env python3
"""CLI entry point for change-drill experiments."""

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
        "--dry-run",
        action="store_true",
        help="Validate setup without executing experiment",
    )
    parser.add_argument(
        "--scenarios-file",
        type=Path,
        default=None,
        help="Path to scenarios.json (default: auto-detect from codeStress repo)",
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

        scenarios_file = args.scenarios_file or (codestress_root / "src" / "scenarios.json")
        results_dir = args.results_dir or (codestress_root / "results")

        scenarios = load_scenarios(scenarios_file)

        if not args.scenario:
            scenario_id = interactive_scenario_selection(scenarios)
        else:
            scenario_id = args.scenario

        scenario = get_scenario_by_id(scenarios, scenario_id)

        if not args.dry_run:
            if not confirm_experiment(args.repo_path, scenario):
                print("Experiment cancelled.")
                return 0
        else:
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

        result = harness.run(dry_run=args.dry_run)

        print("")
        print("=" * 60)
        print("EXPERIMENT COMPLETE")
        print("=" * 60)
        print("")

        if result["status"] in ("success", "dry_run_success"):
            if result["status"] == "success":
                print(f"Status:           Completed")
                print(f"Files changed:    {result['files_changed']}")
                print(f"Lines added:      {result['lines_added']}")
                print(f"Build success:    {'✓' if result['build_success'] else '✗'}")
                print(f"Tests passed:     {'✓' if result['test_success'] else '✗'}")
                print("")
                print(f"Results JSON:     {result['results_json']}")
                print(f"Results Markdown: {result['results_markdown']}")
                print(f"Results Diff:     {result['results_diff']}")
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
