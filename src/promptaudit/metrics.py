"""규칙 기반 프롬프트 지표. LLM을 쓰지 않으므로 몇 번을 돌려도 같은 값이 나온다."""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Any

from .loader import PromptUnit

# 사용자가 요구를 흐리게 만드는 표현
VAGUE_WORDS = ("적당히", "알아서", "대충", "아무거나", "좀 더", "잘 좀", "등등", "같은 거", "느낌으로")

# 다음 프롬프트가 이걸로 시작하면 앞 프롬프트가 원하는 결과를 못 냈다는 신호
CORRECTION_MARKERS = (
    "아니", "그게 아니라", "그거 말고", "말고", "다시", "틀렸", "잘못", "되돌려",
    "원복", "아까", "왜 이렇게", "이게 아니", "그런 거 아니", "안 되잖", "안되잖",
)

# 반대로 이걸로 시작하면 앞 결과를 받아들였다는 신호
APPROVAL_MARKERS = (
    "좋아", "좋다", "굿", "됐다", "됐어", "맞아", "그대로", "오케이", "ok", "okay",
    "완벽", "고마", "감사", "잘했", "훌륭", "이제 됐",
)

# 범위를 좁히는 표현이 있으면 모델이 엉뚱한 파일을 건드릴 여지가 준다
CONSTRAINT_MARKERS = (
    "하지 마", "하지마", "말고", "빼고", "제외", "건들지", "건드리지", "유지",
    "그대로 둬", "만 ", "만.", "까지만", "부터만", "외에는",
)

REQUEST_VERBS = (
    "해줘", "해 줘", "만들", "고쳐", "수정", "추가", "삭제", "지워", "확인",
    "분석", "작성", "구현", "알려", "보여", "실행", "설명", "정리", "바꿔", "찾아",
)

# 무엇을 만족하면 끝난 것인지를 미리 알려 주는 표현
VERIFY_MARKERS = (
    "테스트", "통과하면", "통과할", "검증", "완료 조건", "되면 완료", "확인되면",
    "기준으로", "성공하면", "에러 없이", "정상 동작", "확인하고 알려", "될 때까지",
)

_EXT = "py|ts|tsx|js|jsx|java|sql|json|md|html|css|yml|yaml|xml|sh|ps1|txt|vue|tsv|csv"
PATH_RE = re.compile(
    # 윈도우 절대 경로(C:\dev\...), 유닉스 경로, 확장자 붙은 파일 이름을 모두 잡는다.
    r"(?:[A-Za-z]:[\\/][^\s\"']+"
    r"|(?:\./|/|src/|app/|backend/|frontend/)[\w./\\-]+"
    r"|[\w.-]+\.(?:" + _EXT + r")\b)"
)
CODE_BLOCK_RE = re.compile(r"```")
ERROR_RE = re.compile(r"(Traceback|Exception|ERROR|error:|Caused by|at line \d+|stack trace)", re.IGNORECASE)
URL_RE = re.compile(r"https?://\S+")


# 리포트 4장에서 그대로 보여 주는 채점 기준표. 다섯 항목을 더하면 100점이다.
RUBRIC: tuple[dict[str, Any], ...] = (
    {
        "key": "goal",
        "label": "목표 명확성",
        "max": 25,
        "question": "무엇을 해 달라는 것인지가 한 번에 읽히는가",
        "rules": [
            "요청하는 동작이 문장에 있으면 10점 (예: 고쳐 줘, 만들어 줘, 알려 줘)",
            "대상이 무엇인지 알 수 있으면 10점 (파일 경로가 있거나 설명이 40자 이상)",
            "'적당히', '알아서' 같은 흐릿한 표현이 하나도 없으면 5점",
            "대상 없이 15자 미만으로 짧으면 8점을 뺀다",
        ],
    },
    {
        "key": "context",
        "label": "컨텍스트 충분성",
        "max": 25,
        "question": "판단에 필요한 재료를 함께 건넸는가",
        "rules": [
            "파일 경로를 적었으면 10점",
            "코드 블록이나 에러 원문을 붙였으면 10점",
            "참고 주소를 함께 줬으면 5점",
        ],
    },
    {
        "key": "scope",
        "label": "범위 제한",
        "max": 20,
        "question": "건드리면 안 되는 곳을 미리 못 박았는가",
        "rules": [
            "'이 파일만', '기존 것은 그대로 둬' 같은 제한이 있으면 20점",
            "제한이 없는데 파일까지 고치게 했으면 0점",
            "제한은 없지만 파일을 고치지 않는 질문이면 8점",
        ],
    },
    {
        "key": "decomposition",
        "label": "작업 분해",
        "max": 20,
        "question": "한 번에 하나씩 시켰는가",
        "rules": [
            "요청하는 동작이 두 개 이하이면 20점",
            "세 개이면 10점, 네 개 이상이면 4점",
            "1,500자를 넘는 긴 지시이면 6점을 뺀다",
        ],
    },
    {
        "key": "verification",
        "label": "완료 기준",
        "max": 10,
        "question": "무엇을 만족하면 끝인지 알려 줬는가",
        "rules": [
            "'테스트가 통과하면', '에러 없이 뜨면'처럼 판정 기준이 있으면 10점",
            "기준이 없으면 0점",
        ],
    },
)

