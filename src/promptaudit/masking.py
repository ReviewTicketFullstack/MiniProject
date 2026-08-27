"""리포트에 프롬프트 원문을 싣기 전에 비밀값을 가린다.

프롬프트에는 DB 접속 정보, JWT 시크릿, 내부 IP가 그대로 섞여 있을 수 있다.
리포트는 발표 자료로 공유되므로 인용 전에 반드시 이 단계를 거친다.
"""

from __future__ import annotations

import re

RULES: list[tuple[str, re.Pattern[str], str]] = [
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]+"), "[JWT-MASKED]"),
    ("db_url", re.compile(r"\b(?:jdbc:)?(?:mysql|postgresql|mongodb|redis)(?:\+srv)?://[^\s\"']+", re.I), "[DB-URL-MASKED]"),
    ("private_ip", re.compile(r"\b(?:10|172|192)\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"), "[IP-MASKED]"),
    ("public_ip", re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{2,5}\b"), "[HOST-MASKED]"),
    ("password_kv", re.compile(r"(?i)\b(password|passwd|pwd|secret|token|api[_-]?key)\s*[:=]\s*[\"']?[^\s\"',;]{4,}"), r"\1=[MASKED]"),
    ("bearer", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._-]{12,}"), "Bearer [MASKED]"),
    ("aws_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "[AWS-KEY-MASKED]"),
    ("github_pat", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{16,}\b"), "[GH-TOKEN-MASKED]"),
    ("email", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]{2,}\b"), "[EMAIL-MASKED]"),
]


def mask(text: str) -> tuple[str, list[str]]:
    """가린 텍스트와 어떤 규칙이 걸렸는지 목록을 함께 돌려준다."""
    hit: list[str] = []
    out = text
    for name, pattern, repl in RULES:
        out, n = pattern.subn(repl, out)
        if n:
            hit.append(name)
    return out, hit


def excerpt(text: str, limit: int = 320) -> str:
    """마스킹 + 길이 자르기. 리포트 인용용."""
    masked, _ = mask(text)
    masked = " ".join(masked.split())
    if len(masked) <= limit:
        return masked
    return masked[:limit] + " …"
