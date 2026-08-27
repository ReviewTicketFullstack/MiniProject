"""차트 6종. PNG로 저장하고 동시에 base64로 돌려준다.

PNG를 파일로도 남기는 이유는 발표 슬라이드에 그림을 그대로 옮겨 붙이기
위해서다. 색과 축 규칙은 dataviz 스킬의 기준 팔레트를 따른다.
"""

from __future__ import annotations

import base64
import io
import random
from collections import Counter
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

# 기준 팔레트 (라이트 서피스). 슬라이드에 붙일 그림이므로 라이트로 고정한다.
SURFACE = "#fcfcfb"
TEXT_PRIMARY = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
GRID = "#dedcd6"
SERIES = ("#2a78d6", "#eb6834", "#1baf7a")

_KOREAN_FONTS = ("Malgun Gothic", "NanumGothic", "Gulim", "Dotum")


def _setup() -> None:
    available = {f.name for f in font_manager.fontManager.ttflist}
    for name in _KOREAN_FONTS:
        if name in available:
            plt.rcParams["font.family"] = name
            break
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["figure.facecolor"] = SURFACE
    plt.rcParams["axes.facecolor"] = SURFACE
    plt.rcParams["savefig.facecolor"] = SURFACE
    plt.rcParams["text.color"] = TEXT_PRIMARY
    plt.rcParams["axes.labelcolor"] = TEXT_SECONDARY
    plt.rcParams["xtick.color"] = TEXT_SECONDARY
    plt.rcParams["ytick.color"] = TEXT_SECONDARY
    plt.rcParams["axes.titlesize"] = 13
    plt.rcParams["font.size"] = 10


def _style(ax) -> None:
    """축은 물러나고 데이터가 앞에 오도록 한다."""
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
        ax.spines[side].set_linewidth(1)
    ax.grid(axis="y", color=GRID, linewidth=0.8, alpha=0.7)
    ax.set_axisbelow(True)


def _ylabel(ax, text: str) -> None:
    """세로축 이름을 가로로 눕혀 축 위쪽에 놓는다.

    세로로 세워 두면 글자를 한 자씩 옆으로 읽어야 해서 알아보기 어렵다.
    특히 한글은 세로쓰기가 아니라 옆으로 누운 형태가 되어 더 불편하다.
    """
    ax.set_ylabel(text, rotation=0, ha="left", va="bottom", labelpad=0)
    ax.yaxis.set_label_coords(0.0, 1.03)


def _style_horizontal(ax) -> None:
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.spines["left"].set_color(GRID)
    ax.spines["bottom"].set_color(GRID)
    ax.grid(axis="x", color=GRID, linewidth=0.8, alpha=0.7)
    ax.set_axisbelow(True)


def _finish(fig, out_dir: Path, name: str) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    png_path = out_dir / (name + ".png")
    fig.savefig(png_path, dpi=160, bbox_inches="tight")
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=160, bbox_inches="tight")
    plt.close(fig)
    encoded = base64.b64encode(buf.getvalue()).decode()
    return {
        "name": name,
        "path": str(png_path),
        "data_uri": "data:image/png;base64," + encoded,
    }


def quadrant_scatter(rows, out_dir: Path) -> dict[str, str]:
    """프롬프트 점수 x 결과 점수. 구역은 위치로 구분되므로 색은 하나만 쓴다."""
    fig, ax = plt.subplots(figsize=(7.2, 5.4))
    # 점수가 이산값이라 점이 세로줄로 뭉친다. 밀도가 보이도록 미세 지터를 준다.
    rng = random.Random(42)
    xs = [r.prompt_score + rng.uniform(-1.4, 1.4) for r in rows]
    ys = [r.outcome_score + rng.uniform(-0.9, 0.9) for r in rows]
    ax.scatter(xs, ys, s=26, color=SERIES[0], alpha=0.42,
               edgecolors=SURFACE, linewidths=1.2)
    ax.axvline(60, color=TEXT_SECONDARY, linewidth=1, alpha=0.55)
    ax.axhline(60, color=TEXT_SECONDARY, linewidth=1, alpha=0.55)

    ax.set_xlim(min(xs) - 7, max(xs) + 7)
    ax.set_ylim(min(ys) - 6, max(ys) + 6)
    ax.set_xlabel("프롬프트 점수 (오른쪽일수록 문장을 잘 쓴 것)")
    _ylabel(ax, "결과 점수 (위쪽일수록 원하는 결과를 얻은 것)")
    _style(ax)
    return _finish(fig, out_dir, "quadrant")


LENGTH_BUCKETS = [(0, 20), (20, 50), (50, 120), (120, 300), (300, 800), (800, 10 ** 9)]
LENGTH_LABELS = ["~20자", "20~50자", "50~120자", "120~300자", "300~800자", "800자~"]