OUTCOME_RUBRIC: tuple[dict[str, Any], ...] = (
    {
        "key": "immediate",
        "label": "즉시 성공",
        "max": 35,
        "question": "시킨 일이 곧바로 제대로 돌아갔는가",
        "rules": [
            "도구 실행이 모두 성공했으면 만점에 가깝다",
            "실패한 실행이 있으면 그 비율만큼 깎는다",
            "사용자가 중간에 작업을 끊었으면 크게 깎는다",
        ],
    },
    {
        "key": "convergence",
        "label": "수렴 비용",
        "max": 25,
        "question": "적은 품으로 끝났는가",
        "rules": [
            "주고받은 턴이 적을수록 높다",
            "같은 파일을 여러 번 고쳤으면 그만큼 깎는다",
            "출력이 지나치게 길었으면 조금 깎는다",
        ],
    },
    {
        "key": "persistence",
        "label": "지속성",
        "max": 20,
        "question": "그때 만든 결과물이 실제로 살아남았는가",
        "rules": [
            "고친 파일이 이후 커밋에 들어갔으면 높다",
            "파일을 고치지 않은 질문형 프롬프트는 중간값을 준다",
        ],
    },
    {
        "key": "acceptance",
        "label": "사용자 수용",
        "max": 20,
        "question": "사람이 그 결과를 받아들였는가",
        "rules": [
            "다음 프롬프트가 '좋아', '그대로 가자'처럼 승인이면 만점",
            "특별한 반응 없이 넘어갔으면 중간값",
            "'아니', '그게 아니라'처럼 정정이면 크게 깎는다",
        ],
    },
)


def _count_any(text: str, needles: tuple[str, ...]) -> int:
    return sum(text.count(n) for n in needles)


def _starts_with_any(text: str, needles: tuple[str, ...]) -> bool:
    head = text.strip()[:24].lower()
    return any(head.startswith(n.lower()) or n.lower() in head for n in needles)


