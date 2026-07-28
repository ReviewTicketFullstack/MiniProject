#!/usr/bin/env python3
"""snapshot.py diff 코어 유닛테스트. pytest 없이 `python test_snapshot.py`로 실행 가능."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import snapshot  # noqa: E402


def items(**kw):
    return kw


class DiffItemsTest(unittest.TestCase):
    def test_added(self):
        prev = {}
        cur = {"a": {"kind": "row", "source": "일정", "title": "T", "text": "hello"}}
        r = snapshot.diff_items(prev, cur)
        self.assertEqual([e["id"] for e in r["added"]], ["a"])
        self.assertEqual(r["modified"], [])
        self.assertEqual(r["removed"], [])

    def test_removed(self):
        prev = {"a": {"title": "T", "text": "hello"}}
        cur = {}
        r = snapshot.diff_items(prev, cur)
        self.assertEqual([e["id"] for e in r["removed"]], ["a"])
        self.assertEqual(r["added"], [])

    def test_modified_text(self):
        prev = {"a": {"title": "T", "text": "old value"}}
        cur = {"a": {"title": "T", "text": "new value"}}
        r = snapshot.diff_items(prev, cur)
        self.assertEqual(len(r["modified"]), 1)
        self.assertEqual(r["modified"][0]["before"], "old value")
        self.assertEqual(r["modified"][0]["after"], "new value")

    def test_whitespace_only_not_modified(self):
        prev = {"a": {"title": "T", "text": "same  value"}}
        cur = {"a": {"title": "T", "text": "same value\n"}}
        r = snapshot.diff_items(prev, cur)
        self.assertEqual(r["modified"], [])

    def test_title_change_is_modified(self):
        prev = {"a": {"title": "old title", "text": "body"}}
        cur = {"a": {"title": "new title", "text": "body"}}
        r = snapshot.diff_items(prev, cur)
        self.assertEqual(len(r["modified"]), 1)

    def test_unchanged(self):
        prev = {"a": {"title": "T", "text": "body"}}
        cur = {"a": {"title": "T", "text": "body"}}
        r = snapshot.diff_items(prev, cur)
        self.assertEqual((r["added"], r["modified"], r["removed"]), ([], [], []))


class CliTest(unittest.TestCase):
    def _write(self, path: Path, item_map: dict):
        path.write_text(json.dumps({"page_id": "p", "items": item_map}), encoding="utf-8")

    def test_diff_baseline_when_no_snapshot(self):
        with tempfile.TemporaryDirectory() as d:
            cur = Path(d) / "current.json"
            base = Path(d) / "snapshot.json"  # 존재하지 않음
            self._write(cur, {"a": {"text": "x"}})
            rc = snapshot.main(["diff", "--current", str(cur), "--baseline", str(base)])
            self.assertEqual(rc, 0)

    def test_promote_creates_baseline(self):
        with tempfile.TemporaryDirectory() as d:
            cur = Path(d) / "current.json"
            base = Path(d) / "state" / "snapshot.json"  # 하위 폴더 자동 생성 확인
            self._write(cur, {"a": {"text": "x"}})
            rc = snapshot.main(["promote", "--current", str(cur), "--baseline", str(base)])
            self.assertEqual(rc, 0)
            self.assertTrue(base.exists())
            self.assertEqual(
                json.loads(base.read_text(encoding="utf-8"))["items"]["a"]["text"], "x"
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
