"""리포트 생성.

네 개의 장으로 나뉜 한 장짜리 HTML을 만든다. 위쪽 버튼으로 장을 옮겨 다닐 수
있고, 각 장은 그림과 설명, 그리고 펼쳐서 원문을 확인할 수 있는 목록으로
이루어져 있다. 설명 문장은 프롬프트를 처음 다뤄 보는 사람이 읽어도 이해할 수
있도록 완성된 문장으로 쓴다.
"""

from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from . import advice as advice_mod
from .masking import excerpt, mask
from .metrics import OUTCOME_RUBRIC, RUBRIC
from .rubric import MAX_TOTAL

PASS_LINE = 60

CHART_NOTES = {
    "quadrant": (
        "점 하나가 프롬프트 하나입니다. 가로로 오른쪽에 있을수록 문장을 잘 쓴 것이고, "
        "세로로 위쪽에 있을수록 원하는 결과를 얻은 것입니다. 가운데 가로선과 세로선은 "
        "60점 기준선입니다. 오른쪽 아래에 놓인 점들은 문장은 잘 썼는데 결과가 따라오지 "
        "않은 경우이고, 왼쪽 위에 놓인 점들은 문장은 부실했지만 앞의 대화 덕분에 넘어간 "
        "경우입니다."
    ),
    "score_histogram": (
        "프롬프트 점수가 어느 구간에 몰려 있는지 보여 줍니다. 막대가 높은 자리가 가장 "
        "흔한 점수대이고, 주황색 세로선이 전체 평균입니다."
    ),
    "score_breakdown": (
        "회색 막대가 각 항목의 만점이고, 그 위에 겹쳐진 파란 막대가 실제로 받은 평균 "
        "점수입니다. 두 막대의 차이가 큰 항목일수록 앞으로 점수를 올릴 여지가 많습니다."
    ),
    "outcome_breakdown": (
        "결과 점수도 같은 방식으로 읽으면 됩니다. 회색이 만점이고 초록색이 실제로 받은 "
        "평균 점수입니다."
    ),
    "rework_by_length": (
        "재작업률이란 어떤 프롬프트를 보낸 바로 다음에 '아니 그게 아니라' 같은 정정이 "
        "따라붙은 비율입니다. 막대가 낮을수록 한 번에 통했다는 뜻입니다. 글자 수 구간별로 "
        "묶어 두었으니 길게 쓰는 것이 실제로 도움이 되었는지 확인할 수 있습니다."
    ),
    "tool_distribution": (
        "대화 중에 어떤 도구를 몇 번 시켰는지 보여 줍니다. 파일을 읽는 일보다 명령을 "
        "실행하거나 파일을 고치는 일이 훨씬 많다면, 확인을 건너뛰고 바로 손대는 습관이 "
        "있다는 신호로 볼 수 있습니다."
    ),
    "weekly_trend": (
        "세 가지 지표를 주 단위로 이어 놓은 그림입니다. 세 선 모두 낮을수록 좋습니다. "
        "선이 오른쪽으로 갈수록 내려간다면 협업이 실제로 나아지고 있다는 뜻입니다."
    ),
    "antipatterns": (
        "미리 정해 둔 다섯 가지 실수가 각각 몇 번 나타났는지 세어 본 것입니다. 막대가 "
        "가장 긴 항목부터 고치는 것이 효율이 좋습니다."
    ),
    "score_gap": (
        "문장만 보고 매긴 점수에서 결과를 보고 매긴 점수를 뺀 값입니다. 0보다 오른쪽에 "
        "있는 프롬프트는 문장은 괜찮아 보였지만 실제 결과가 그만큼 따라오지 않은 경우입니다."
    ),
}

CHART_HEADINGS = {
    "quadrant": "문장 점수와 결과 점수를 함께 놓고 보기",
    "score_histogram": "프롬프트 점수의 분포",
    "score_breakdown": "프롬프트 점수를 항목별로 나눠 보기",
    "outcome_breakdown": "결과 점수를 항목별로 나눠 보기",
    "rework_by_length": "길게 쓰면 정말 나아지는가",
    "tool_distribution": "어떤 일을 시켰는가",
    "weekly_trend": "시간이 지나면서 나아졌는가",
    "antipatterns": "가장 자주 저지른 실수",
    "score_gap": "문장 점수와 결과 점수의 차이",
}


# --- 사례 고르기 ----------------------------------------------------------

def _happened(row) -> str:
    """그 프롬프트를 보낸 뒤 실제로 무슨 일이 있었는지 한 줄로 정리한다."""
    m = row.metrics
    parts = []
    if m.assistant_turns:
        parts.append("답변 " + str(m.assistant_turns) + "번")
    if m.tool_call_count:
        parts.append("도구 " + str(m.tool_call_count) + "회 사용")
    if m.tool_error_count:
        parts.append("그중 " + str(m.tool_error_count) + "회 실패")
    if m.edited_file_count:
        parts.append("파일 " + str(m.edited_file_count) + "개 수정")
    if row.outcome.committed_files:
        parts.append("커밋까지 남은 파일 " + str(row.outcome.committed_files) + "개")
    if m.interrupted:
        parts.append("도중에 중단됨")
    if m.followed_by_correction:
        parts.append("바로 다음에 정정을 받음")
    if m.followed_by_approval:
        parts.append("바로 다음에 승인을 받음")
    return ", ".join(parts) or "도구를 쓰지 않고 답변만 했습니다"


def _entry(row) -> dict[str, Any]:
    masked, _ = mask(row.prompt.text)
    return {
        "summary": excerpt(row.prompt.text, limit=90),
        "full": " ".join(masked.split()),
        "session": row.prompt.session_id[:8],
        "date": row.prompt.timestamp.strftime("%Y-%m-%d") if row.prompt.timestamp else "-",
        "prompt_score": round(row.prompt_score, 1),
        "outcome_score": round(row.outcome_score, 1),
        "happened": _happened(row),
        "antipatterns": row.metrics.antipatterns,
    }


def _collect(rows, limit: int) -> list[dict[str, Any]]:
    """세션이 한쪽으로 쏠리지 않도록 고르게 뽑는다."""
    seen: set[str] = set()
    picked: list[dict[str, Any]] = []
    leftovers = []
    for row in rows:
        if row.prompt.session_id in seen:
            leftovers.append(row)
            continue
        seen.add(row.prompt.session_id)
        picked.append(_entry(row))
        if len(picked) >= limit:
            return picked
    for row in leftovers:
        picked.append(_entry(row))
        if len(picked) >= limit:
            break
    return picked