@dataclass
class PromptMetrics:
    session_id: str
    index: int
    timestamp: str | None
    char_len: int
    approx_tokens: int
    has_code_block: bool
    has_file_path: bool
    has_error_paste: bool
    has_url: bool
    vague_count: int
    constraint_count: int
    request_verb_count: int
    question_count: int
    has_verification: bool

    assistant_turns: int
    tool_call_count: int
    tool_error_count: int
    output_tokens: int
    duration_seconds: float | None
    edited_file_count: int
    interrupted: bool

    followed_by_correction: bool
    followed_by_approval: bool

    # 안티패턴 플래그
    ap_vague_no_context: bool
    ap_no_scope_on_edit: bool
    ap_multi_demand: bool
    ap_too_terse: bool
    ap_wall_of_text: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def antipatterns(self) -> list[str]:
        names = []
        if self.ap_vague_no_context:
            names.append("모호어 사용 + 컨텍스트 없음")
        if self.ap_no_scope_on_edit:
            names.append("범위 미지정 상태로 파일 수정 지시")
        if self.ap_multi_demand:
            names.append("한 프롬프트에 요구 여러 개")
        if self.ap_too_terse:
            names.append("지시가 지나치게 짧음")
        if self.ap_wall_of_text:
            names.append("한 번에 너무 긴 지시")
        return names

    @property
    def score_components(self) -> dict[str, float]:
        """100점을 다섯 항목에 나눠 담는다. 결과는 보지 않고 문장만 본다."""
        # 목표 명확성 (25점) - 무엇을 원하는지가 한 번에 읽히는가
        goal = 0.0
        if self.request_verb_count:
            goal += 10
        if self.has_file_path or self.char_len >= 40:
            goal += 10
        if self.vague_count == 0:
            goal += 5
        if self.ap_too_terse:
            goal = max(0.0, goal - 8)

        # 컨텍스트 충분성 (25점) - 판단에 필요한 재료를 함께 줬는가
        context = 0.0
        if self.has_file_path:
            context += 10
        if self.has_code_block or self.has_error_paste:
            context += 10
        if self.has_url:
            context += 5

        # 범위 제한 (20점) - 건드리면 안 되는 것을 밝혔는가
        if self.constraint_count:
            scope = 20.0
        elif self.edited_file_count:
            scope = 0.0
        else:
            scope = 8.0

        # 작업 분해 (20점) - 한 번에 하나씩 시켰는가
        if self.request_verb_count <= 2:
            decomposition = 20.0
        elif self.request_verb_count == 3:
            decomposition = 10.0
        else:
            decomposition = 4.0
        if self.ap_wall_of_text:
            decomposition -= 6
        decomposition = max(0.0, decomposition)

        # 완료 기준 (10점) - 무엇을 만족하면 끝인지 알려 줬는가
        verification = 10.0 if self.has_verification else 0.0

        return {
            "goal": goal,
            "context": context,
            "scope": scope,
            "decomposition": decomposition,
            "verification": verification,
        }

    @property
    def prompt_score(self) -> float:
        """프롬프트 자체의 품질. 100점 만점. 결과는 보지 않는다."""
        return round(sum(self.score_components.values()), 1)


def compute(prompt: PromptUnit, next_prompt: PromptUnit | None) -> PromptMetrics:
    text = prompt.text
    stripped = text.strip()

    has_path = bool(PATH_RE.search(text))
    has_code = bool(CODE_BLOCK_RE.search(text))
    has_error = bool(ERROR_RE.search(text))
    vague = _count_any(text, VAGUE_WORDS)
    constraints = _count_any(text, CONSTRAINT_MARKERS)
    verbs = _count_any(text, REQUEST_VERBS)
    edited = len(prompt.edited_files)

    ap_vague_no_context = vague > 0 and not (has_path or has_code or has_error)
    ap_no_scope_on_edit = edited > 0 and constraints == 0 and not has_path
    ap_multi_demand = verbs >= 3 or text.count("그리고") >= 2
    ap_too_terse = len(stripped) < 15 and not (has_path or has_code)
    ap_wall_of_text = len(stripped) > 1500

    return PromptMetrics(
        session_id=prompt.session_id,
        index=prompt.index,
        timestamp=prompt.timestamp.isoformat() if prompt.timestamp else None,
        char_len=len(stripped),
        approx_tokens=max(1, len(stripped) // 2),
        has_code_block=has_code,
        has_file_path=has_path,
        has_error_paste=has_error,
        has_url=bool(URL_RE.search(text)),
        vague_count=vague,
        constraint_count=constraints,
        request_verb_count=verbs,
        question_count=text.count("?") + text.count("？"),
        has_verification=_count_any(text, VERIFY_MARKERS) > 0,
        assistant_turns=prompt.assistant_turns,
        tool_call_count=len(prompt.tool_calls),
        tool_error_count=prompt.tool_error_count,
        output_tokens=prompt.output_tokens,
        duration_seconds=prompt.duration_seconds,
        edited_file_count=edited,
        interrupted=prompt.interrupted,
        followed_by_correction=(
            _starts_with_any(next_prompt.text, CORRECTION_MARKERS) if next_prompt else False
        ),
        followed_by_approval=(
            _starts_with_any(next_prompt.text, APPROVAL_MARKERS) if next_prompt else False
        ),
        ap_vague_no_context=ap_vague_no_context,
        ap_no_scope_on_edit=ap_no_scope_on_edit,
        ap_multi_demand=ap_multi_demand,
        ap_too_terse=ap_too_terse,
        ap_wall_of_text=ap_wall_of_text,
    )


def compute_session(prompts: list[PromptUnit]) -> list[PromptMetrics]:
    out = []
    for i, prompt in enumerate(prompts):
        nxt = prompts[i + 1] if i + 1 < len(prompts) else None
        out.append(compute(prompt, nxt))
    return out
