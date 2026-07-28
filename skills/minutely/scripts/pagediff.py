#!/usr/bin/env python3
"""페이지 산문 dump 두 개(이전/현재)를 비교해 바뀐 구간을 뽑는다.

C조_한컴 페이지는 표·콜아웃이 많은 큰 문서라 소스 DB row 스냅샷만으로는 산문 변화를
못 잡는다. 이 스크립트는 이전 dump와 현재 dump를 difflib로 비교해 insert/replace/delete
구간을 사람이 읽을 만하게 출력한다. Claude가 그 결과를 요약한다. 표준 라이브러리만.
"""
from __future__ import annotations

import argparse
import difflib
import sys
from pathlib import Path

# 이보다 짧은 변경 조각은 표 태그 재정렬 같은 노이즈일 확률이 높아 건너뛴다.
MIN_CHUNK = 4


def _clean(s: str) -> str:
    return s.replace("\\n", " ").replace("\n", " ").strip()


def diff_text(old: str, new: str) -> list[dict]:
    sm = difflib.SequenceMatcher(a=old, b=new, autojunk=False)
    out: list[dict] = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        removed = _clean(old[i1:i2])
        added = _clean(new[j1:j2])
        if len(removed) < MIN_CHUNK and len(added) < MIN_CHUNK:
            continue
        out.append({"tag": tag, "removed": removed, "added": added})
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="페이지 dump 비교")
    parser.add_argument("--old", required=True, type=Path)
    parser.add_argument("--new", required=True, type=Path)
    args = parser.parse_args(argv)

    if not args.old.exists():
        print("BASELINE_MISSING", args.old)
        return 0

    old = args.old.read_text(encoding="utf-8")
    new = args.new.read_text(encoding="utf-8")
    changes = diff_text(old, new)
    if not changes:
        print("NO_PROSE_CHANGE")
        return 0

    for c in changes:
        if c["removed"]:
            print(f"[-] {c['removed'][:300]}")
        if c["added"]:
            print(f"[+] {c['added'][:300]}")
        print("---")
    return 0


if __name__ == "__main__":
    sys.exit(main())
