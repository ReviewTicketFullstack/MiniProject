"""Terminal UI output for change drill results.

Display experiment results in a visually clear terminal format.
"""

from typing import Dict, List
from .analysis import ComparisonResult


def format_terminal_result(comparison: ComparisonResult, scenario_name: str) -> str:
    """
    Format comparison results for terminal display.

    Args:
        comparison: Comparison analysis result
        scenario_name: Human-readable scenario name

    Returns:
        Formatted terminal output string
    """
    lines = []

    # Header
    lines.append("━" * 70)
    lines.append("             CODESTRESS")
    lines.append("          CHANGE DRILL RESULT")
    lines.append("━" * 70)
    lines.append("")

    # Scenario
    lines.append("Scenario")
    lines.append(f"  {scenario_name}")
    lines.append("")

    # COST section
    lines.append("COST")
    lines.append("")
    for agent_id in sorted(comparison.agents.keys()):
        metrics = comparison.agents[agent_id]

        lines.append(f"    Agent {agent_id}")
        lines.append(f"    Estimated tokens    ~{metrics.estimated_tokens:,}")
        lines.append(f"    Estimated files        {metrics.files_changed}")
        lines.append(
        f"    Estimated LOC       +{metrics.lines_added} / -{metrics.lines_deleted}"
        )
        lines.append("")

    # CHANGEABILITY section
    lines.append("CHANGEABILITY")
    lines.append("")
    for agent_id in sorted(comparison.agents.keys()):
        metrics = comparison.agents[agent_id]
        unrelated_files = metrics.files_changed - len(comparison.shared_files)

        lines.append(f"  Agent {agent_id}")
        lines.append(f"    Change scope       {metrics.files_changed} files")
        lines.append(f"    Shared files       {len(comparison.shared_files)}")
        lines.append(f"    Unrelated files    {max(0, unrelated_files)}")
        lines.append("")

    # CODE STRUCTURE section - analyze from implementation approach
    lines.append("CODE STRUCTURE")
    lines.append("")

    # Determine coupling/duplication based on divergence
    for agent_id in sorted(comparison.agents.keys()):
        metrics = comparison.agents[agent_id]

        # Simple heuristic: more divergent files = higher coupling
        unrelated = metrics.files_changed - len(comparison.shared_files)

        if unrelated <= 1:
            coupling = "Low"
            duplication = "Low"
            responsibility = "Focused"
        elif unrelated <= 2:
            coupling = "Low-Medium"
            duplication = "Low-Medium"
            responsibility = "Balanced"
        else:
            coupling = "Medium"
            duplication = "Medium"
            responsibility = "Distributed"

        lines.append(f"  Agent {agent_id}")
        lines.append(f"    Coupling           {coupling}")
        lines.append(f"    Duplication        {duplication}")
        lines.append(f"    Responsibility     {responsibility}")
        lines.append("")

    # REFACTORING SUGGESTIONS section
    lines.append("REFACTORING SUGGESTIONS")
    lines.append("")
    lines.append("  Agent A")
    lines.append("    results/agent_A/refactoring-suggestion.md")
    lines.append("")
    lines.append("  Agent B")
    lines.append("    results/agent_B/refactoring-suggestion.md")
    lines.append("")

    lines.append("━" * 70)

    return "\n".join(lines)


def print_terminal_result(comparison: ComparisonResult, scenario_name: str) -> None:
    """Print formatted result to terminal."""
    output = format_terminal_result(comparison, scenario_name)
    print(output)
