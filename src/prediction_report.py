"""Terminal UI for prediction results.

Renders the fixed CHANGE DRILL PREDICTION template: a boxed KEY METRICS table,
an ESTIMATE COMPARISON block of ASCII bar charts, then CONSENSUS and
DIFFERENCE. The structure is deterministic - the same sections appear in the
same order for every run, whatever the agents reported.

Every number rendered here is an ESTIMATE from static analysis. Nothing was
built, executed, or measured. The long-form observations (implementation
approach, coupling, duplication, responsibility, changeability) are
deliberately kept out of this view - they stay in the saved JSON evidence.
"""

from typing import Callable, List, Sequence

from .prediction import PredictionComparison, AgentPrediction


WIDTH = 70
METRIC_COL = 22
AGENT_COL = 18
LABEL_WIDTH = 15
BAR_WIDTH = 32


def _rule(char: str = "─") -> str:
    return char * WIDTH


def _cell(text: str, width: int) -> str:
    """One table cell: leading pad, then text clipped to the column."""
    body = text[: width - 1]
    return f" {body:<{width - 1}}"


def _table_border(left: str, joint: str, right: str, columns: int) -> str:
    segments = ["─" * METRIC_COL] + ["─" * AGENT_COL] * columns
    return "  " + left + joint.join(segments) + right


def _table_row(label: str, cells: Sequence[str]) -> str:
    parts = [_cell(label, METRIC_COL)] + [_cell(cell, AGENT_COL) for cell in cells]
    return "  │" + "│".join(parts) + "│"


def _bar(value: float, max_value: float, width: int = BAR_WIDTH) -> str:
    """Proportional block bar, scaled against the largest estimate in the row."""
    if max_value <= 0 or value <= 0:
        return ""
    filled = int(round((value / max_value) * width))
    return "█" * max(1, min(width, filled))


def _chart(
    title: str,
    agent_ids: Sequence[str],
    values: Sequence[float],
    formatter: Callable[[float], str],
) -> List[str]:
    lines = [f"  {title}"]
    max_value = max(values) if values else 0

    for agent_id, value in zip(agent_ids, values):
        bar = _bar(value, max_value)
        lines.append(f"  Agent {agent_id:<3}{bar:<{BAR_WIDTH}}  {formatter(value)}")

    lines.append("")
    return lines


def _note(label: str, value: str) -> str:
    return f"  {label:<{LABEL_WIDTH}}{value}"


def _spread(values: Sequence[float]) -> tuple:
    """Absolute difference between the extreme estimates, plus % of the larger."""
    low, high = min(values), max(values)
    diff = high - low
    pct = (diff / high * 100) if high else 0.0
    return diff, pct


def _agreement_band(pct: float) -> str:
    if pct <= 10:
        return "close"
    if pct <= 25:
        return "moderate"
    return "wide"


def _total_loc(pred: AgentPrediction) -> int:
    return pred.estimated_lines_added + pred.estimated_lines_deleted


def format_prediction_result(
    comparison: PredictionComparison,
    scenario_name: str,
) -> str:
    agent_ids = sorted(comparison.agents.keys())
    preds = [comparison.agents[agent_id] for agent_id in agent_ids]
    columns = len(agent_ids)

    lines: List[str] = []

    # ── Header ────────────────────────────────────────────────────────────
    lines.append(_rule("━"))
    lines.append("  CODESTRESS · CHANGE DRILL PREDICTION")
    lines.append("  ESTIMATES ONLY · READ-ONLY ANALYSIS")
    lines.append(_rule("━"))
    lines.append("")
    lines.append("  SCENARIO")
    lines.append(f"  {scenario_name}")
    lines.append("")

    # ── Key metrics table ─────────────────────────────────────────────────
    lines.append("  KEY METRICS")
    lines.append(_table_border("┌", "┬", "┐", columns))
    lines.append(_table_row("Metric", [f"Agent {a}" for a in agent_ids]))
    lines.append(_table_border("├", "┼", "┤", columns))
    lines.append(_table_row("Tokens", [f"~{p.estimated_tokens:,}" for p in preds]))
    lines.append(
        _table_row("Files changed", [f"{p.estimated_files_changed}" for p in preds])
    )
    lines.append(
        _table_row(
            "LOC (+ / -)",
            [
                f"+{p.estimated_lines_added} / -{p.estimated_lines_deleted}"
                for p in preds
            ],
        )
    )
    lines.append(
        _table_row("Complexity", [p.complexity_level.upper() for p in preds])
    )
    lines.append(_table_border("└", "┴", "┘", columns))
    lines.append("")

    # ── Estimate comparison ───────────────────────────────────────────────
    lines.append("  ESTIMATE COMPARISON")
    lines.append("")
    lines.extend(
        _chart(
            "Tokens",
            agent_ids,
            [p.estimated_tokens for p in preds],
            lambda v: f"~{int(v):,}",
        )
    )
    lines.extend(
        _chart(
            "Files",
            agent_ids,
            [p.estimated_files_changed for p in preds],
            lambda v: f"{int(v)}",
        )
    )
    lines.extend(
        _chart(
            "LOC TOUCHED",
            agent_ids,
            [_total_loc(p) for p in preds],
            lambda v: f"{int(v)}",
        )
    )

    # ── Consensus / difference ────────────────────────────────────────────
    # Both blocks always render; with a single agent there is nothing to
    # compare, so every field reads n/a rather than being dropped.
    if len(preds) >= 2:
        token_diff, token_pct = _spread([p.estimated_tokens for p in preds])
        file_diff, file_pct = _spread([p.estimated_files_changed for p in preds])
        loc_diff, loc_pct = _spread([_total_loc(p) for p in preds])

        levels = {p.complexity_level.strip().lower() for p in preds}
        complexity_note = (
            f"agree ({levels.pop()})" if len(levels) == 1
            else "differ (" + ", ".join(sorted(levels)) + ")"
        )

        consensus = [
            ("Scope", _agreement_band(file_pct)),
            ("Complexity", complexity_note),
            ("Tokens", _agreement_band(token_pct)),
            ("LOC", _agreement_band(loc_pct)),
        ]
        difference = [
            ("Tokens", f"~{int(token_diff):,} ({token_pct:.0f}%)"),
            ("Files", f"{int(file_diff)} ({file_pct:.0f}%)"),
            ("LOC", f"{int(loc_diff)} ({loc_pct:.0f}%)"),
        ]
    else:
        consensus = [
            ("Scope", "n/a (single agent)"),
            ("Complexity", "n/a (single agent)"),
            ("Tokens", "n/a (single agent)"),
            ("LOC", "n/a (single agent)"),
        ]
        difference = [
            ("Tokens", "n/a (single agent)"),
            ("Files", "n/a (single agent)"),
            ("LOC", "n/a (single agent)"),
        ]

    lines.append("  CONSENSUS")
    lines.extend(_note(label, value) for label, value in consensus)
    lines.append("")

    lines.append("  DIFFERENCE")
    lines.extend(_note(label, value) for label, value in difference)
    lines.append("")

    # ── Footer ────────────────────────────────────────────────────────────
    lines.append(_rule("━"))
    lines.append("  All values are estimates from static code analysis.")
    lines.append("  No source files were modified.")
    lines.append(_rule("━"))
    lines.append("")

    return "\n".join(lines)


def print_prediction_result(comparison: PredictionComparison, scenario_name: str) -> None:
    """Print formatted prediction to terminal."""
    output = format_prediction_result(comparison, scenario_name)
    print(output)
