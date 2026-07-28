#!/usr/bin/env python3
"""Minutely 공용 설정 — Notion 대상 id 상수 + OPENAI_API_KEY 로드."""
from __future__ import annotations

import os
from pathlib import Path

# --- Notion 대상 (SKILL.md와 동일하게 유지) ---
WATCH_PAGE_ID = "3aabdeac-d0b4-804d-a1c2-dfc339401282"  # C조_한컴

# 경로 A: 노션 변화 정리 로그를 쌓는 페이지 (회의록 아님)
CHANGE_LOG_PAGE_ID = "3abbdeac-d0b4-802e-be23-f0a4c4f131e0"  # 노션 변경 내용 정리 (Claude 전용)

# 경로 B: 회의 녹음/텍스트를 정리해 새 행을 만드는 회의록 DB
MEETING_MINUTES_COLLECTION = "c5bbdeac-d0b4-8333-bba6-07d1ccebfcfb"  # 회의록 (1)

# diff에서 제외할 출력/자동생성 DB (피드백 루프 방지) — collection id
EXCLUDED_COLLECTIONS = {
    "회의록": "c5bbdeac-d0b4-8333-bba6-07d1ccebfcfb",
    "데일리 스크럼": "a79bdeac-d0b4-83b2-8ace-077993a8dd69",
}

# 소스 DB (변화 감시 대상) — 출력 DB는 피드백 루프 방지 위해 제외
SOURCE_COLLECTIONS = [
    "ee9bdeac-d0b4-83f2-a974-079e24493877",
    "949bdeac-d0b4-8273-a20e-07bd8585adad",
    "533bdeac-d0b4-825b-b53a-87ceec15f904",
    "2e1bdeac-d0b4-82a1-bdd8-87f9ca7d2a93",
    "6f6bdeac-d0b4-82b8-97f9-87eb00fdd2c4",
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