def _pick_cases(analysis) -> dict[str, list[dict[str, Any]]]:
    rows = analysis.rows
    good = _collect(
        sorted(
            [r for r in rows if r.quadrant == "good_good" and r.metrics.char_len > 25],
            key=lambda r: -(r.outcome_score + r.prompt_score),
        ),
        18,
    )
    bad = _collect(
        sorted([r for r in rows if r.quadrant == "bad_bad"], key=lambda r: r.outcome_score),
        18,
    )
    claude = _collect(
        sorted(
            [r for r in rows if r.quadrant == "good_bad"],
            key=lambda r: -(r.prompt_score - r.outcome_score),
        ),
        12,
    )
    return {"good": good, "bad": bad, "claude": claude}


def _rewrites(analysis, judged: dict[str, Any] | None, limit: int = 6) -> list[dict[str, str]]:
    """채점 과정에서 만든 재작성본 가운데 결과가 나빴던 것부터 보여 준다."""
    if not judged:
        return []
    from .rubric import prompt_key

    by_key = {prompt_key(r.prompt.text): r for r in analysis.rows}
    scored = []
    for key, value in judged.items():
        if not value.get("rewrite"):
            continue
        row = by_key.get(key)
        if row is None:
            continue
        scored.append((row.outcome_score, value, row))
    scored.sort(key=lambda t: t[0])

    out = []
    for _, value, row in scored[:limit]:
        masked, _ = mask(row.prompt.text)
        out.append({
            "before": " ".join(masked.split())[:400],
            "after": str(value.get("rewrite")),
            "verdict": str(value.get("verdict") or ""),
            "prompt_score": round(row.prompt_score, 1),
            "outcome_score": round(row.outcome_score, 1),
        })
    return out


# --- 문맥 조립 ------------------------------------------------------------

def build_context(analysis, chart_files: dict[str, dict[str, str]],
                  judged: dict[str, Any] | None = None) -> dict[str, Any]:
    stats = analysis.summary()
    cards = advice_mod.build(analysis)
    cases = _pick_cases(analysis)

    masked_hits: set[str] = set()
    for row in analysis.rows:
        _, hits = mask(row.prompt.text)
        masked_hits.update(hits)

    component_avg = {}
    for item in RUBRIC:
        values = [r.metrics.score_components.get(item["key"], 0.0) for r in analysis.rows]
        component_avg[item["key"]] = round(sum(values) / len(values), 1) if values else 0.0

    outcome_avg = {}
    for item in OUTCOME_RUBRIC:
        values = [getattr(r.outcome, item["key"], 0.0) / 100 * item["max"]
                  for r in analysis.rows]
        outcome_avg[item["key"]] = round(sum(values) / len(values), 1) if values else 0.0

    judged_summary = None
    if judged:
        blind = [v["blind_total"] for v in judged.values() if "blind_total" in v]
        aware = [v["aware_total"] for v in judged.values() if "aware_total" in v]
        if blind and aware:
            judged_summary = {
                "count": len(blind),
                "blind_avg": round(sum(blind) / len(blind), 1),
                "aware_avg": round(sum(aware) / len(aware), 1),
                "max_total": MAX_TOTAL,
            }

    reason_label = {
        "cwd": "작업 폴더로 확인",
        "keyword": "대화 내용으로 확인",
        "cwd+keyword": "폴더와 내용 둘 다",
    }

    return {
        "generated_at": datetime.now().strftime("%Y년 %m월 %d일 %H시 %M분"),
        "stats": stats,
        "charts": chart_files,
        "notes": CHART_NOTES,
        "headings": CHART_HEADINGS,
        "cards": cards,
        "cases": cases,
        "rewrites": _rewrites(analysis, judged),
        "masked_hits": sorted(masked_hits),
        "judged": judged_summary,
        "component_avg": component_avg,
        "outcome_avg": outcome_avg,
        "sessions": [
            {
                "id": sel.session.session_id[:8],
                "prompts": len(sel.session.prompts),
                "reason": reason_label.get(sel.reason, sel.reason),
                "started": sel.session.started_at.strftime("%Y-%m-%d") if sel.session.started_at else "-",
            }
            for sel in analysis.selections
        ],
    }


# --- Markdown -------------------------------------------------------------