def rework_by_length(rows, out_dir: Path) -> dict[str, str]:
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    rates = []
    totals = []
    for lo, hi in LENGTH_BUCKETS:
        bucket = [r for r in rows if lo <= r.metrics.char_len < hi]
        totals.append(len(bucket))
        n = sum(1 for r in bucket if r.metrics.followed_by_correction)
        rates.append(n / len(bucket) * 100 if bucket else 0.0)

    bars = ax.bar(LENGTH_LABELS, rates, color=SERIES[0], width=0.62)
    top = max(rates + [1.0])
    for bar, rate, total in zip(bars, rates, totals):
        ax.text(bar.get_x() + bar.get_width() / 2, rate + top * 0.02,
                format(rate, ".1f") + "%\n(n=" + format(total, ",") + ")",
                ha="center", va="bottom", fontsize=8.5,
                color=TEXT_SECONDARY, linespacing=1.4)
    _ylabel(ax, "재작업률 (%)")
    ax.set_xlabel("프롬프트 길이")
    ax.set_ylim(0, top * 1.35)
    _style(ax)
    return _finish(fig, out_dir, "rework_by_length")


def tool_distribution(counter: Counter, out_dir: Path) -> dict[str, str]:
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    items = counter.most_common(10)[::-1]
    if not items:
        items = [("해당 없음", 0)]
    names = [n.replace("mcp__", "").replace("Claude_Browser__", "browser.")[:28]
             for n, _ in items]
    values = [v for _, v in items]
    ax.barh(names, values, color=SERIES[0], height=0.6)
    top = max(values + [1])
    for i, v in enumerate(values):
        ax.text(v + top * 0.01, i, format(v, ","), va="center",
                fontsize=8.5, color=TEXT_SECONDARY)
    ax.set_xlabel("호출 횟수")
    _style_horizontal(ax)
    return _finish(fig, out_dir, "tool_distribution")


def weekly_trend(rows, out_dir: Path) -> dict[str, str]:
    """세 지표 모두 단위가 퍼센트라 축 하나에 함께 올릴 수 있다."""
    buckets: dict[str, list] = {}
    for row in rows:
        ts = row.prompt.timestamp
        if not ts:
            continue
        iso = ts.isocalendar()
        key = format(iso.year, "d") + "-W" + format(iso.week, "02d")
        buckets.setdefault(key, []).append(row)

    keys = sorted(buckets)
    rework = []
    interrupt = []
    tool_err = []
    for key in keys:
        group = buckets[key]
        n = len(group) or 1
        rework.append(sum(1 for r in group if r.metrics.followed_by_correction) / n * 100)
        interrupt.append(sum(1 for r in group if r.metrics.interrupted) / n * 100)
        calls = sum(r.metrics.tool_call_count for r in group)
        errs = sum(r.metrics.tool_error_count for r in group)
        tool_err.append(errs / calls * 100 if calls else 0.0)

    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    ax.plot(keys, rework, color=SERIES[0], linewidth=2, marker="o",
            markersize=5, label="재작업률")
    ax.plot(keys, interrupt, color=SERIES[1], linewidth=2, marker="s",
            markersize=5, label="중단률")
    ax.plot(keys, tool_err, color=SERIES[2], linewidth=2, marker="^",
            markersize=5, label="도구 에러율")
    _ylabel(ax, "비율 (%)")
    ax.set_xlabel("주차")
    ax.legend(frameon=False, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.2))
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
    _style(ax)
    return _finish(fig, out_dir, "weekly_trend")


def antipattern_freq(counter: Counter, out_dir: Path) -> dict[str, str]:
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    items = counter.most_common()[::-1]
    if not items:
        items = [("해당 없음", 0)]
    names = [n for n, _ in items]
    values = [v for _, v in items]
    ax.barh(names, values, color=SERIES[1], height=0.58)
    top = max(values + [1])
    for i, v in enumerate(values):
        ax.text(v + top * 0.01, i, format(v, ","), va="center",
                fontsize=8.5, color=TEXT_SECONDARY)
    ax.set_xlabel("발생 건수")
    _style_horizontal(ax)
    return _finish(fig, out_dir, "antipatterns")


