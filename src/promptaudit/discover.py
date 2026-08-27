"""로컬에 쌓인 모든 세션 기록을 훑어 분석할 만한 후보를 찾아낸다.

이 프로그램을 처음 쓰는 사람은 자기 컴퓨터에 어떤 대화가 얼마나 남아 있는지
모른다. 그래서 실행하면 먼저 기록 전체를 훑어 작업 폴더별로 묶어 보여 주고,
그중에서 무엇을 분석할지 고르게 한다.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .loader import DEFAULT_PROJECTS_DIR, is_human_prompt, iter_raw_records, parse_timestamp
from .selector import PROJECTS, strip_system_text

# 작업 폴더를 프로젝트 이름으로 접을 때, 이 폴더들은 그 자체가 프로젝트가 아니라
# 프로젝트들을 담아 두는 상자다. 그래서 한 단계 더 들어간 이름을 쓴다.
CONTAINER_DIRS = {"dev", "lab", "projects", "workspace", "repos", "src", "code", "work"}


@dataclass
class Candidate:
    """분석 대상 후보 하나. 보통 프로젝트 폴더 하나에 해당한다."""

    label: str
    cwd_prefix: str
    sessions: set[str] = field(default_factory=set)
    prompts: int = 0
    first_seen: datetime | None = None
    last_seen: datetime | None = None

    @property
    def key(self) -> str:
        return re.sub(r"[^a-z0-9]+", "", self.label.lower())

    @property
    def session_count(self) -> int:
        return len(self.sessions)

    @property
    def period(self) -> str:
        if not self.first_seen or not self.last_seen:
            return "-"
        start = self.first_seen.strftime("%Y-%m-%d")
        end = self.last_seen.strftime("%Y-%m-%d")
        return start if start == end else start + " ~ " + end

    def observe(self, session_id: str, stamp: datetime | None) -> None:
        self.sessions.add(session_id)
        if stamp is None:
            return
        if self.first_seen is None or stamp < self.first_seen:
            self.first_seen = stamp
        if self.last_seen is None or stamp > self.last_seen:
            self.last_seen = stamp


def project_label(cwd: str) -> tuple[str, str] | None:
    """작업 폴더 경로에서 프로젝트 이름과 그 폴더 경로를 뽑아낸다.

    예를 들어 ``C:\\dev\\ReviewTicketFullstack\\backend\\Server`` 는
    ``("ReviewTicketFullstack", "C:\\dev\\ReviewTicketFullstack")`` 이 된다.
    """
    if not cwd:
        return None
    normalized = cwd.replace("/", "\\").rstrip("\\")
    parts = [p for p in normalized.split("\\") if p]
    if len(parts) < 2:
        return None

    # 드라이브 문자(C:)를 뺀 나머지에서 첫 번째 의미 있는 폴더를 찾는다.
    body = parts[1:] if re.fullmatch(r"[A-Za-z]:", parts[0]) else parts
    if not body:
        return None

    index = 0
    while index < len(body) - 1 and body[index].lower() in CONTAINER_DIRS:
        index += 1
    label = body[index]
    prefix = "\\".join(parts[: len(parts) - len(body) + index + 1])
    return label, prefix


def is_home_path(cwd: str) -> bool:
    """사용자 홈 폴더나 바탕화면처럼 프로젝트가 아닌 자리인지 판단한다.

    데스크톱 앱은 폴더를 따로 열지 않으면 작업 폴더를 홈 아래로 남긴다. 그런
    경로는 프로젝트 이름으로 쓸 수 없다.
    """
    normalized = cwd.replace("/", "\\").lower()
    return bool(re.match(r"^[a-z]:\\users\\[^\\]+\\?$", normalized)) or any(
        part in normalized
        for part in ("\\바탕 화면", "\\desktop", "\\onedrive\\바탕", "\\문서", "\\documents")
    )


def matching_preset(cwds: set[str], prompt_bodies: list[str]):
    """이 세션이 미리 등록해 둔 프로젝트 중 하나에 해당하는지 본다.

    선별 단계와 똑같은 규칙(작업 폴더 또는 본문 키워드 두 번 이상)을 쓴다. 목록에
    보여 주는 수와 실제로 분석하는 수가 어긋나지 않게 하기 위해서다.
    """
    for preset in PROJECTS.values():
        if any(cwd.startswith(prefix) for cwd in cwds for prefix in preset.cwd_prefixes):
            return preset
        pattern = preset.keyword_pattern
        hits = sum(1 for body in prompt_bodies if pattern.search(strip_system_text(body)))
        if hits >= preset.min_keyword_hits:
            return preset
    return None


def scan(projects_dir: Path | None = None, min_prompts: int = 3) -> list[Candidate]:
    """기록 전체를 훑어 후보 목록을 만든다.

    사람이 친 프롬프트 레코드에는 작업 폴더가 거의 항상 홈 폴더로 남는다. 실제
    프로젝트 경로는 도구를 실행한 레코드에만 들어 있다. 그래서 세션 안의 모든
    레코드에서 폴더를 모은 뒤, 그 세션의 프롬프트 수를 거기에 붙여 준다.
    """
    root = projects_dir or DEFAULT_PROJECTS_DIR
    found: dict[str, Candidate] = {}

    for path in sorted(root.glob("**/*.jsonl")):
        session_id = path.stem
        folder_hits: Counter = Counter()
        prompt_count = 0
        first: datetime | None = None
        last: datetime | None = None

        prompt_bodies: list[str] = []
        all_cwds: set[str] = set()

        for record in iter_raw_records(path):
            stamp = parse_timestamp(record.get("timestamp"))
            if stamp is not None:
                if first is None or stamp < first:
                    first = stamp
                if last is None or stamp > last:
                    last = stamp
            if is_human_prompt(record):
                prompt_count += 1
                prompt_bodies.append((record.get("message") or {}).get("content") or "")
            cwd = record.get("cwd")
            if not cwd:
                continue
            all_cwds.add(cwd.lower())
            if is_home_path(cwd):
                continue
            parsed = project_label(cwd)
            if parsed is not None:
                folder_hits[parsed] += 1

        if prompt_count < 1:
            continue

        preset = matching_preset(all_cwds, prompt_bodies)
        if preset is not None:
            # 미리 등록해 둔 프로젝트에 걸리면 그 이름 하나로만 센다. 목록에 뜨는
            # 수와 실제로 분석한 수가 달라지면 안 되기 때문이다.
            targets = [(preset.name, preset.cwd_prefixes[0])]
        elif folder_hits:
            # 한 세션에서 여러 프로젝트를 오갔을 수 있으므로 상위 세 개까지 인정한다.
            targets = [key for key, _ in folder_hits.most_common(3)]
        else:
            targets = [("작업 폴더를 지정하지 않은 대화", "")]

        for label, prefix in targets:
            candidate = found.get(prefix or label)
            if candidate is None:
                candidate = Candidate(label=label, cwd_prefix=prefix)
                found[prefix or label] = candidate
            candidate.prompts += prompt_count
            candidate.observe(session_id, first)
            candidate.observe(session_id, last)

    candidates = [c for c in found.values() if c.prompts >= min_prompts]
    candidates.sort(key=lambda c: (-c.prompts, c.label))
    return candidates


def merge_similar(candidates: list[Candidate]) -> list[Candidate]:
    """이름이 겹치는 후보를 하나로 합친다.

    같은 프로젝트인데 폴더를 옮겨 다닌 경우가 있다. 예를 들어 ReviewTicket 과
    ReviewTicketFullstack 은 사람 눈에는 같은 프로젝트다. 짧은 쪽 이름으로
    시작하는 다른 후보가 있으면 하나로 묶어 준다.
    """
    by_length = sorted(candidates, key=lambda c: len(c.label))
    merged: list[Candidate] = []
    absorbed: set[str] = set()

    for base in by_length:
        if base.cwd_prefix in absorbed:
            continue
        group = [base]
        for other in by_length:
            if other is base or other.cwd_prefix in absorbed:
                continue
            if other.label.lower().startswith(base.label.lower()):
                group.append(other)
                absorbed.add(other.cwd_prefix)
        if len(group) == 1:
            merged.append(base)
            continue

        # 합칠 때는 프롬프트가 가장 많은 쪽 이름을 대표로 쓴다.
        leader = max(group, key=lambda c: c.prompts)
        combined = Candidate(label=leader.label, cwd_prefix=base.cwd_prefix)
        for member in group:
            combined.prompts += member.prompts
            combined.sessions |= member.sessions
            combined.observe(next(iter(member.sessions), ""), member.first_seen)
            combined.observe(next(iter(member.sessions), ""), member.last_seen)
        combined.sessions.discard("")
        merged.append(combined)

    merged.sort(key=lambda c: (-c.prompts, c.label))
    return merged


def _width(text: str) -> int:
    """한글은 터미널에서 두 칸을 차지하므로 그 폭을 세어 준다."""
    total = 0
    for char in text:
        total += 2 if ord(char) > 0x1100 and not char.isascii() else 1
    return total


def _pad(text: str, width: int) -> str:
    return text + " " * max(0, width - _width(text))


def format_table(candidates: list[Candidate]) -> str:
    """고르기 좋게 번호를 붙인 표를 만든다."""
    lines = ["", "  번호  " + _pad("이름", 32) + "세션   프롬프트   기간",
             "  " + "-" * 70]
    for i, c in enumerate(candidates, 1):
        label = c.label
        while _width(label) > 30:
            label = label[:-1]
        lines.append(
            "  " + format(i, ">3") + ".  " + _pad(label, 32)
            + format(c.session_count, ">4") + "   "
            + format(c.prompts, ">7") + "   " + c.period
        )
    lines.append("")
    return "\n".join(lines)


def choose(candidates: list[Candidate]) -> Candidate | None:
    """사용자에게 무엇을 분석할지 물어본다."""
    if not candidates:
        return None

    print("컴퓨터에 남아 있는 대화 기록을 살펴봤다. 아래가 분석할 수 있는 대상이다.")
    print(format_table(candidates))
    print("분석하고 싶은 것의 번호나 이름을 입력하면 된다. 그냥 엔터를 누르면 1번을 고른다.")

    try:
        answer = input("  선택 > ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return None

    if not answer:
        return candidates[0]
    if answer.isdigit():
        index = int(answer) - 1
        if 0 <= index < len(candidates):
            return candidates[index]
        print("목록에 없는 번호다. 1번을 고른 것으로 하겠다.")
        return candidates[0]

    lowered = answer.lower()
    for candidate in candidates:
        if candidate.label.lower() == lowered or candidate.key == lowered:
            return candidate
    for candidate in candidates:
        if lowered in candidate.label.lower():
            return candidate
    print("이름이 목록과 맞지 않는다. 1번을 고른 것으로 하겠다.")
    return candidates[0]