def render_markdown(ctx: dict[str, Any]) -> str:
    s = ctx["stats"]
    lines: list[str] = []
    add = lines.append

    add("# 프롬프트 평가 리포트")
    add("")
    add("이 리포트는 " + s["project"] + " 프로젝트를 진행하면서 오간 대화 기록을 읽어, "
        "사람이 직접 입력한 프롬프트 " + format(s["prompts"], ",") + "개를 평가한 "
        "결과입니다. 세션 " + str(s["sessions"]) + "개가 분석에 쓰였고, 만든 시각은 " +
        ctx["generated_at"] + "입니다.")
    add("")

    add("## 1장. 평가 지표")
    add("")
    add("**종합 점수는 100점 만점에 " + str(s["avg_total_score"]) + "점입니다.** "
        "문장 점수 " + str(s["avg_prompt_score"]) + "점의 절반인 " +
        str(s["prompt_half"]) + "점과, 결과 점수 " + str(s["avg_outcome_score"]) +
        "점의 절반인 " + str(s["outcome_half"]) + "점을 더한 값입니다.")
    add("")
    add("| 항목 | 값 | 어떤 뜻인가 |")
    add("| --- | --- | --- |")
    add("| 종합 점수 | " + str(s["avg_total_score"]) + " / 100 | 두 점수를 반씩 섞은 대표 값입니다 |")
    add("| 분석한 세션 | " + str(s["sessions"]) + "개 | 대화창 하나가 세션 하나입니다 |")
    add("| 분석한 프롬프트 | " + format(s["prompts"], ",") + "개 | 사람이 직접 입력한 것만 셌습니다 |")
    add("| 평균 프롬프트 점수 | " + str(s["avg_prompt_score"]) + " / 100 | 문장만 보고 매긴 점수입니다 |")
    add("| 평균 결과 점수 | " + str(s["avg_outcome_score"]) + " / 100 | 실제 결과를 보고 매긴 점수입니다 |")
    add("| 재작업률 | " + str(s["rework_rate"]) + "% | 바로 다음에 정정이 따라붙은 비율입니다 |")
    add("| 중단률 | " + str(s["interrupt_rate"]) + "% | 하던 작업을 사람이 끊은 비율입니다 |")
    add("| 도구 실패율 | " + str(s["tool_error_rate"]) + "% | 명령이 에러로 끝난 비율입니다 |")
    add("| 컨텍스트 제공률 | " + str(s["context_rate"]) + "% | 파일 경로나 에러를 함께 준 비율입니다 |")
    add("")

    for key in ("quadrant", "score_histogram", "rework_by_length",
                "tool_distribution", "weekly_trend", "antipatterns"):
        chart = ctx["charts"].get(key)
        if not chart:
            continue
        add("### " + ctx["headings"].get(key, key))
        add("")
        add("![" + key + "](" + Path(chart["path"]).as_posix() + ")")
        add("")
        add(ctx["notes"].get(key, ""))
        add("")

    add("## 2장. 상세 분석")
    add("")
    add("### 잘 쓴 프롬프트")
    add("")
    for case in ctx["cases"]["good"]:
        add("- " + case["summary"])
        add("  - 프롬프트 " + str(case["prompt_score"]) + "점, 결과 " + str(case["outcome_score"]) + "점")
        add("  - " + case["happened"])
    add("")
    add("### 못 쓴 프롬프트")
    add("")
    for case in ctx["cases"]["bad"]:
        add("- " + case["summary"])
        add("  - 프롬프트 " + str(case["prompt_score"]) + "점, 결과 " + str(case["outcome_score"]) + "점")
        add("  - " + case["happened"])
        if case["antipatterns"]:
            add("  - 걸린 실수: " + ", ".join(case["antipatterns"]))
    add("")
    add("### Claude의 문제")
    add("")
    add("아래는 사람이 프롬프트를 충분히 잘 썼는데도 결과가 따라오지 않은 경우입니다. "
        "프롬프트를 더 다듬는다고 해결되는 문제가 아니라, 받아들이는 쪽에서 잘못 처리한 "
        "사례로 보아야 합니다.")
    add("")
    for case in ctx["cases"]["claude"]:
        add("- " + case["summary"])
        add("  - 프롬프트는 " + str(case["prompt_score"]) + "점인데 결과는 " +
            str(case["outcome_score"]) + "점이었습니다")
        add("  - " + case["happened"])
    add("")

    add("## 3장. Feedback")
    add("")
    for i, card in enumerate(ctx["cards"][:5], 1):
        add("### " + str(i) + ". " + card.title)
        add("")
        add(card.why)
        add("")
        add("이렇게 하세요. " + card.how)
        add("")
    if ctx["rewrites"]:
        add("### 이렇게 다시 써 보세요")
        add("")
        for item in ctx["rewrites"]:
            add("- 그때 보낸 문장: " + item["before"])
            add("  - 이렇게 고치면 좋습니다: " + item["after"])
            if item["verdict"]:
                add("  - 이유: " + item["verdict"])
        add("")

    add("## 4장. 채점 기준")
    add("")
    add("프롬프트 점수는 아래 다섯 항목을 더해 100점으로 만듭니다.")
    add("")
    add("| 항목 | 배점 | 무엇을 보는가 | 평균 획득 |")
    add("| --- | --- | --- | --- |")
    for item in RUBRIC:
        add("| " + item["label"] + " | " + str(item["max"]) + "점 | " +
            item["question"] + " | " + str(ctx["component_avg"][item["key"]]) + "점 |")
    add("")
    add("결과 점수는 아래 네 항목을 더해 100점으로 만듭니다.")
    add("")
    add("| 항목 | 배점 | 무엇을 보는가 | 평균 획득 |")
    add("| --- | --- | --- | --- |")
    for item in OUTCOME_RUBRIC:
        add("| " + item["label"] + " | " + str(item["max"]) + "점 | " +
            item["question"] + " | " + str(ctx["outcome_avg"][item["key"]]) + "점 |")
    add("")
    add("### 종합 점수를 만드는 방법")
    add("")
    add("두 점수를 그대로 더하면 200점이 되므로, 각각의 절반씩만 가져와 더합니다. "
        "두 축을 똑같이 중요하게 본다는 뜻이고, 합계는 정확히 100점 만점이 됩니다.")
    add("")
    add("| 항목 | 점수 (100점 척도) | 종합에 들어가는 몫 |")
    add("| --- | --- | --- |")
    add("| 프롬프트 점수 | " + str(s["avg_prompt_score"]) + "점 | " + str(s["prompt_half"]) + "점 |")
    add("| 결과 점수 | " + str(s["avg_outcome_score"]) + "점 | " + str(s["outcome_half"]) + "점 |")
    add("| **종합 점수** | — | **" + str(s["avg_total_score"]) + "점** |")
    add("")
    add("오른쪽 칸만 더하면 " + str(s["prompt_half"]) + " + " + str(s["outcome_half"]) +
        " = " + str(s["avg_total_score"]) + "점이 됩니다.")
    add("")
    add("이 값은 전체를 한눈에 보기 위한 것이지, 무엇을 고쳐야 하는지를 알려 주지는 "
        "못합니다. 고칠 곳을 찾으려면 항목별 점수를 보셔야 합니다.")
    add("")

    add("## 이 리포트를 읽을 때 주의할 점")
    add("")
    add("결과 점수에는 과제의 난이도가 섞여 있습니다. 어려운 일일수록 주고받는 횟수가 "
        "늘고 실패도 잦은데, 그것이 반드시 프롬프트를 잘못 썼기 때문은 아닙니다. 따라서 "
        "두 점수가 함께 움직인다고 해서 하나가 다른 하나의 원인이라고 단정해서는 안 됩니다.")
    add("")
    if ctx["masked_hits"]:
        add("인용한 문장에는 비밀값 가리기를 적용했습니다. 걸린 규칙은 " +
            ", ".join(ctx["masked_hits"]) + "입니다.")
    else:
        add("인용한 문장에서 가려야 할 비밀값은 발견되지 않았습니다.")
    return "\n".join(lines)


# --- HTML -----------------------------------------------------------------