def score_gap(rows, out_dir: Path, judged: dict[str, Any] | None = None) -> dict[str, str]:
    """문장 점수에서 결과 점수를 뺀 값의 분포.

    양수가 크면 문장은 멀쩡했는데 결과가 나빴던 프롬프트다. LLM 채점 결과가
    있으면 블라인드 점수와 결과 인지 점수의 차로 대신한다.
    """
    gaps = []
    if judged:
        for value in judged.values():
            if "blind_total" in value and "aware_total" in value:
                gaps.append(value["blind_total"] - value["aware_total"])
    if gaps:
        title = "블라인드 채점과 결과 인지 채점의 점수 차"
        xlabel = "블라인드 - 결과 인지 (30점 만점 기준)"
        threshold = 3
    else:
        gaps = [r.prompt_score - r.outcome_score for r in rows]
        title = "문장 점수와 결과 점수의 차"
        xlabel = "프롬프트 점수 - 결과 점수"
        threshold = 10

    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    bins = min(24, max(8, len(gaps) // 8))
    ax.hist(gaps, bins=bins, color=SERIES[0], edgecolor=SURFACE, linewidth=1.2)
    ax.axvline(0, color=TEXT_SECONDARY, linewidth=1.4)
    over = sum(1 for g in gaps if g > threshold)
    ax.text(0.98, 0.94, "문장만 좋았던 프롬프트 " + format(over, ",") + "건",
            transform=ax.transAxes, ha="right", va="top",
            fontsize=9.5, color=TEXT_SECONDARY)
    ax.set_xlabel(xlabel)
    _ylabel(ax, "프롬프트 수")
    _style(ax)
    return _finish(fig, out_dir, "score_gap")


def score_breakdown(rows, out_dir: Path) -> dict[str, str]:
    """채점 항목마다 만점 대비 몇 점을 받았는지 나란히 보여 준다.

    회색 막대가 만점이고 그 위에 겹친 파란 막대가 실제로 받은 평균 점수다.
    """
    from .metrics import RUBRIC

    labels = [item["label"] for item in RUBRIC][::-1]
    maxima = [float(item["max"]) for item in RUBRIC][::-1]
    keys = [item["key"] for item in RUBRIC][::-1]

    earned = []
    for key in keys:
        values = [r.metrics.score_components.get(key, 0.0) for r in rows]
        earned.append(sum(values) / len(values) if values else 0.0)

    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    ax.barh(labels, maxima, color=GRID, height=0.6, label="만점")
    ax.barh(labels, earned, color=SERIES[0], height=0.6, label="평균 획득 점수")
    for i, (got, full) in enumerate(zip(earned, maxima)):
        ax.text(full + 0.6, i, format(got, ".1f") + " / " + format(int(full), "d"),
                va="center", fontsize=9, color=TEXT_SECONDARY)
    ax.set_xlabel("점수")
    ax.set_xlim(0, max(maxima) * 1.28)
    ax.legend(frameon=False, ncol=2, loc="upper center", bbox_to_anchor=(0.5, -0.16))
    _style_horizontal(ax)
    return _finish(fig, out_dir, "score_breakdown")


def outcome_breakdown(rows, out_dir: Path) -> dict[str, str]:
    """결과 점수도 같은 방식으로 항목별 획득 점수를 보여 준다."""
    from .metrics import OUTCOME_RUBRIC

    labels = [item["label"] for item in OUTCOME_RUBRIC][::-1]
    maxima = [float(item["max"]) for item in OUTCOME_RUBRIC][::-1]
    keys = [item["key"] for item in OUTCOME_RUBRIC][::-1]

    earned = []
    for key, full in zip(keys, maxima):
        # 각 층은 100점 기준으로 계산되므로 배점 비율로 환산한다.
        values = [getattr(r.outcome, key, 0.0) / 100 * full for r in rows]
        earned.append(sum(values) / len(values) if values else 0.0)

    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    ax.barh(labels, maxima, color=GRID, height=0.6, label="만점")
    ax.barh(labels, earned, color=SERIES[2], height=0.6, label="평균 획득 점수")
    for i, (got, full) in enumerate(zip(earned, maxima)):
        ax.text(full + 0.8, i, format(got, ".1f") + " / " + format(int(full), "d"),
                va="center", fontsize=9, color=TEXT_SECONDARY)
    ax.set_xlabel("점수")
    ax.set_xlim(0, max(maxima) * 1.28)
    ax.legend(frameon=False, ncol=2, loc="upper center", bbox_to_anchor=(0.5, -0.18))
    _style_horizontal(ax)
    return _finish(fig, out_dir, "outcome_breakdown")


def score_histogram(rows, out_dir: Path) -> dict[str, str]:
    """100점 만점 프롬프트 점수가 어떻게 흩어져 있는지 보여 준다."""
    scores = [r.prompt_score for r in rows]
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    ax.hist(scores, bins=20, color=SERIES[0], edgecolor=SURFACE, linewidth=1.2)
    average = sum(scores) / len(scores) if scores else 0
    ax.axvline(average, color=SERIES[1], linewidth=2)
    ax.text(average + 1.5, ax.get_ylim()[1] * 0.92,
            "평균 " + format(average, ".1f") + "점",
            fontsize=9.5, color=TEXT_SECONDARY)
    ax.set_xlabel("프롬프트 점수 (100점 만점)")
    _ylabel(ax, "프롬프트 수")
    _style(ax)
    return _finish(fig, out_dir, "score_histogram")


def build_all(analysis, out_dir: Path,
              judged: dict[str, Any] | None = None) -> dict[str, dict[str, str]]:
    _setup()
    rows = analysis.rows
    return {
        "quadrant": quadrant_scatter(rows, out_dir),
        "score_breakdown": score_breakdown(rows, out_dir),
        "outcome_breakdown": outcome_breakdown(rows, out_dir),
        "score_histogram": score_histogram(rows, out_dir),
        "rework_by_length": rework_by_length(rows, out_dir),
        "tool_distribution": tool_distribution(analysis.tool_counter, out_dir),
        "weekly_trend": weekly_trend(rows, out_dir),
        "antipatterns": antipattern_freq(analysis.antipattern_counter, out_dir),
        "score_gap": score_gap(rows, out_dir, judged),
    }
