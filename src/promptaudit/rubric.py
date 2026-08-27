"""LLM 채점 계층.

같은 프롬프트를 두 번 채점한다.

  블라인드   프롬프트 문장만 보여 준다. 결과는 감춘다.
  결과 인지  그 뒤에 실제로 벌어진 일까지 붙여서 보여 준다.

두 점수의 차가 "잘 쓴 줄 알았는데 안 통한 프롬프트" 목록이 된다.

채점 주체는 두 갈래로 쓸 수 있다.

  skill 모드 (기본)  채점 대기열을 JSON으로 뽑아 두면 Claude Code가 스킬 안에서
                     직접 읽고 채점 결과 JSON을 써 준다. API 키가 필요 없다.
  api 모드           anthropic SDK로 직접 호출한다. 키가 있을 때만 쓴다.
"""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .masking import excerpt

AXES = {
    "goal_clarity": "목표 명확성 - 무엇을 원하는지 한 번에 읽히는가",
    "context": "컨텍스트 충분성 - 파일, 에러, 현재 상태를 줬는가",
    "scope": "제약과 범위 - 건드리면 안 되는 것을 명시했는가",
    "verification": "검증 기준 - 완료 판단 기준을 제시했는가",
    "decomposition": "작업 분해 - 한 프롬프트에 과하게 몰아넣지 않았는가",
    "reusability": "재사용성 - 규칙으로 승격시킬 만한 지시인가",
}

MAX_TOTAL = len(AXES) * 5  # 30점 만점


def prompt_key(text: str) -> str:
    return hashlib.sha1(text.strip().encode("utf-8")).hexdigest()[:12]


@dataclass
class SampleItem:
    key: str
    session_id: str
    index: int
    text: str
    reason: str
    outcome_context: dict[str, Any]

    def to_queue_entry(self) -> dict[str, Any]:
        return {
            "id": self.key,
            "session": self.session_id[:8],
            "index": self.index,
            "sampled_because": self.reason,
            "prompt": self.text,
            "what_happened": self.outcome_context,
        }


def _context_of(row) -> dict[str, Any]:
    m = row.metrics
    tools = {}
    for call in row.prompt.tool_calls:
        tools[call.name] = tools.get(call.name, 0) + 1
    if m.followed_by_correction:
        reaction = "다음 프롬프트가 정정이었다"
    elif m.followed_by_approval:
        reaction = "다음 프롬프트가 승인이었다"
    else:
        reaction = "다음 프롬프트는 중립이었다"
    return {
        "assistant_turns": m.assistant_turns,
        "tool_calls": sorted(tools.items(), key=lambda kv: -kv[1])[:6],
        "tool_errors": m.tool_error_count,
        "files_edited": m.edited_file_count,
        "repeated_edit_max": row.outcome.repeated_edit_max,
        "committed_files": row.outcome.committed_files,
        "interrupted_by_user": m.interrupted,
        "user_reaction": reaction,
        "outcome_score": row.outcome_score,
    }


def select_sample(analysis, size: int = 180, seed: int = 7) -> list[SampleItem]:
    """층화 표본. 실패 신호가 붙은 것은 전부, 나머지는 양 끝과 무작위로 채운다."""
    rng = random.Random(seed)
    rows = analysis.rows
    picked: dict[str, SampleItem] = {}

    def add(row, reason: str) -> None:
        text = excerpt(row.prompt.text, limit=1200)
        if not text.strip():
            return
        key = prompt_key(row.prompt.text)
        if key in picked:
            return
        picked[key] = SampleItem(
            key=key,
            session_id=row.prompt.session_id,
            index=row.prompt.index,
            text=text,
            reason=reason,
            outcome_context=_context_of(row),
        )

    failures = [r for r in rows if r.metrics.followed_by_correction or r.metrics.interrupted]
    for row in failures[: size // 2]:
        add(row, "재작업 또는 중단 신호")

    ranked = sorted(rows, key=lambda r: r.prompt_score)
    for row in ranked[:25]:
        add(row, "프롬프트 점수 하위")
    for row in ranked[-25:]:
        add(row, "프롬프트 점수 상위")

    pool = [r for r in rows if prompt_key(r.prompt.text) not in picked]
    rng.shuffle(pool)
    for row in pool:
        if len(picked) >= size:
            break
        add(row, "무작위 표본")

    return list(picked.values())[:size]


QUEUE_INSTRUCTIONS = {
    "how_to_score": (
        "각 프롬프트를 두 번 채점한다. blind 채점에서는 prompt 필드만 읽고 "
        "what_happened 필드는 절대 보지 않는다. aware 채점에서는 둘 다 읽는다. "
        "여섯 축을 각각 1~5점으로 매기고, 근거 한 문장과 개선 재작성본을 붙인다."
    ),
    "axes": AXES,
    "output_schema": {
        "<id>": {
            "blind": {axis: "1~5" for axis in AXES},
            "aware": {axis: "1~5" for axis in AXES},
            "verdict": "한 문장 근거",
            "rewrite": "같은 의도를 더 잘 전달하는 프롬프트 재작성본",
        }
    },
}


def write_queue(items: Iterable[SampleItem], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "instructions": QUEUE_INSTRUCTIONS,
        "items": [item.to_queue_entry() for item in items],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _total(scores: dict[str, Any] | None) -> float | None:
    if not isinstance(scores, dict):
        return None
    values = []
    for axis in AXES:
        try:
            values.append(float(scores.get(axis)))
        except (TypeError, ValueError):
            return None
    return sum(values)


def load_results(path: Path) -> dict[str, dict[str, Any]]:
    """채점 결과 JSON을 읽어 합계까지 계산해 둔다. 없으면 빈 dict."""
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    if isinstance(raw, dict) and "results" in raw:
        raw = raw["results"]
    if not isinstance(raw, dict):
        return {}

    out: dict[str, dict[str, Any]] = {}
    for key, value in raw.items():
        if not isinstance(value, dict):
            continue
        entry = dict(value)
        blind_total = _total(value.get("blind"))
        aware_total = _total(value.get("aware"))
        if blind_total is not None:
            entry["blind_total"] = blind_total
        if aware_total is not None:
            entry["aware_total"] = aware_total
        out[key] = entry
    return out


def merge_cache(cache_path: Path, results: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """이미 채점한 프롬프트는 다시 채점하지 않도록 해시 키로 쌓아 둔다."""
    cached = load_results(cache_path)
    cached.update(results)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        json.dumps(cached, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return cached


def pending(items: Iterable[SampleItem], cache: dict[str, Any]) -> list[SampleItem]:
    return [item for item in items if item.key not in cache]
