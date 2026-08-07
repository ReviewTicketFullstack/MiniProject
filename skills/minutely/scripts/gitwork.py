#!/usr/bin/env python3
"""git 작업 내역 수집 — GitHub 커밋·PR을 날짜(KST)별·팀원별로 묶어 JSON으로 출력.

Notion 쓰기는 스킬(Claude + MCP)이 담당하고, 이 스크립트는 수집·집계만 한다.
gh CLI만 사용하므로 로컬 클론 상태와 무관하다.

사용:
    python gitwork.py --since 2026-08-05 [--until 2026-08-07]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import GITHUB_TO_MEMBER, TARGET_BRANCH, TARGET_REPO  # noqa: E402

KST = timezone(timedelta(hours=9))

# 변경 파일 경로 → 데일리 스크럼 '분야' 옵션. 위에서부터 첫 일치를 쓴다.
AREA_BY_PREFIX = [
    ("frontend/", "프론트엔드"),
    ("backend/", "API·연동"),
    ("ai/", "AI 기능"),
    (".github/", "문서·발표"),
    ("README", "문서·발표"),
]


def gh(*args: str):
    """gh CLI 호출 후 JSON 파싱. 실패하면 stderr를 그대로 보여주고 중단."""
    proc = subprocess.run(["gh", *args], capture_output=True, text=True, encoding="utf-8")
    if proc.returncode != 0:
        raise SystemExit(f"gh 호출 실패: gh {' '.join(args)}\n{proc.stderr.strip()}")
    return json.loads(proc.stdout or "null")


def kst_day(iso_utc: str) -> str:
    """GitHub의 UTC ISO 시각 → KST 날짜 문자열."""
    dt = datetime.strptime(iso_utc, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return dt.astimezone(KST).date().isoformat()


def member_of(login: str | None) -> str:
    """GitHub login → 팀원 실명. 모르는 계정은 login 그대로 남긴다(조용히 버리지 않음)."""
    if not login:
        return "(작성자 불명)"
    return GITHUB_TO_MEMBER.get(login, login)


def areas_of(paths) -> list[str]:
    areas: list[str] = []
    for path in paths:
        for prefix, area in AREA_BY_PREFIX:
            if path.startswith(prefix):
                if area not in areas:
                    areas.append(area)
                break
    return areas


def bucket(days: dict, day: str, member: str) -> dict:
    return days.setdefault(day, {}).setdefault(
        member, {"commits": [], "prs": [], "areas": []}
    )


def collect_commits(days: dict, since_utc: str, until_utc: str) -> None:
    path = (
        f"repos/{TARGET_REPO}/commits"
        f"?sha={TARGET_BRANCH}&since={since_utc}&until={until_utc}&per_page=100"
    )
    for commit in gh("api", "--paginate", path):
        if len(commit.get("parents", [])) > 1:
            continue  # 머지 커밋은 PR 쪽에서 이미 잡힌다
        author = commit.get("author") or {}
        day = kst_day(commit["commit"]["author"]["date"])
        slot = bucket(days, day, member_of(author.get("login")))
        slot["commits"].append(
            {
                "sha": commit["sha"][:7],
                "message": commit["commit"]["message"].split("\n")[0],
                "url": commit["html_url"],
            }
        )
        detail = gh("api", f"repos/{TARGET_REPO}/commits/{commit['sha']}")
        for area in areas_of(f["filename"] for f in detail.get("files", [])):
            if area not in slot["areas"]:
                slot["areas"].append(area)


def collect_prs(days: dict, since: str, until: str) -> None:
    fields = "number,title,url,author,state,mergedAt,createdAt,files"
    for pr in gh("pr", "list", "--repo", TARGET_REPO, "--state", "all",
                 "--limit", "200", "--json", fields):
        stamp = pr["mergedAt"] or pr["createdAt"]
        day = kst_day(stamp)
        if not (since <= day <= until):
            continue
        slot = bucket(days, day, member_of((pr.get("author") or {}).get("login")))
        slot["prs"].append(
            {
                "number": pr["number"],
                "title": pr["title"],
                "state": pr["state"],
                "url": pr["url"],
            }
        )
        for area in areas_of(f["path"] for f in pr.get("files", [])):
            if area not in slot["areas"]:
                slot["areas"].append(area)


def main() -> None:
    parser = argparse.ArgumentParser(description="GitHub 커밋·PR을 날짜별·팀원별로 집계")
    parser.add_argument("--since", required=True, help="시작 날짜 (KST, YYYY-MM-DD)")
    parser.add_argument("--until", help="종료 날짜 (KST, YYYY-MM-DD). 기본값 오늘")
    args = parser.parse_args()

    until = args.until or datetime.now(KST).date().isoformat()
    if args.since > until:
        raise SystemExit(f"--since({args.since})가 --until({until})보다 늦습니다.")

    # KST 하루 경계를 UTC로 옮긴다 (KST = UTC+9)
    since_utc = (
        datetime.strptime(f"{args.since}T00:00:00Z", "%Y-%m-%dT%H:%M:%SZ")
        - timedelta(hours=9)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")
    until_utc = (
        datetime.strptime(f"{until}T23:59:59Z", "%Y-%m-%dT%H:%M:%SZ")
        - timedelta(hours=9)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")

    days: dict = {}
    collect_commits(days, since_utc, until_utc)
    collect_prs(days, args.since, until)

    # Windows 콘솔 기본 인코딩(cp949)에서 한글이 깨지므로 출력만 UTF-8로 고정한다.
    sys.stdout.reconfigure(encoding="utf-8")
    print(
        json.dumps(
            {
                "repo": TARGET_REPO,
                "branch": TARGET_BRANCH,
                "since": args.since,
                "until": until,
                "days": dict(sorted(days.items())),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