_CSS = """
:root {
  --bg: #f6f6f4;
  --surface: #ffffff;
  --surface-2: #f2f1ed;
  --border: #e4e2dc;
  --border-strong: #cfccc4;
  --text: #16150f;
  --text-2: #55534c;
  --text-3: #85837a;
  --accent: #2a78d6;
  --accent-soft: #e9f1fc;
  --warn: #c9531f;
  --warn-soft: #fbeee7;
  --radius: 14px;
  --shadow: 0 1px 2px rgba(16,15,15,.04), 0 8px 22px rgba(16,15,15,.05);
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #131312;
    --surface: #1c1c1a;
    --surface-2: #232321;
    --border: #33332f;
    --border-strong: #45443f;
    --text: #f7f7f4;
    --text-2: #bfbdb4;
    --text-3: #8d8b82;
    --accent: #4a94ea;
    --accent-soft: #17273a;
    --warn: #e08252;
    --warn-soft: #33211a;
    --shadow: 0 1px 2px rgba(0,0,0,.3), 0 8px 22px rgba(0,0,0,.28);
  }
}
:root[data-theme="dark"] {
  --bg: #131312; --surface: #1c1c1a; --surface-2: #232321;
  --border: #33332f; --border-strong: #45443f;
  --text: #f7f7f4; --text-2: #bfbdb4; --text-3: #8d8b82;
  --accent: #4a94ea; --accent-soft: #17273a;
  --warn: #e08252; --warn-soft: #33211a;
  --shadow: 0 1px 2px rgba(0,0,0,.3), 0 8px 22px rgba(0,0,0,.28);
}
* { box-sizing: border-box; }
/* 한글은 기본 설정에서 아무 글자에서나 줄이 바뀌어 단어가 잘린다.
   keep-all 을 걸어 어절 단위로만 줄이 바뀌게 한다. 긴 영문 경로처럼
   한 덩어리가 칸을 넘칠 때만 예외로 끊는다. */
html, body { word-break: keep-all; overflow-wrap: break-word; }
body {
  margin: 0; background: var(--bg); color: var(--text);
  font-family: "Pretendard", "Malgun Gothic", "Apple SD Gothic Neo", system-ui, sans-serif;
  line-height: 1.78; font-size: 15.5px; -webkit-font-smoothing: antialiased;
}
.shell { max-width: 1180px; margin: 0 auto; padding: 0 32px 120px; }

header.top { padding: 56px 0 22px; border-bottom: 1px solid var(--border); }
header.top h1 { font-size: 32px; line-height: 1.35; margin: 0 0 10px; letter-spacing: -.02em; }
header.top .eyebrow { font-size: 13px; color: var(--text-3); letter-spacing: .02em; margin-bottom: 18px; }
header.top p { margin: 0; color: var(--text-2); }

nav.chapters {
  position: sticky; top: 0; z-index: 20;
  display: flex; gap: 8px; flex-wrap: wrap; justify-content: center;
  padding: 14px 0; margin-bottom: 34px;
  background: var(--bg);
  border-bottom: 1px solid var(--border);
}
nav.chapters button {
  font: inherit; font-size: 14px; cursor: pointer;
  padding: 8px 16px; border-radius: 999px;
  border: 1px solid var(--border); background: var(--surface); color: var(--text-2);
  transition: background .15s, color .15s, border-color .15s;
}
nav.chapters button:hover { border-color: var(--border-strong); color: var(--text); }
nav.chapters button[aria-selected="true"] {
  background: var(--accent); border-color: var(--accent); color: #ffffff;
}

section.chapter { display: none; }
section.chapter.active { display: block; animation: rise .22s ease; }
@keyframes rise { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: none; } }

h2.chapter-title {
  font-size: 26px; margin: 6px 0 10px; letter-spacing: -.01em;
  padding-bottom: 14px; border-bottom: 2px solid var(--text);
}
.chapter-lede { color: var(--text-2); margin: 0 0 34px; }
h3 {
  font-size: 19px; margin: 48px 0 12px; letter-spacing: -.01em;
  padding-bottom: 8px; border-bottom: 1px solid var(--border);
}
h4 { font-size: 15.5px; margin: 26px 0 8px; }
p { margin: 12px 0; color: var(--text-2); }

.hero { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 26px 30px; margin: 26px 0 14px; box-shadow: var(--shadow); }
.hero-label { font-size: 13px; color: var(--text-3); letter-spacing: .02em; }
.hero-value { font-size: 56px; font-weight: 680; letter-spacing: -.03em; color: var(--accent); line-height: 1.15; margin-top: 2px; font-variant-numeric: tabular-nums; }
.hero-unit { font-size: 22px; font-weight: 500; color: var(--text-3); letter-spacing: 0; }
.hero-note { font-size: 13.5px; color: var(--text-2); margin-top: 10px; }
.metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(178px, 1fr)); gap: 12px; margin: 24px 0 8px; }
.metric { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 16px 18px; box-shadow: var(--shadow); }
.metric .label { font-size: 12.5px; color: var(--text-3); }
.metric .value { font-size: 27px; font-weight: 640; letter-spacing: -.02em; margin-top: 4px; color: var(--text); font-variant-numeric: tabular-nums; }
.metric .hint { font-size: 12.5px; color: var(--text-3); margin-top: 6px; line-height: 1.6; }

figure { margin: 18px 0 8px; background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 18px; box-shadow: var(--shadow); }
figure img { width: 100%; height: auto; display: block; border-radius: 8px; background: #fcfcfb; }
figcaption { font-size: 14px; color: var(--text-2); margin-top: 14px; line-height: 1.75; }

.tablewrap { overflow-x: auto; margin: 20px 0 28px; border: 1px solid var(--border); border-radius: var(--radius); background: var(--surface); box-shadow: var(--shadow); }
table { border-collapse: collapse; width: 100%; font-size: 14px; line-height: 1.7; }
th, td {
  text-align: left; padding: 13px 18px; vertical-align: top;
  border-bottom: 1px solid var(--border);
  word-break: keep-all; overflow-wrap: break-word;
}
tr:last-child td { border-bottom: none; }
th { color: var(--text-2); font-weight: 600; font-size: 13px; letter-spacing: .01em; background: var(--surface-2); white-space: nowrap; }
td.num { font-variant-numeric: tabular-nums; white-space: nowrap; }
/* 채점 기준표는 규칙 칸이 가장 넓어야 읽기 좋다. */
table.rubric { table-layout: fixed; }
table.rubric col.c-name { width: 13%; }
table.rubric col.c-max { width: 8%; }
table.rubric col.c-what { width: 24%; }
table.rubric col.c-how { width: 44%; }
table.rubric col.c-avg { width: 11%; }

details.item { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; margin: 8px 0; box-shadow: var(--shadow); overflow: hidden; }
details.item > summary { cursor: pointer; padding: 14px 18px; list-style: none; display: flex; gap: 12px; align-items: baseline; }
details.item > summary::-webkit-details-marker { display: none; }
details.item > summary::before { content: "\\25B8"; color: var(--text-3); font-size: 12px; flex: none; transition: transform .15s; }
details.item[open] > summary::before { transform: rotate(90deg); }
details.item > summary:hover { background: var(--surface-2); }
summary .title { flex: 1; color: var(--text); font-size: 14.5px; }
summary .score { flex: none; font-size: 12.5px; color: var(--text-3); font-variant-numeric: tabular-nums; }
.body { padding: 6px 18px 18px 42px; border-top: 1px solid var(--border); }
.fulltext { white-space: pre-wrap; word-break: break-word; background: var(--surface-2); border-radius: 10px; padding: 14px 16px; font-size: 14px; color: var(--text); margin: 12px 0; line-height: 1.75; }
.facts { font-size: 13.5px; color: var(--text-2); margin: 6px 0; }
.chips { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px; }
.chip { font-size: 12px; padding: 3px 10px; border-radius: 999px; background: var(--warn-soft); color: var(--warn); }
.chip.good { background: var(--accent-soft); color: var(--accent); }

.guide { background: var(--surface); border: 1px solid var(--border); border-left: 3px solid var(--accent); border-radius: 12px; padding: 18px 20px; margin: 16px 0; box-shadow: var(--shadow); }
.guide .step { font-size: 12.5px; color: var(--text-3); letter-spacing: .04em; }
.guide h4 { margin: 4px 0 10px; font-size: 17px; color: var(--text); }
.guide .do { background: var(--accent-soft); border-radius: 10px; padding: 12px 14px; margin-top: 12px; font-size: 14px; color: var(--text); line-height: 1.75; }

.pair { display: grid; gap: 10px; margin: 14px 0 24px; }
.pair .before, .pair .after { border-radius: 10px; padding: 13px 15px; font-size: 14px; line-height: 1.75; }
.pair .before { background: var(--surface-2); color: var(--text-2); }
.pair .after { background: var(--accent-soft); color: var(--text); border-left: 3px solid var(--accent); }
.pair .tag { display: block; font-size: 12px; color: var(--text-3); margin-bottom: 5px; }

.note {
  font-size: 14px; color: var(--text-2); background: var(--surface-2);
  border-left: 3px solid var(--accent); border-radius: 0 10px 10px 0;
  padding: 16px 20px; margin: 24px 0; line-height: 1.78;
}
.rules { margin: 4px 0 0; padding-left: 17px; color: var(--text-2); font-size: 13.5px; }
.rules li { margin: 6px 0; word-break: keep-all; }
footer.end { margin-top: 56px; padding-top: 22px; border-top: 1px solid var(--border); font-size: 13px; color: var(--text-3); }
"""

