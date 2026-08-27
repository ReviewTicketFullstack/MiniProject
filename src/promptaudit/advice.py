"""조언 계층.

일반론이 매번 똑같이 나오면 시스템이라고 부를 수 없다. 지표마다 임계값을
걸어 두고, 넘긴 항목에 해당하는 카드만 발동시킨다. 발동한 카드는 자기가
어떤 수치 때문에 떴는지를 근거로 달고 나온다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class AdviceCard:
    key: str
    title: str
    why: str
    how: str
    severity: float  # 0~1, 임계값을 얼마나 크게 넘겼는가
    weight: float    # 카드 자체의 중요도

    @property
    def priority(self) -> float:
        return self.severity * self.weight


@dataclass
class Rule:
    key: str
    title: str
    weight: float
    threshold: float
    higher_is_worse: bool
    measure: Callable[[dict[str, Any]], float]
    why: Callable[[float], str]
    how: str

    def evaluate(self, stats: dict[str, Any]) -> AdviceCard | None:
        value = self.measure(stats)
        if self.higher_is_worse:
            if value < self.threshold:
                return None
            severity = min(1.0, (value - self.threshold) / max(self.threshold, 1e-6))
        else:
            if value > self.threshold:
                return None
            severity = min(1.0, (self.threshold - value) / max(self.threshold, 1e-6))
        return AdviceCard(
            key=self.key,
            title=self.title,
            why=self.why(value),
            how=self.how,
            severity=max(0.15, severity),
            weight=self.weight,
        )


def _ratio(stats: dict[str, Any], name: str) -> float:
    total = stats.get("prompts") or 1
    return stats.get("antipattern_counts", {}).get(name, 0) / total * 100


RULES: list[Rule] = [
    Rule(
        key="rework",
        title="요구를 한 번에 다 넣지 말고 쪼개서 던진다",
        weight=1.0,
        threshold=8.0,
        higher_is_worse=True,
        measure=lambda s: s["rework_rate"],
        why=lambda v: (
            "프롬프트 " + format(v, ".1f") + "%가 바로 다음 턴에서 정정을 받았다. "
            "열 번에 한 번꼴로 같은 일을 두 번 시킨 셈이다."
        ),
        how=(
            "요구가 두 개 이상이면 프롬프트를 나눈다. 특히 '구현하고 테스트하고 "
            "문서까지' 형태는 첫 단계 결과를 확인한 뒤 다음을 시키는 편이 총 턴 수가 적다."
        ),
    ),
    Rule(
        key="context",
        title="파일 경로와 에러 원문을 프롬프트에 붙인다",
        weight=1.0,
        threshold=40.0,
        higher_is_worse=False,
        measure=lambda s: s["context_rate"],
        why=lambda v: (
            "파일 경로나 코드, 에러를 함께 준 프롬프트가 " + format(v, ".1f") + "%뿐이다. "
            "나머지는 모델이 대상을 먼저 찾아야 해서 탐색 턴이 늘어난다."
        ),
        how=(
            "고칠 대상이 정해져 있으면 경로를 그대로 적는다. 에러가 났으면 요약하지 말고 "
            "원문을 붙인다. 탐색 비용이 그대로 줄어든다."
        ),
    ),
    Rule(
        key="interrupt",
        title="실행 전에 무엇을 할 것인지 먼저 말하게 한다",
        weight=0.9,
        threshold=5.0,
        higher_is_worse=True,
        measure=lambda s: s["interrupt_rate"],
        why=lambda v: (
            "프롬프트 " + format(v, ".1f") + "%에서 진행 중인 작업을 직접 끊었다. "
            "끊었다는 것은 엉뚱한 방향으로 가고 있었다는 뜻이다."
        ),
        how=(
            "범위가 큰 작업은 '먼저 계획만 말해 줘, 승인하면 실행'을 붙인다. "
            "중단은 그때까지 쓴 토큰을 그대로 버리는 일이다."
        ),
    ),
    Rule(
        key="tool_error",
        title="실행 전 상태 확인을 지시에 포함한다",
        weight=0.8,
        threshold=4.0,
        higher_is_worse=True,
        measure=lambda s: s["tool_error_rate"],
        why=lambda v: (
            "도구 실행의 " + format(v, ".1f") + "%가 에러로 끝났다. 없는 경로, 꺼져 있는 "
            "서비스, 잘못된 인코딩처럼 미리 확인하면 피할 수 있는 것이 대부분이다."
        ),
        how=(
            "명령을 시키기 전에 대상이 존재하는지 확인하라고 한 줄 덧붙인다. "
            "특히 경로와 인코딩은 이 프로젝트에서 반복해 걸린 지점이다."
        ),
    ),
    Rule(
        key="approval",
        title="완료 판단 기준을 프롬프트에 적는다",
        weight=0.85,
        threshold=10.0,
        higher_is_worse=False,
        measure=lambda s: s["approval_rate"],
        why=lambda v: (
            "다음 프롬프트가 명시적 승인이었던 경우가 " + format(v, ".1f") + "%뿐이다. "
            "끝났는지 아닌지를 매번 사람이 눈으로 확인하고 있다는 뜻이다."
        ),
        how=(
            "'테스트가 통과하면 완료', '이 화면에서 값이 보이면 완료'처럼 판정 기준을 "
            "미리 준다. 모델이 스스로 검증하고 끝낼 수 있게 된다."
        ),
    ),
    Rule(
        key="multi_demand",
        title="한 프롬프트에 목표 하나만 담는다",
        weight=0.75,
        threshold=8.0,
        higher_is_worse=True,
        measure=lambda s: _ratio(s, "한 프롬프트에 요구 여러 개"),
        why=lambda v: (
            "프롬프트 " + format(v, ".1f") + "%에 요청 동사가 세 개 이상 들어 있다. "
            "이런 프롬프트는 일부만 처리되고 나머지가 누락되기 쉽다."
        ),
        how="요구를 나열해야 한다면 번호를 붙이고, 어느 것부터 할지 순서를 지정한다.",
    ),
    Rule(
        key="terse",
        title="한 줄 지시에는 대상을 함께 적는다",
        weight=0.7,
        threshold=7.0,
        higher_is_worse=True,
        measure=lambda s: _ratio(s, "지시가 지나치게 짧음"),
        why=lambda v: (
            "프롬프트 " + format(v, ".1f") + "%가 대상도 없이 열다섯 자 미만이다. "
            "직전 맥락이 살아 있을 때만 통하고, 세션이 길어지면 어긋난다."
        ),
        how="'그거 고쳐 줘' 대신 '방금 만든 A 파일의 B 함수를 고쳐 줘'로 대상을 되짚는다.",
    ),
    Rule(
        key="no_scope",
        title="건드리지 말아야 할 범위를 먼저 못 박는다",
        weight=0.8,
        threshold=8.0,
        higher_is_worse=True,
        measure=lambda s: _ratio(s, "범위 미지정 상태로 파일 수정 지시"),
        why=lambda v: (
            "파일을 수정한 프롬프트 중 " + format(v, ".1f") + "%가 범위 제한 없이 나갔다. "
            "의도하지 않은 파일까지 바뀌면 되돌리는 비용이 더 크다."
        ),
        how="'이 파일만', '기존 함수는 그대로 두고'처럼 경계를 한 구절로 붙인다.",
    ),
    Rule(
        key="wall_of_text",
        title="긴 사양은 프롬프트가 아니라 문서로 넘긴다",
        weight=0.6,
        threshold=4.0,
        higher_is_worse=True,
        measure=lambda s: _ratio(s, "한 번에 너무 긴 지시"),
        why=lambda v: (
            "프롬프트 " + format(v, ".1f") + "%가 1,500자를 넘는다. 길어질수록 어느 요구가 "
            "핵심인지 흐려진다."
        ),
        how="사양은 파일로 만들어 경로만 주고, 프롬프트에는 이번에 할 일만 적는다.",
    ),
    Rule(
        key="context_dependent",
        title="맥락에 기대는 프롬프트 비중을 줄인다",
        weight=0.7,
        threshold=35.0,
        higher_is_worse=True,
        measure=lambda s: (
            s.get("quadrants", {}).get("bad_good", 0) / (s.get("prompts") or 1) * 100
        ),
        why=lambda v: (
            "문장 자체는 부실한데 결과는 괜찮았던 프롬프트가 " + format(v, ".1f") + "%다. "
            "앞 턴의 맥락이 받쳐 줘서 넘어간 것이라 세션이 바뀌면 재현되지 않는다."
        ),
        how=(
            "새 세션에서 다시 시켰을 때도 통할 문장인지 한 번 자문한다. "
            "자주 쓰는 지시는 CLAUDE.md 규칙이나 스킬로 승격시킨다."
        ),
    ),
]


def build(analysis) -> list[AdviceCard]:
    stats = analysis.summary()
    stats["antipattern_counts"] = dict(analysis.antipattern_counter)
    cards = []
    for rule in RULES:
        card = rule.evaluate(stats)
        if card is not None:
            cards.append(card)
    cards.sort(key=lambda c: -c.priority)
    return cards
