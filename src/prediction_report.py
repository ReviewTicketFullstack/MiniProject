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
        return "근접"
    if pct <= 25:
        return "중간"
    return "넓음"


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
    lines.append("  코드스트레스 · 변경 드릴 예측")
    lines.append("  추정치 전용 · 읽기 전용 분석")
    lines.append(_rule("━"))
    lines.append("")
    lines.append("  시나리오")
    lines.append(f"  {scenario_name}")
    lines.append("")

    # ── Key metrics table ─────────────────────────────────────────────────
    lines.append("  주요 지표")
    lines.append(_table_border("┌", "┬", "┐", columns))
    lines.append(_table_row("지표", [f"에이전트 {a}" for a in agent_ids]))
    lines.append(_table_border("├", "┼", "┤", columns))
    lines.append(_table_row("토큰", [f"~{p.estimated_tokens:,}" for p in preds]))
    lines.append(
        _table_row("변경 파일", [f"{p.estimated_files_changed}" for p in preds])
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
        _table_row("복잡도", [p.complexity_level.upper() for p in preds])
    )
    lines.append(_table_border("└", "┴", "┘", columns))
    lines.append("")

    # ── Estimate comparison ───────────────────────────────────────────────
    lines.append("  추정치 비교")
    lines.append("")
    lines.extend(
        _chart(
            "토큰",
            agent_ids,
            [p.estimated_tokens for p in preds],
            lambda v: f"~{int(v):,}",
        )
    )
    lines.extend(
        _chart(
            "파일",
            agent_ids,
            [p.estimated_files_changed for p in preds],
            lambda v: f"{int(v)}",
        )
    )
    lines.extend(
        _chart(
            "터치된 LOC",
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
            f"동의 ({levels.pop()})" if len(levels) == 1
            else "불일치 (" + ", ".join(sorted(levels)) + ")"
        )

        consensus = [
            ("범위", _agreement_band(file_pct)),
            ("복잡도", complexity_note),
            ("토큰", _agreement_band(token_pct)),
            ("LOC", _agreement_band(loc_pct)),
        ]
        difference = [
            ("토큰", f"~{int(token_diff):,} ({token_pct:.0f}%)"),
            ("파일", f"{int(file_diff)} ({file_pct:.0f}%)"),
            ("LOC", f"{int(loc_diff)} ({loc_pct:.0f}%)"),
        ]
    else:
        consensus = [
            ("범위", "해당 없음 (단일 에이전트)"),
            ("복잡도", "해당 없음 (단일 에이전트)"),
            ("토큰", "해당 없음 (단일 에이전트)"),
            ("LOC", "해당 없음 (단일 에이전트)"),
        ]
        difference = [
            ("토큰", "해당 없음 (단일 에이전트)"),
            ("파일", "해당 없음 (단일 에이전트)"),
            ("LOC", "해당 없음 (단일 에이전트)"),
        ]

    lines.append("  합의")
    lines.extend(_note(label, value) for label, value in consensus)
    lines.append("")

    lines.append("  차이")
    lines.extend(_note(label, value) for label, value in difference)
    lines.append("")

    # ── Footer ────────────────────────────────────────────────────────────
    lines.append(_rule("━"))
    lines.append("  모든 값은 정적 코드 분석의 추정치입니다.")
    lines.append("  원본 파일은 수정되지 않았습니다.")
    lines.append(_rule("━"))
    lines.append("")

    return "\n".join(lines)


def print_prediction_result(comparison: PredictionComparison, scenario_name: str) -> None:
    """Print formatted prediction to terminal."""
    output = format_prediction_result(comparison, scenario_name)
    print(output)
