"""세션 선별부터 점수 산출까지 묶는다. 여기까지는 LLM을 쓰지 않는다."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from statistics import mean
from typing import Any

from .loader import PromptUnit
from .metrics import PromptMetrics, compute_session
from .outcome import GitIndex, OutcomeScore, score_prompt
from .selector import PROJECTS, SelectionResult, resolve, select_sessions

# 대표 점수를 만들 때 두 축을 섞는 비율. 어느 한쪽을 더 중히 볼 이유가 없어
# 반씩 나눈다. 이 값을 바꾸면 리포트의 대표 점수도 함께 바뀐다.
TOTAL_WEIGHTS = {"prompt": 0.5, "outcome": 0.5}

REPOS: dict[str, list[Path]] = {
    "reviewticket": [Path(r"C:\dev\ReviewTicketFullstack")],
    "mycloset": [Path(r"C:\dev\mycloset")],
}


@dataclass
class Row:
    """프롬프트 하나에 대한 모든 것."""

    prompt: PromptUnit
    metrics: PromptMetrics
    outcome: OutcomeScore

    @property
    def prompt_score(self) -> float:
        return self.metrics.prompt_score

    @property
    def outcome_score(self) -> float:
        return self.outcome.total

    @property
    def total_score(self) -> float:
        """대표 점수. 두 축을 반씩 섞어 100점 하나로 만든다.

        발표나 요약에서 "몇 점인가"를 한 숫자로 말하기 위한 값이다. 어디를
        고쳐야 하는지는 이 숫자로 알 수 없으므로, 분석은 여전히 두 축을 따로
        본다.
        """
        return round(self.prompt_score * TOTAL_WEIGHTS["prompt"]
                     + self.outcome_score * TOTAL_WEIGHTS["outcome"], 1)

    @property
    def quadrant(self) -> str:
        p = self.prompt_score >= 60
        o = self.outcome_score >= 60
        if p and o:
            return "good_good"
        if p and not o:
            return "good_bad"
        if not p and o:
            return "bad_good"
        return "bad_bad"


@dataclass
class Analysis:
    project_key: str
    project_name: str
    selections: list[SelectionResult]
    rows: list[Row]
    tool_counter: Counter = field(default_factory=Counter)

    # --- 요약 지표 -------------------------------------------------------
    @property
    def session_count(self) -> int:
        return len(self.selections)

    @property
    def prompt_count(self) -> int:
        return len(self.rows)

    @property
    def rework_rate(self) -> float:
        if not self.rows:
            return 0.0
        n = sum(1 for r in self.rows if r.metrics.followed_by_correction)
        return n / len(self.rows) * 100

    @property
    def interrupt_rate(self) -> float:
        if not self.rows:
            return 0.0
        n = sum(1 for r in self.rows if r.metrics.interrupted)
        return n / len(self.rows) * 100

    @property
    def tool_error_rate(self) -> float:
        calls = sum(r.metrics.tool_call_count for r in self.rows)
        errs = sum(r.metrics.tool_error_count for r in self.rows)
        return (errs / calls * 100) if calls else 0.0

    @property
    def approval_rate(self) -> float:
        if not self.rows:
            return 0.0
        n = sum(1 for r in self.rows if r.metrics.followed_by_approval)
        return n / len(self.rows) * 100

    @property
    def avg_prompt_score(self) -> float:
        return mean([r.prompt_score for r in self.rows]) if self.rows else 0.0

    @property
    def avg_outcome_score(self) -> float:
        return mean([r.outcome_score for r in self.rows]) if self.rows else 0.0

    @property
    def avg_total_score(self) -> float:
        """리포트 맨 앞에 내세우는 대표 점수. 100점 만점 하나로 말할 때 쓴다."""
        return mean([r.total_score for r in self.rows]) if self.rows else 0.0

    @property
    def context_rate(self) -> float:
        """파일 경로나 코드/에러를 함께 준 프롬프트 비율."""
        if not self.rows:
            return 0.0
        n = sum(
            1 for r in self.rows
            if r.metrics.has_file_path or r.metrics.has_code_block or r.metrics.has_error_paste
        )
        return n / len(self.rows) * 100

    @property
    def quadrants(self) -> Counter:
        return Counter(r.quadrant for r in self.rows)

    @property
    def antipattern_counter(self) -> Counter:
        c: Counter = Counter()
        for row in self.rows:
            for name in row.metrics.antipatterns:
                c[name] += 1
        return c

    def summary(self) -> dict[str, Any]:
        return {
            "project": self.project_name,
            "sessions": self.session_count,
            "prompts": self.prompt_count,
            "avg_prompt_score": round(self.avg_prompt_score, 1),
            "avg_outcome_score": round(self.avg_outcome_score, 1),
            "avg_total_score": round(self.avg_total_score, 1),
            "total_weights": dict(TOTAL_WEIGHTS),
            # 종합 점수를 "절반씩 더한 값"으로 보여 줄 때 쓰는 몫
            "prompt_half": round(self.avg_prompt_score * TOTAL_WEIGHTS["prompt"], 1),
            "outcome_half": round(self.avg_outcome_score * TOTAL_WEIGHTS["outcome"], 1),
            "rework_rate": round(self.rework_rate, 1),
            "interrupt_rate": round(self.interrupt_rate, 1),
            "tool_error_rate": round(self.tool_error_rate, 1),
            "approval_rate": round(self.approval_rate, 1),
            "context_rate": round(self.context_rate, 1),
            "quadrants": dict(self.quadrants),
            "top_tools": self.tool_counter.most_common(10),
            "antipatterns": self.antipattern_counter.most_common(),
        }


def repo_candidates(project) -> list[Path]:
    """결과물이 살아남았는지 대조할 저장소 경로를 찾는다.

    미리 등록해 둔 프로젝트면 그 경로를 쓰고, 그렇지 않으면 선별 규칙에 들어
    있는 작업 폴더가 저장소인지 직접 확인한다.
    """
    if isinstance(project, str) and project in REPOS:
        return REPOS[project]
    rule = resolve(project)
    paths = []
    for prefix in rule.cwd_prefixes:
        path = Path(prefix)
        if (path / ".git").exists():
            paths.append(path)
    return paths


def run(project_key, projects_dir: Path | None = None) -> Analysis:
    selections = select_sessions(project_key, projects_dir)
    rule = resolve(project_key)

    git_indexes = [GitIndex.load(p) for p in repo_candidates(project_key)]
    git = next((g for g in git_indexes if g.file_commits), None)

    rows: list[Row] = []
    tools: Counter = Counter()
    for sel in selections:
        prompts = sel.session.prompts
        metrics = compute_session(prompts)
        for prompt, m in zip(prompts, metrics):
            rows.append(Row(prompt=prompt, metrics=m, outcome=score_prompt(prompt, m, git)))
            for call in prompt.tool_calls:
                tools[call.name] += 1

    return Analysis(
        project_key=project_key if isinstance(project_key, str) else rule.name,
        project_name=rule.name,
        selections=selections,
        rows=rows,
        tool_counter=tools,
    )