_JS = """
(function () {
  var buttons = Array.prototype.slice.call(document.querySelectorAll('nav.chapters button'));
  var sections = Array.prototype.slice.call(document.querySelectorAll('section.chapter'));
  function show(id) {
    sections.forEach(function (s) { s.classList.toggle('active', s.id === id); });
    buttons.forEach(function (b) { b.setAttribute('aria-selected', String(b.dataset.target === id)); });
    try { localStorage.setItem('promptaudit-chapter', id); } catch (e) {}
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }
  buttons.forEach(function (b) {
    b.addEventListener('click', function () { show(b.dataset.target); });
  });
  var saved = null;
  try { saved = localStorage.getItem('promptaudit-chapter'); } catch (e) {}
  show(saved && document.getElementById(saved) ? saved : sections[0].id);
})();
"""


def _esc(value: Any) -> str:
    return html.escape(str(value))


def _figure(ctx: dict[str, Any], key: str) -> list[str]:
    chart = ctx["charts"].get(key)
    if not chart:
        return []
    heading = ctx["headings"].get(key, key)
    return [
        "<h3>" + _esc(heading) + "</h3>",
        "<figure>",
        '<img alt="' + _esc(heading) + '" src="' + chart["data_uri"] + '">',
        "<figcaption>" + _esc(ctx["notes"].get(key, "")) + "</figcaption>",
        "</figure>",
    ]


def _item_list(cases: list[dict[str, Any]], tone: str) -> list[str]:
    out = []
    for case in cases:
        out.append('<details class="item">')
        out.append('<summary><span class="title">' + _esc(case["summary"]) +
                   '</span><span class="score">프롬프트 ' + _esc(case["prompt_score"]) +
                   " / 결과 " + _esc(case["outcome_score"]) + "</span></summary>")
        out.append('<div class="body">')
        out.append('<p class="facts">아래가 그때 실제로 입력했던 문장 전체입니다.</p>')
        out.append('<div class="fulltext">' + _esc(case["full"]) + "</div>")
        out.append('<p class="facts">그 뒤에 벌어진 일은 다음과 같습니다. ' +
                   _esc(case["happened"]) + ".</p>")
        out.append('<p class="facts">기록된 날짜는 ' + _esc(case["date"]) +
                   "이고 세션 번호는 " + _esc(case["session"]) + "입니다.</p>")
        if case["antipatterns"]:
            out.append('<div class="chips">')
            for name in case["antipatterns"]:
                out.append('<span class="chip">' + _esc(name) + "</span>")
            out.append("</div>")
        elif tone == "good":
            out.append('<div class="chips"><span class="chip good">걸린 실수 없음</span></div>')
        out.append("</div></details>")
    return out


