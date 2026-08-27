"""핵심 판정 로직 검증.

실행: PYTHONPATH=src python -m pytest tests -q
pytest가 없으면 python tests/test_core.py 로도 돌아간다.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from promptaudit import masking, metrics  # noqa: E402
from promptaudit.loader import PromptUnit, ToolCall  # noqa: E402
from promptaudit.outcome import GitIndex, score_prompt  # noqa: E402
from promptaudit.selector import strip_system_text  # noqa: E402

BASE = datetime(2026, 8, 1, tzinfo=timezone.utc)


def make_prompt(text: str, **kwargs) -> PromptUnit:
    unit = PromptUnit(
        session_id="testsess",
        index=kwargs.pop("index", 0),
        text=text,
        timestamp=kwargs.pop("timestamp", BASE),
        cwd=r"C:\dev\ReviewTicketFullstack",
        git_branch="main",
    )
    for key, value in kwargs.items():
        setattr(unit, key, value)
    return unit


def test_masking_catches_secrets():
    text = (
        "DB는 mysql://root:hunter2@10.0.3.14:3306/reviewticket 이고 "
        "토큰은 eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.abcdefghij 이다. "
        "password=supersecret 로 접속한다."
    )
    masked, hits = masking.mask(text)
    assert "hunter2" not in masked
    assert "eyJhbGciOiJIUzI1NiJ9" not in masked
    assert "supersecret" not in masked
    assert "db_url" in hits and "jwt" in hits
    print("test_masking_catches_secrets ok ->", hits)


def test_masking_leaves_plain_text():
    masked, hits = masking.mask("리뷰 목록 API를 고쳐 줘")
    assert masked == "리뷰 목록 API를 고쳐 줘"
    assert hits == []
    print("test_masking_leaves_plain_text ok")


def test_file_path_detection():
    m = metrics.compute(make_prompt(r"C:\dev\ReviewTicketFullstack\backend\Server\src\Main.java 를 고쳐 줘"), None)
    assert m.has_file_path, "윈도우 절대 경로를 잡아야 한다"

    m2 = metrics.compute(make_prompt("src/pages/Login.tsx 에서 에러 문구를 바꿔 줘"), None)
    assert m2.has_file_path, "유닉스 스타일 경로도 잡아야 한다"

    m3 = metrics.compute(make_prompt("그거 고쳐 줘"), None)
    assert not m3.has_file_path
    print("test_file_path_detection ok")


def test_correction_marker_detects_rework():
    first = make_prompt("리뷰 목록 API 만들어 줘", index=0)
    second = make_prompt("아니 그게 아니라 페이징을 붙이라고", index=1)
    m = metrics.compute(first, second)
    assert m.followed_by_correction
    assert not m.followed_by_approval

    third = make_prompt("좋아 그대로 가자", index=1)
    m2 = metrics.compute(first, third)
    assert m2.followed_by_approval
    print("test_correction_marker_detects_rework ok")


def test_antipatterns():
    terse = metrics.compute(make_prompt("해줘"), None)
    assert terse.ap_too_terse

    multi = metrics.compute(
        make_prompt("API 구현해줘 그리고 테스트 작성해줘 그리고 문서도 정리해줘"), None
    )
    assert multi.ap_multi_demand

    long_one = metrics.compute(make_prompt("가" * 1600), None)
    assert long_one.ap_wall_of_text
    print("test_antipatterns ok")


def test_strip_system_reminder():
    text = "리뷰 API 고쳐 줘 <system-reminder>ReviewTicket 메모리 주입</system-reminder>"
    assert "메모리 주입" not in strip_system_text(text)
    print("test_strip_system_reminder ok")


def test_outcome_penalises_interrupt_and_errors():
    clean = make_prompt(
        "src/api/review.ts 의 목록 응답에 페이징을 붙여 줘",
        assistant_turns=2,
        end_timestamp=BASE + timedelta(seconds=40),
        tool_calls=[
            ToolCall(name="Read", input={}, tool_use_id="a", is_error=False),
            ToolCall(name="Edit", input={"file_path": r"C:\dev\x\a.ts"}, tool_use_id="b", is_error=False),
        ],
    )
    good = score_prompt(clean, metrics.compute(clean, make_prompt("좋아")), None)

    messy = make_prompt(
        "그거 좀 고쳐 줘",
        assistant_turns=9,
        interrupted=True,
        tool_calls=[
            ToolCall(name="Bash", input={}, tool_use_id="c", is_error=True),
            ToolCall(name="Bash", input={}, tool_use_id="d", is_error=True),
            ToolCall(name="Edit", input={"file_path": r"C:\dev\x\a.ts"}, tool_use_id="e", is_error=False),
            ToolCall(name="Edit", input={"file_path": r"C:\dev\x\a.ts"}, tool_use_id="f", is_error=False),
        ],
    )
    bad = score_prompt(messy, metrics.compute(messy, make_prompt("아니 그거 말고")), None)

    assert good.total > bad.total + 20, (good.total, bad.total)
    assert bad.immediate < 40
    print("test_outcome_penalises_interrupt_and_errors ok ->", good.total, bad.total)


def test_git_index_persistence():
    """세션 시각 이후 커밋에 등장한 파일만 살아남은 것으로 본다."""
    index = GitIndex(
        repo=Path(r"C:\dev\ReviewTicketFullstack"),
        file_commits={"backend/server/src/main.java": [BASE + timedelta(days=1)]},
    )
    assert index.committed_after(r"C:\dev\ReviewTicketFullstack\backend\Server\src\Main.java", BASE)
    assert not index.committed_after(
        r"C:\dev\ReviewTicketFullstack\backend\Server\src\Main.java", BASE + timedelta(days=5)
    )
    assert not index.committed_after(r"C:\dev\other\thing.py", BASE)
    print("test_git_index_persistence ok")


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
            except AssertionError as exc:
                failures += 1
                print("FAIL", name, exc)
    print("실패", failures, "건")
    raise SystemExit(1 if failures else 0)
