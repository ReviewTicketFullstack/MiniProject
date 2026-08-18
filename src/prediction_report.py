"""Terminal UI for prediction results."""

from typing import Dict
from .prediction import PredictionComparison, AgentPrediction


def format_prediction_result(
    comparison: PredictionComparison,
    scenario_name: str,
) -> str:
    lines = []

    lines.append("━" * 70)
    lines.append("             CODESTRESS")
    lines.append("         CHANGE DRILL PREDICTION")
    lines.append("━" * 70)
    lines.append("")

    lines.append("Scenario")
    lines.append(f"  {scenario_name}")
    lines.append("")

    lines.append("ESTIMATED COST")
    lines.append("")

    for agent_id in sorted(comparison.agents.keys()):
        pred = comparison.agents[agent_id]

        lines.append(f"  Agent {agent_id}")
        lines.append(f"    Tokens          ~{pred.estimated_tokens:,}")
        lines.append(f"    Files changed   {pred.estimated_files_changed}")
        lines.append(
            f"    LOC             +{pred.estimated_lines_added} / "
            f"-{pred.estimated_lines_deleted}"
        )
        lines.append(f"    Complexity      {pred.complexity_level}")
        lines.append("")

    lines.append("━" * 70)
    lines.append("")

    lines.append("CHANGEABILITY")
    lines.append("")

    for agent_id in sorted(comparison.agents.keys()):
        pred = comparison.agents[agent_id]

        lines.append(f"  Agent {agent_id}")
        lines.append(f"    {pred.changeability_observations}")
        lines.append("")

    lines.append("━" * 70)
    lines.append("")

    lines.append("COMPARISON")
    lines.append("")
    lines.append(f"  Scope             {comparison.scope_consensus}")

    if len(comparison.agents) >= 2:
        predictions = list(comparison.agents.values())

        token_difference = abs(
            predictions[0].estimated_tokens
            - predictions[1].estimated_tokens
        )

        file_difference = abs(
            predictions[0].estimated_files_changed
            - predictions[1].estimated_files_changed
        )

        loc_difference = abs(
            (
                predictions[0].estimated_lines_added
                + predictions[0].estimated_lines_deleted
            )
            -
            (
                predictions[1].estimated_lines_added
                + predictions[1].estimated_lines_deleted
            )
        )

        lines.append(f"  Token difference  ~{token_difference:,}")
        lines.append(f"  File difference   {file_difference}")
        lines.append(f"  LOC difference    {loc_difference}")

    lines.append("")
    lines.append("━" * 70)
    lines.append("")
    lines.append("All values are estimates based on static code analysis.")
    lines.append("No files were modified during prediction.")
    lines.append("")

    return "\n".join(lines)


def print_prediction_result(comparison: PredictionComparison, scenario_name: str) -> None:
    """Print formatted prediction to terminal."""
    output = format_prediction_result(comparison, scenario_name)
    print(output)
