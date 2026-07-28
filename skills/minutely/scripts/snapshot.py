#!/usr/bin/env python3
"""Minutely 스냅샷 diff 코어.

C조_한컴 페이지를 정규화한 JSON을 직전 스냅샷과 비교해 added/modified/removed를 뽑는다.
Notion 접근은 스킬(Claude + MCP)이 담당하고, 이 스크립트는 순수 비교만 한다 — 표준 라이브러리만.

정규화 입력 형태 (current.json):
{
  "page_id": "...",
  "captured_at": "ISO8601",
  "items": {
    "<고유 id>": {"kind": "prose|row", "source": "page|<DB 이름>", "title": "...", "text": "..."}
  }
}
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DEFAULT_BASELINE = Path(".minutely") / "snapshot.json"


def _norm(text: str | None) -> str:
    """공백만 다른 변경은 무시하도록 텍스트를 정규화."""
    if not text:
        return ""
    return " ".join(str(text).split())


def load_items(path: Path) -> dict[str, dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data.get("items")
    if not isinstance(items, dict):
        raise SystemExit(f"{path}: 'items' 객체가 없습니다.")
    return items


def diff_items(previous: dict[str, dict], current: dict[str, dict]) -> dict:
    """previous 대비 current의 added/modified/removed를 반환."""
    prev_keys = set(previous)
    cur_keys = set(current)

    added = [_entry(k, current[k]) for k in sorted(cur_keys - prev_keys)]
    removed = [_entry(k, previous[k]) for k in sorted(prev_keys - cur_keys)]

    modified = []
    for k in sorted(cur_keys & prev_keys):
        before, after = previous[k], current[k]
        if _norm(before.get("text")) != _norm(after.get("text")) or \
           _norm(before.get("title")) != _norm(after.get("title")):
            modified.append({
                "id": k,
                "kind": after.get("kind", ""),
                "source": after.get("source", ""),
                "title": after.get("title", ""),
                "before": before.get("text", ""),
                "after": after.get("text", ""),
            })

    return {"added": added, "modified": modified, "removed": removed}


def _entry(key: str, item: dict) -> dict:
    return {
        "id": key,
        "kind": item.get("kind", ""),
        "source": item.get("source", ""),
        "title": item.get("title", ""),
        "text": item.get("text", ""),
    }


def cmd_diff(current_path: Path, baseline_path: Path) -> int:
    current = load_items(current_path)
    if not baseline_path.exists():
        # 최초 실행: 비교 대상이 없다. 기준선만 만들면 된다.
        print(json.dumps({
            "baseline": True,
            "added": [], "modified": [], "removed": [],
        }, ensure_ascii=False, indent=2))
        return 0

    previous = load_items(baseline_path)
    result = diff_items(previous, current)
    result["baseline"] = False
    result["changed"] = bool(result["added"] or result["modified"] or result["removed"])
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_promote(current_path: Path, baseline_path: Path) -> int:
    baseline_path.parent.mkdir(parents=True, exist_ok=True)
    baseline_path.write_text(current_path.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"promoted: {current_path} -> {baseline_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Minutely 스냅샷 diff 코어")
    sub = parser.add_subparsers(dest="command", required=True)

    for name in ("diff", "promote"):
        p = sub.add_parser(name)
        p.add_argument("--current", required=True, type=Path)
        p.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)

    args = parser.parse_args(argv)
    if args.command == "diff":
        return cmd_diff(args.current, args.baseline)
    if args.command == "promote":
        return cmd_promote(args.current, args.baseline)
    return 2


if __name__ == "__main__":
    sys.exit(main())
