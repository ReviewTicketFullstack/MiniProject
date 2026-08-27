"""Claude Code JSONL 트랜스크립트를 읽어 프롬프트 단위로 정규화한다.

세션 파일은 한 줄에 레코드 하나씩 들어 있는 JSONL이며, 인코딩은 UTF-8이다.
PowerShell의 Get-Content 기본 인코딩으로 읽으면 한글이 깨지고 JSON 파싱까지
실패하므로 반드시 여기서만 파일을 연다.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

DEFAULT_PROJECTS_DIR = Path.home() / ".claude" / "projects"

# 사람이 직접 입력한 프롬프트만 이 값을 가진다. 도구 실행 결과도 type "user"로
# 들어오기 때문에 이 필터가 없으면 지표가 통째로 오염된다.
HUMAN_ORIGIN = "human"


def iter_raw_records(path: Path) -> Iterator[dict[str, Any]]:
    """JSONL 한 줄씩 파싱한다. 깨진 줄은 조용히 건너뛴다."""
    with path.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def text_of(content: Any) -> str:
    """message.content를 순수 텍스트로 편다.

    content는 문자열일 수도 있고 블록 리스트일 수도 있다. 텍스트 블록만 모은다.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text") or "")
        return "\n".join(parts)
    return ""


def is_human_prompt(record: dict[str, Any]) -> bool:
    if record.get("type") != "user":
        return False
    if record.get("isSidechain"):
        # 서브에이전트 대화. 사람이 쓴 프롬프트가 아니다.
        return False
    origin = record.get("origin") or {}
    if origin.get("kind") != HUMAN_ORIGIN:
        return False
    content = (record.get("message") or {}).get("content")
    return isinstance(content, str) and bool(content.strip())


@dataclass
class ToolCall:
    name: str
    input: dict[str, Any]
    tool_use_id: str | None = None
    is_error: bool | None = None  # tool_result와 짝지은 뒤 채워진다


@dataclass
class PromptUnit:
    """사람 프롬프트 하나 + 다음 사람 프롬프트 전까지 벌어진 모든 일."""

    session_id: str
    index: int  # 세션 내 순번
    text: str
    timestamp: datetime | None
    cwd: str | None
    git_branch: str | None

    assistant_text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    output_tokens: int = 0
    input_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    assistant_turns: int = 0
    interrupted: bool = False
    end_timestamp: datetime | None = None

    @property
    def duration_seconds(self) -> float | None:
        if self.timestamp and self.end_timestamp:
            return (self.end_timestamp - self.timestamp).total_seconds()
        return None

    @property
    def tool_error_count(self) -> int:
        return sum(1 for call in self.tool_calls if call.is_error)

    @property
    def edited_files(self) -> list[str]:
        files = []
        for call in self.tool_calls:
            if call.name in ("Edit", "Write", "NotebookEdit"):
                path = call.input.get("file_path")
                if path:
                    files.append(path)
        return files

    @property
    def bash_commands(self) -> list[str]:
        commands = []
        for call in self.tool_calls:
            if call.name in ("Bash", "PowerShell"):
                command = call.input.get("command")
                if command:
                    commands.append(str(command))
        return commands


@dataclass
class Session:
    path: Path
    session_id: str
    cwds: set[str] = field(default_factory=set)
    prompts: list[PromptUnit] = field(default_factory=list)
    started_at: datetime | None = None
    ended_at: datetime | None = None
    sidechain_records: int = 0

    @property
    def title(self) -> str:
        return self.path.stem[:8]


def load_session(path: Path) -> Session:
    """세션 파일 하나를 프롬프트 단위 리스트로 접는다."""
    session = Session(path=path, session_id=path.stem)
    current: PromptUnit | None = None
    pending_tools: dict[str, ToolCall] = {}

    for record in iter_raw_records(path):
        cwd = record.get("cwd")
        if cwd:
            session.cwds.add(cwd)

        stamp = parse_timestamp(record.get("timestamp"))
        if stamp:
            if session.started_at is None or stamp < session.started_at:
                session.started_at = stamp
            if session.ended_at is None or stamp > session.ended_at:
                session.ended_at = stamp

        if record.get("isSidechain"):
            session.sidechain_records += 1
            continue

        if is_human_prompt(record):
            current = PromptUnit(
                session_id=session.session_id,
                index=len(session.prompts),
                text=(record.get("message") or {}).get("content", ""),
                timestamp=stamp,
                cwd=cwd,
                git_branch=record.get("gitBranch"),
            )
            session.prompts.append(current)
            pending_tools = {}
            continue

        if current is None:
            continue

        record_type = record.get("type")
        message = record.get("message") or {}

        if record_type == "assistant":
            current.assistant_turns += 1
            if stamp:
                current.end_timestamp = stamp
            current.assistant_text += "\n" + text_of(message.get("content"))

            usage = message.get("usage") or {}
            current.output_tokens += usage.get("output_tokens") or 0
            current.input_tokens += usage.get("input_tokens") or 0
            current.cache_read_tokens += usage.get("cache_read_input_tokens") or 0
            current.cache_creation_tokens += usage.get("cache_creation_input_tokens") or 0

            for block in message.get("content") or []:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    call = ToolCall(
                        name=block.get("name") or "?",
                        input=block.get("input") or {},
                        tool_use_id=block.get("id"),
                    )
                    current.tool_calls.append(call)
                    if call.tool_use_id:
                        pending_tools[call.tool_use_id] = call

        elif record_type == "user":
            # 사람 프롬프트가 아닌 user 레코드 = 도구 결과 또는 중단 표시
            content = message.get("content")
            if isinstance(content, list):
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    if block.get("type") == "tool_result":
                        call = pending_tools.get(block.get("tool_use_id"))
                        if call is not None:
                            call.is_error = bool(block.get("is_error"))
                    elif block.get("type") == "text":
                        if "[Request interrupted" in (block.get("text") or ""):
                            current.interrupted = True
            elif isinstance(content, str) and "[Request interrupted" in content:
                current.interrupted = True

    return session


def iter_session_paths(projects_dir: Path = DEFAULT_PROJECTS_DIR) -> list[Path]:
    return sorted(projects_dir.glob("**/*.jsonl"))
