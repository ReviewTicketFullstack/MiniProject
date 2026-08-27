"""분석 대상 세션을 골라낸다.

두 가지 근거를 합집합으로 쓴다.

1. cwd prefix - 세션 레코드의 작업 폴더가 프로젝트 경로 아래인 경우
2. 본문 키워드 - 데스크톱 앱에서 폴더를 열지 않고 작업하면 cwd가 바탕화면으로
   남기 때문에, 사람이 친 프롬프트 본문에 프로젝트 이름이 반복해 나오면 포함한다.

키워드 스캔을 레코드 전체에 걸면 안 된다. 세션마다 MEMORY.md가 컨텍스트로
주입되고 그 안에 프로젝트 이름이 들어 있어, 거의 모든 세션이 걸려 버린다.
사람 프롬프트 본문에만, system-reminder 블록을 뺀 뒤 적용한다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .loader import Session, iter_session_paths, load_session

SYSTEM_REMINDER = re.compile(r"<system-reminder>.*?</system-reminder>", re.S)


@dataclass(frozen=True)
class ProjectFilter:
    name: str
    cwd_prefixes: tuple[str, ...]
    keywords: tuple[str, ...]
    min_keyword_hits: int = 2

    @property
    def keyword_pattern(self) -> re.Pattern[str]:
        joined = "|".join(re.escape(k) for k in self.keywords)
        return re.compile(joined, re.IGNORECASE)


PROJECTS: dict[str, ProjectFilter] = {
    "reviewticket": ProjectFilter(
        name="ReviewTicketFullstack",
        cwd_prefixes=(
            r"c:\dev\reviewticketfullstack",
            r"c:\dev\reviewticket",
        ),
        keywords=("reviewticket", "리뷰티켓", "리뷰 티켓", "review_ticket"),
    ),
    "mycloset": ProjectFilter(
        name="MyCloset",
        cwd_prefixes=(r"c:\dev\mycloset",),
        keywords=("mycloset", "마이클로젯", "마이클로셋"),
    ),
}


def strip_system_text(text: str) -> str:
    return SYSTEM_REMINDER.sub(" ", text)


@dataclass
class SelectionResult:
    session: Session
    by_cwd: bool
    keyword_hits: int

    @property
    def reason(self) -> str:
        if self.by_cwd and self.keyword_hits:
            return "cwd+keyword"
        if self.by_cwd:
            return "cwd"
        return "keyword"


def evaluate(session: Session, project: ProjectFilter) -> SelectionResult | None:
    by_cwd = any(
        cwd.lower().startswith(prefix)
        for cwd in session.cwds
        for prefix in project.cwd_prefixes
    )

    pattern = project.keyword_pattern
    hits = 0
    for prompt in session.prompts:
        body = strip_system_text(prompt.text)
        if pattern.search(body):
            hits += 1

    if by_cwd or hits >= project.min_keyword_hits:
        return SelectionResult(session=session, by_cwd=by_cwd, keyword_hits=hits)
    return None


def preset_for(candidate) -> ProjectFilter | None:
    """목록에서 고른 대상이 미리 등록해 둔 프로젝트와 같은 것인지 확인한다.

    등록된 규칙에는 '리뷰티켓' 같은 한글 키워드가 더 들어 있어, 폴더를 열지 않고
    바탕화면에서 작업한 세션까지 잡아낸다. 같은 프로젝트를 목록에서 골랐을 때와
    이름으로 지정했을 때의 결과가 달라지면 안 되므로, 같은 것이면 등록된 규칙을
    쓴다.
    """
    key = candidate.key
    if len(key) < 3:
        return None
    for name, preset in PROJECTS.items():
        if key.startswith(name) or name.startswith(key):
            return preset
    return None


def filter_from_candidate(candidate) -> ProjectFilter:
    """탐색 단계에서 고른 후보를 그대로 선별 규칙으로 바꾼다.

    미리 등록해 둔 프로젝트가 아니어도 쓸 수 있어야 하므로 폴더 이름을 그대로
    키워드로 삼는다. 이름에 밑줄이나 붙임표가 섞여 있으면 그 변형도 함께 찾는다.
    """
    preset = preset_for(candidate)
    if preset is not None:
        return preset

    label = candidate.label
    keywords = {label, label.replace("_", " "), label.replace("-", " ")}
    if candidate.key and candidate.key != label.lower():
        keywords.add(candidate.key)
    return ProjectFilter(
        name=label,
        cwd_prefixes=(candidate.cwd_prefix.lower(),),
        keywords=tuple(sorted(k for k in keywords if len(k) >= 3)),
    )


def resolve(project) -> ProjectFilter:
    """프로젝트 키를 받든 규칙을 통째로 받든 규칙으로 통일해 돌려준다."""
    if isinstance(project, ProjectFilter):
        return project
    return PROJECTS[project]


def select_sessions(
    project_key,
    projects_dir: Path | None = None,
) -> list[SelectionResult]:
    project = resolve(project_key)
    paths = (
        iter_session_paths(projects_dir) if projects_dir else iter_session_paths()
    )
    selected: list[SelectionResult] = []
    for path in paths:
        session = load_session(path)
        if not session.prompts:
            continue
        result = evaluate(session, project)
        if result is not None:
            selected.append(result)
    selected.sort(key=lambda r: r.session.started_at or r.session.path.stat().st_mtime)
    return selected
