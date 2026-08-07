#!/usr/bin/env python3
"""Minutely 공용 설정 — Notion 대상 id 상수 + OPENAI_API_KEY/GEMINI_API_KEY 로드."""
from __future__ import annotations

import os
from pathlib import Path

# --- Notion 대상 (SKILL.md와 동일하게 유지) ---
# 워크스페이스: ReviewTicketSpace (cc10a7ce-f23f-81b0-a4ac-000317aa2a01)
WATCH_PAGE_ID = "3b20a7ce-f23f-804e-bf2f-e4d21bc2e17e"  # ReviewTicket_26_0804

# 경로 A: 노션 변화 정리 로그를 쌓는 페이지 (회의록 아님)
CHANGE_LOG_PAGE_ID = "3b20a7ce-f23f-803d-9821-e87fed8a5d8b"  # 노션 변경 내용 정리 (Claude 전용) (1)

# 경로 B: 회의 녹음/텍스트를 정리해 새 행을 만드는 회의록 DB
MEETING_MINUTES_COLLECTION = "1220a7ce-f23f-83e9-9723-879f446d12ec"  # 회의록 (1)

# 경로 C: git 작업 내역을 날짜별 1행으로 쌓는 DB
DAILY_SCRUM_COLLECTION = "6e90a7ce-f23f-8294-b05f-07bc31f3d157"  # 데일리 스크럼 (1)

# 경로 C: 수집 대상 GitHub 저장소
TARGET_REPO = "ReviewTicket/ReviewTicketFullstack"

# 경로 C: 실제 작업이 쌓이는 브랜치 (main은 비어 있음)
TARGET_BRANCH = "dev"

# 경로 C: GitHub 계정 → 팀원 실명. 한 사람이 여러 author 이름을 쓰므로 login 기준으로 묶는다.
# (이메일 기준 금지 — 강성원의 git 이메일은 노션 등록 이메일과 다름)
GITHUB_TO_MEMBER = {
    "jkjun1234": "정기준",
    "jkjun": "정기준",
    "JunCo": "정기준",
    "mikeolw": "강성원",
    "byu-rin": "이도연",
    "simon3397": "이도연",
    "Lee do yeon": "이도연",
    "sealworldking": "한유진",
    "Han Yujin": "한유진",
}

# diff에서 제외할 출력/자동생성 DB (피드백 루프 방지) — collection id
EXCLUDED_COLLECTIONS = {
    "회의록": MEETING_MINUTES_COLLECTION,
    "데일리 스크럼": DAILY_SCRUM_COLLECTION,
}

# 소스 DB (변화 감시 대상) — 출력 DB는 피드백 루프 방지 위해 제외
SOURCE_COLLECTIONS = [
    "d630a7ce-f23f-8263-826b-07f17023a8b8",  # 프로젝트 안내 (1)
    "b7a0a7ce-f23f-8244-9d5f-07c9021d748a",  # 일정 (1)
    "b3b0a7ce-f23f-82ec-a906-07e67e332344",  # 기능명세서 (분야별) (1)
    "f850a7ce-f23f-83a2-9852-07fc63da9277",  # 기술 스택 (1)
]

# --- 시크릿 로드 ---
DOTENV_PATHS = [
    Path.cwd() / ".env",
    Path.home() / ".config" / "minutely" / ".env",
]


def _from_dotenv(path: Path, name: str) -> str | None:
    if not path.exists():
        return None
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            if key.strip() != name:
                continue
            value = value.strip()
            if len(value) >= 2 and value[0] in ('"', "'") and value[-1] == value[0]:
                value = value[1:-1]
            return value or None
    except OSError:
        return None
    return None


def load_openai_key() -> str | None:
    """환경변수 → cwd/.env → ~/.config/minutely/.env 순으로 OPENAI_API_KEY 탐색."""
    env = os.environ.get("OPENAI_API_KEY")
    if env and env.strip():
        return env.strip()
    for path in DOTENV_PATHS:
        value = _from_dotenv(path, "OPENAI_API_KEY")
        if value:
            return value
    return None


def load_gemini_key() -> str | None:
    """환경변수 → cwd/.env → ~/.config/minutely/.env 순으로 GEMINI_API_KEY 탐색."""
    env = os.environ.get("GEMINI_API_KEY")
    if env and env.strip():
        return env.strip()
    for path in DOTENV_PATHS:
        value = _from_dotenv(path, "GEMINI_API_KEY")
        if value:
            return value
    return None