def render_html(ctx: dict[str, Any]) -> str:
    s = ctx["stats"]
    out: list[str] = []
    add = out.append

    add("<title>프롬프트 평가 리포트</title>")
    add("<style>" + _CSS + "</style>")
    add('<div class="shell">')

    add('<header class="top">')
    add("<h1>프롬프트 평가 리포트</h1>")
    add('<div class="eyebrow">분석 대상 ' + _esc(s["project"]) + " &nbsp;|&nbsp; 만든 시각 " +
        _esc(ctx["generated_at"]) + "</div>")
    add("<p>이 리포트는 " + _esc(s["project"]) + " 프로젝트를 진행하면서 오간 대화 기록을 "
        "읽어 만든 것입니다. 사람이 직접 입력한 프롬프트 " + _esc(format(s["prompts"], ",")) +
        "개를 두 가지 기준으로 평가했습니다. 하나는 문장을 얼마나 잘 썼는지이고, 다른 하나는 "
        "그 문장이 실제로 원하는 결과를 만들어 냈는지입니다. 위쪽 버튼을 눌러 원하는 장으로 "
        "바로 이동할 수 있습니다.</p>")
    add("</header>")

    add('<nav class="chapters">')
    for target, label in (("ch1", "1장. 평가 지표"), ("ch2", "2장. 상세 분석"),
                          ("ch3", "3장. Feedback"), ("ch4", "4장. 채점 기준")):
        add('<button data-target="' + target + '" aria-selected="false">' + label + "</button>")
    add("</nav>")

    # 1장 -------------------------------------------------------------
    add('<section class="chapter" id="ch1">')
    add('<h2 class="chapter-title">1장. 평가 지표</h2>')
    add('<p class="chapter-lede">먼저 전체 그림을 숫자로 봅니다. 아래 값들은 모두 기록에서 '
        "직접 세어 낸 것이라, 몇 번을 다시 계산해도 같은 값이 나옵니다.</p>")

    add('<div class="hero">')
    add('<div class="hero-label">종합 점수</div>')
    add('<div class="hero-value">' + _esc(s["avg_total_score"]) +
        '<span class="hero-unit"> / 100</span></div>')
    add('<div class="hero-note">문장 점수 ' + _esc(s["avg_prompt_score"]) +
        "점의 절반인 " + _esc(s["prompt_half"]) + "점과, 결과 점수 " +
        _esc(s["avg_outcome_score"]) + "점의 절반인 " + _esc(s["outcome_half"]) +
        "점을 더한 값입니다. 한 숫자로 말할 때 쓰는 대표 점수이고, 어디를 고쳐야 "
        "하는지는 아래 두 점수를 따로 보셔야 합니다.</div>")
    add("</div>")

    metrics = [
        ("분석한 세션", str(s["sessions"]) + "개", "대화창 하나가 세션 하나입니다."),
        ("분석한 프롬프트", format(s["prompts"], ",") + "개", "사람이 직접 입력한 문장만 셌습니다."),
        ("평균 프롬프트 점수", str(s["avg_prompt_score"]), "100점 만점으로, 문장만 보고 매깁니다."),
        ("평균 결과 점수", str(s["avg_outcome_score"]), "100점 만점으로, 실제 결과를 보고 매깁니다."),
        ("재작업률", str(s["rework_rate"]) + "%", "바로 다음에 정정이 따라붙은 비율입니다."),
        ("중단률", str(s["interrupt_rate"]) + "%", "하던 작업을 사람이 끊은 비율입니다."),
        ("도구 실패율", str(s["tool_error_rate"]) + "%", "명령이 에러로 끝난 비율입니다."),
        ("컨텍스트 제공률", str(s["context_rate"]) + "%", "파일 경로나 에러를 함께 준 비율입니다."),
    ]
    add('<div class="metrics">')
    for label, value, hint in metrics:
        add('<div class="metric"><div class="label">' + _esc(label) +
            '</div><div class="value">' + _esc(value) +
            '</div><div class="hint">' + _esc(hint) + "</div></div>")
    add("</div>")

    if ctx["judged"]:
        j = ctx["judged"]
        add('<div class="note">표본 ' + _esc(j["count"]) + "개에 대해서는 문장을 한 번 더 "
            "꼼꼼히 읽고 채점했습니다. 결과를 감춘 채 문장만 보고 매긴 평균은 " +
            _esc(j["blind_avg"]) + "점이었고, 실제로 무슨 일이 있었는지까지 확인한 뒤 매긴 "
            "평균은 " + _esc(j["aware_avg"]) + "점이었습니다. 둘 다 " + _esc(j["max_total"]) +
            "점 만점입니다. 뒤쪽 점수가 더 낮다는 것은 문장만 보고 좋다고 판단하기가 "
            "그만큼 어렵다는 뜻입니다.</div>")

    for key in ("quadrant", "score_histogram", "rework_by_length",
                "tool_distribution", "weekly_trend", "antipatterns"):
        out.extend(_figure(ctx, key))
    add("</section>")

    # 2장 -------------------------------------------------------------
    add('<section class="chapter" id="ch2">')
    add('<h2 class="chapter-title">2장. 상세 분석</h2>')
    add('<p class="chapter-lede">여기서는 실제로 주고받았던 문장을 직접 봅니다. 각 항목의 '
        "제목을 누르면 그때 입력했던 문장 전체와 그 뒤에 무슨 일이 있었는지가 펼쳐집니다.</p>")

    add("<h3>잘 쓴 프롬프트</h3>")
    add("<p>문장 점수와 결과 점수가 모두 기준선을 넘은 경우입니다. 대부분 무엇을 다룰지 "
        "대상을 분명히 지정했거나, 하지 말아야 할 일을 미리 못 박아 두었다는 공통점이 "
        "있습니다. 앞으로도 이런 식으로 쓰시면 됩니다.</p>")
    out.extend(_item_list(ctx["cases"]["good"], "good"))

    add("<h3>못 쓴 프롬프트</h3>")
    add("<p>문장 점수와 결과 점수가 모두 기준선에 못 미친 경우입니다. 목록을 펼쳐 원문을 "
        "보시면 대부분 '무엇을'에 해당하는 대상이 빠져 있다는 점을 확인하실 수 있습니다. "
        "어떻게 고쳐 쓰면 좋을지는 3장에서 다룹니다.</p>")
    out.extend(_item_list(ctx["cases"]["bad"], "bad"))

    add("<h3>Claude의 문제</h3>")
    add("<p>아래는 사람이 문장을 충분히 잘 썼는데도 결과가 따라오지 않은 경우입니다. "
        "지시가 분명했는데도 엉뚱한 곳을 손대거나, 필요 이상으로 여러 번 오가거나, 결국 "
        "중간에 멈춘 사례들입니다. 이런 것은 프롬프트를 더 다듬는다고 해결되지 않으므로 "
        "받아들이는 쪽의 문제로 따로 구분해 두었습니다.</p>")
    out.extend(_item_list(ctx["cases"]["claude"], "claude"))

    add("<h3>분석에 쓰인 세션</h3>")
    add("<p>어떤 대화를 골라 분석했는지 밝혀 둡니다. 작업 폴더가 프로젝트 폴더로 기록된 "
        "대화와, 폴더는 다르지만 대화 내용에 프로젝트 이야기가 반복해서 나온 대화를 함께 "
        "골랐습니다.</p>")
    add('<div class="tablewrap"><table>')
    add("<tr><th>세션 번호</th><th>시작한 날</th><th>프롬프트 수</th><th>고른 이유</th></tr>")
    for row in ctx["sessions"]:
        add("<tr><td>" + _esc(row["id"]) + '</td><td class="num">' + _esc(row["started"]) +
            '</td><td class="num">' + _esc(row["prompts"]) + "</td><td>" +
            _esc(row["reason"]) + "</td></tr>")
    add("</table></div>")
    add("</section>")

    # 3장 -------------------------------------------------------------
    add('<section class="chapter" id="ch3">')
    add('<h2 class="chapter-title">3장. Feedback</h2>')
    add('<p class="chapter-lede">이 장은 앞에서 본 숫자를 바탕으로, 다음에 무엇을 어떻게 '
        "바꾸면 되는지를 알려 드립니다. 아래 항목은 미리 정해 둔 기준선을 넘긴 것만 "
        "나타나므로, 이번 기록에서 실제로 문제가 된 것들입니다. 위에 있을수록 고쳤을 때 "
        "효과가 큽니다.</p>")

    for i, card in enumerate(ctx["cards"][:5], 1):
        add('<div class="guide">')
        add('<div class="step">' + _esc(i) + "번째로 할 일</div>")
        add("<h4>" + _esc(card.title) + "</h4>")
        add("<p>" + _esc(card.why) + "</p>")
        add('<div class="do"><strong>이렇게 하세요.</strong> ' + _esc(card.how) + "</div>")
        add("</div>")

    rest = ctx["cards"][5:]
    if rest:
        add("<h3>그 밖에 기준선을 넘긴 항목</h3>")
        add("<p>아래 항목도 기준선을 넘겼습니다. 위의 다섯 가지를 먼저 고친 뒤에 차례로 "
            "살펴보시면 됩니다.</p>")
        add('<div class="tablewrap"><table>')
        add("<tr><th>할 일</th><th>왜 필요한가</th></tr>")
        for card in rest:
            add("<tr><td>" + _esc(card.title) + "</td><td>" + _esc(card.why) + "</td></tr>")
        add("</table></div>")

    if ctx["rewrites"]:
        add("<h3>이렇게 다시 써 보세요</h3>")
        add("<p>실제로 결과가 좋지 않았던 문장을 골라, 같은 뜻을 더 잘 전달하는 문장으로 "
            "고쳐 보았습니다. 위쪽이 그때 보냈던 문장이고 아래쪽이 고쳐 쓴 문장입니다.</p>")
        for item in ctx["rewrites"]:
            add('<div class="pair">')
            add('<div class="before"><span class="tag">그때 보낸 문장</span>' +
                _esc(item["before"]) + "</div>")
            add('<div class="after"><span class="tag">이렇게 고치면 좋습니다</span>' +
                _esc(item["after"]) + "</div>")
            if item["verdict"]:
                add('<p class="facts">이유는 이렇습니다. ' + _esc(item["verdict"]) + "</p>")
            add("</div>")

    add("<h3>프롬프트를 쓸 때 지킬 다섯 가지</h3>")
    add("<p>지금까지의 내용을 실제로 문장을 쓸 때 순서대로 적용할 수 있도록 정리했습니다. "
        "이 다섯 가지만 지켜도 4장의 채점 기준에서 대부분의 점수를 받게 됩니다.</p>")
    basics = [
        ("무엇을 다룰지 대상을 먼저 적습니다.",
         "'그거 고쳐 줘'가 아니라 '방금 만든 로그인 화면의 오류 문구를 고쳐 줘'처럼 대상을 "
         "문장 안에 남겨 둡니다. 대화가 길어지면 '그거'가 무엇인지 서로 어긋나기 쉽습니다."),
        ("판단에 필요한 재료를 함께 붙입니다.",
         "고칠 파일의 경로를 그대로 적고, 에러가 났다면 요약하지 말고 원문을 그대로 붙여 "
         "넣습니다. 이것만으로 대상을 찾느라 헤매는 시간이 크게 줄어듭니다."),
        ("건드리면 안 되는 곳을 미리 못 박습니다.",
         "'이 파일만 고쳐', '기존 함수는 그대로 둬'처럼 한 구절을 덧붙입니다. 의도하지 않은 "
         "곳까지 바뀌면 되돌리는 데 드는 품이 더 큽니다."),
        ("한 번에 한 가지만 시킵니다.",
         "'구현하고 테스트하고 문서까지'처럼 묶어서 보내면 일부만 처리되고 나머지가 빠지기 "
         "쉽습니다. 첫 단계 결과를 확인한 뒤 다음을 시키는 편이 결국 더 빠릅니다."),
        ("무엇을 만족하면 끝인지 알려 줍니다.",
         "'테스트가 통과하면 완료', '화면에 목록이 보이면 완료'처럼 판정 기준을 주면 스스로 "
         "확인하고 마무리할 수 있어, 사람이 매번 눈으로 검사하지 않아도 됩니다."),
    ]
    for i, (title, detail) in enumerate(basics, 1):
        add('<div class="guide">')
        add('<div class="step">규칙 ' + _esc(i) + "</div>")
        add("<h4>" + _esc(title) + "</h4>")
        add("<p>" + _esc(detail) + "</p>")
        add("</div>")
    add("</section>")

    # 4장 -------------------------------------------------------------
    add('<section class="chapter" id="ch4">')
    add('<h2 class="chapter-title">4장. 채점 기준</h2>')
    add('<p class="chapter-lede">앞에서 나온 점수가 어떻게 매겨졌는지를 남김없이 밝혀 '
        "둡니다. 점수는 두 종류이고 각각 100점 만점입니다. 하나는 문장만 보고 매기는 "
        "프롬프트 점수이고, 다른 하나는 그 뒤에 실제로 벌어진 일을 보고 매기는 결과 "
        "점수입니다. 두 점수는 서로 다른 근거로 계산되므로 따로 읽으셔야 합니다.</p>")

    add("<h3>프롬프트 점수 100점의 구성</h3>")
    add("<p>아래 다섯 항목의 배점을 모두 더하면 정확히 100점이 됩니다. 표의 맨 오른쪽은 "
        "이번 분석에서 실제로 받은 평균 점수입니다.</p>")
    add('<div class="tablewrap"><table class="rubric">')
    add('<colgroup><col class="c-name"><col class="c-max"><col class="c-what">'
        '<col class="c-how"><col class="c-avg"></colgroup>')
    add("<tr><th>항목</th><th>배점</th><th>무엇을 보는가</th><th>어떻게 매기는가</th><th>평균 획득</th></tr>")
    for item in RUBRIC:
        rules = "".join("<li>" + _esc(rule) + "</li>" for rule in item["rules"])
        add("<tr><td><strong>" + _esc(item["label"]) + '</strong></td><td class="num">' +
            _esc(item["max"]) + "점</td><td>" + _esc(item["question"]) +
            '</td><td><ul class="rules">' + rules + '</ul></td><td class="num">' +
            _esc(ctx["component_avg"][item["key"]]) + "점</td></tr>")
    add("</table></div>")
    out.extend(_figure(ctx, "score_breakdown"))
    out.extend(_figure(ctx, "score_gap"))

    add("<h3>결과 점수 100점의 구성</h3>")
    add("<p>결과 점수는 문장을 전혀 보지 않고, 그 프롬프트를 보낸 뒤 실제로 무슨 일이 "
        "있었는지만 가지고 매깁니다. 네 항목의 배점을 더하면 100점이 됩니다.</p>")
    add('<div class="tablewrap"><table class="rubric">')
    add('<colgroup><col class="c-name"><col class="c-max"><col class="c-what">'
        '<col class="c-how"><col class="c-avg"></colgroup>')
    add("<tr><th>항목</th><th>배점</th><th>무엇을 보는가</th><th>어떻게 매기는가</th><th>평균 획득</th></tr>")
    for item in OUTCOME_RUBRIC:
        rules = "".join("<li>" + _esc(rule) + "</li>" for rule in item["rules"])
        add("<tr><td><strong>" + _esc(item["label"]) + '</strong></td><td class="num">' +
            _esc(item["max"]) + "점</td><td>" + _esc(item["question"]) +
            '</td><td><ul class="rules">' + rules + '</ul></td><td class="num">' +
            _esc(ctx["outcome_avg"][item["key"]]) + "점</td></tr>")
    add("</table></div>")
    out.extend(_figure(ctx, "outcome_breakdown"))

    add("<h3>종합 점수를 만드는 방법</h3>")
    add("<p>위의 두 점수는 서로 다른 것을 재기 때문에 그대로 더하면 200점이 되어 버립니다. "
        "그래서 각각의 절반씩만 가져와 더합니다. 두 축을 똑같이 중요하게 본다는 뜻이고, "
        "이렇게 하면 합계가 정확히 100점 만점이 됩니다.</p>")
    add('<div class="tablewrap"><table>')
    add("<tr><th>항목</th><th>점수 (100점 척도)</th><th>종합에 들어가는 몫</th></tr>")
    add("<tr><td>프롬프트 점수</td><td class=\"num\">" + _esc(s["avg_prompt_score"]) +
        '점</td><td class="num">' + _esc(s["prompt_half"]) + "점</td></tr>")
    add("<tr><td>결과 점수</td><td class=\"num\">" + _esc(s["avg_outcome_score"]) +
        '점</td><td class="num">' + _esc(s["outcome_half"]) + "점</td></tr>")
    add("<tr><td><strong>종합 점수</strong></td><td class=\"num\">—</td>"
        '<td class="num"><strong>' + _esc(s["avg_total_score"]) + "점</strong></td></tr>")
    add("</table></div>")
    add("<p>표의 오른쪽 칸만 세로로 더하면 " + _esc(s["prompt_half"]) + " + " +
        _esc(s["outcome_half"]) + " = " + _esc(s["avg_total_score"]) +
        "점이 됩니다. 왼쪽 칸의 점수는 각 축을 100점 만점으로 봤을 때의 값이라, "
        "그 축 하나만 놓고 잘했는지 못했는지를 볼 때 씁니다.</p>")
    add("<p>이 종합 점수는 "
        "전체를 한눈에 보기 위한 것이지, 무엇을 고쳐야 하는지를 알려 주지는 못합니다. "
        "고칠 곳을 찾으려면 위의 항목별 점수를 보셔야 합니다. 예를 들어 종합 점수가 "
        "같은 두 프롬프트라도, 하나는 문장이 부실했는데 앞 대화 덕에 넘어간 경우이고 "
        "다른 하나는 문장은 좋았는데 결과가 따라오지 않은 경우일 수 있습니다.</p>")

    add("<h3>합격선을 60점으로 잡은 이유</h3>")
    add("<p>2장에서 잘 쓴 프롬프트와 못 쓴 프롬프트를 나눈 기준은 100점 만점에 60점입니다. "
        "다섯 항목 가운데 절반을 조금 넘게 지켰다면 최소한의 형식은 갖춘 것으로 보자는 "
        "뜻입니다. 이 기준선은 절대적인 것이 아니라 읽기 편하도록 정한 약속이므로, 점수 "
        "자체보다는 어느 항목에서 점수를 잃었는지를 보시는 편이 도움이 됩니다.</p>")

    add('<div class="note">이 리포트를 읽을 때 한 가지 주의할 점이 있습니다. 결과 점수에는 '
        "과제의 난이도가 섞여 있습니다. 어려운 일일수록 주고받는 횟수가 늘고 실패도 잦은데, "
        "그것이 반드시 프롬프트를 잘못 썼기 때문은 아닙니다. 따라서 두 점수가 함께 움직인다고 "
        "해서 하나가 다른 하나의 원인이라고 단정해서는 안 됩니다.</div>")
    add("</section>")

    add('<footer class="end">')
    if ctx["masked_hits"]:
        add("인용한 문장에는 비밀값 가리기를 적용했습니다. 걸린 규칙은 " +
            _esc(", ".join(ctx["masked_hits"])) + "입니다. 그래도 발표 자료로 옮기기 전에 "
            "한 번 더 눈으로 확인하시기 바랍니다.")
    else:
        add("인용한 문장에서 가려야 할 비밀값은 발견되지 않았습니다.")
    add("</footer>")

    add("</div>")
    add("<script>" + _JS + "</script>")
    return "\n".join(out)


def write_all(analysis, chart_files, out_dir: Path,
              judged: dict[str, Any] | None = None) -> dict[str, Path]:
    ctx = build_context(analysis, chart_files, judged)
    out_dir.mkdir(parents=True, exist_ok=True)

    html_path = out_dir / "report.html"
    md_path = out_dir / "report.md"
    scores_path = out_dir / "scores.json"

    html_path.write_text(render_html(ctx), encoding="utf-8")
    md_path.write_text(render_markdown(ctx), encoding="utf-8")

    scores_path.write_text(json.dumps({
        "summary": ctx["stats"],
        "prompt_rubric": [dict(item) for item in RUBRIC],
        "outcome_rubric": [dict(item) for item in OUTCOME_RUBRIC],
        "component_average": ctx["component_avg"],
        "outcome_average": ctx["outcome_avg"],
        "rows": [
            {
                "session": row.prompt.session_id[:8],
                "index": row.prompt.index,
                "prompt_score": round(row.prompt_score, 1),
                "score_components": row.metrics.score_components,
                "outcome": row.outcome.to_dict(),
                "metrics": row.metrics.to_dict(),
            }
            for row in analysis.rows
        ],
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    return {"html": html_path, "markdown": md_path, "scores": scores_path}
