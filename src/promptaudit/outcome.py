"""결과물 품질 축.

프롬프트 문장이 아니라 그 프롬프트가 실제로 무엇을 만들어 냈는지를 본다.
네 개 층으로 나눠 재고, 합쳐서 0~100 결과 점수를 만든다.

  즉시 성공   도구 실행이 에러 없이 끝났는가, 사용자가 중간에 끊지 않았는가
  수렴 비용   목표에 닿기까지 턴과 토큰을 얼마나 썼는가, 같은 파일을 몇 번 고쳤는가
  지속성      그때 건드린 파일이 실제 커밋까지 갔는가
  사용자 수용 다음 프롬프트가 승인이었는가 정정이었는가
"""

from __future__ import annotations

import subprocess
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .loader import PromptUnit
from .metrics import PromptMetrics


@dataclass
class GitIndex:
    """레포의 파일별 커밋 시각 목록. 지속성 판정에 쓴다."""

    repo: Path
    file_commits: dict[str, list[datetime]]

    @classmethod
    def load(cls, repo: Path, since: str = "2026-01-01") -> "GitIndex":
        file_commits: dict[str, list[datetime]] = defaultdict(list)
        if not (repo / ".git").exists():
            return cls(repo=repo, file_commits={})
        try:
            raw = subprocess.run(
                ["git", "-C", str(repo), "log", f"--since={since}",
                 "--name-only", "--pretty=format:%x01%cI"],
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=120,
            ).stdout
        except (OSError, subprocess.SubprocessError):
            return cls(repo=repo, file_commits={})

        current: datetime | None = None
        for line in raw.splitlines():
            if line.startswith("\x01"):
                try:
                    current = datetime.fromisoformat(line[1:].strip())
                except ValueError:
                    current = None
            elif line.strip() and current is not None:
                file_commits[line.strip().replace("\\", "/").lower()].append(current)
        return cls(repo=repo, file_commits=dict(file_commits))

    def committed_after(self, abs_path: str, after: datetime | None) -> bool:
        """절대 경로 파일이 주어진 시각 이후 커밋에 등장했는지."""
        if not self.file_commits:
            return False
        norm = abs_path.replace("\\", "/").lower()
        try:
            repo_norm = str(self.repo).replace("\\", "/").lower().rstrip("/") + "/"
        except Exception:
            return False
        if not norm.startswith(repo_norm):
            return False
        rel = norm[len(repo_norm):]
        stamps = self.file_commits.get(rel)
        if not stamps:
            return False
        if after is None:
            return True
        if after.tzinfo is None:
            after = after.replace(tzinfo=timezone.utc)
        return any(s >= after for s in stamps)


@dataclass
class OutcomeScore:
    session_id: str
    index: int
    immediate: float
    convergence: float
    persistence: float
    acceptance: float
    total: float
    committed_files: int
    repeated_edit_max: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _immediate(prompt: PromptUnit, m: PromptMetrics) -> float:
    if m.tool_call_count == 0:
        # 도구를 안 쓴 질의응답. 중단만 아니면 성공으로 본다.
        return 40.0 if prompt.interrupted else 85.0
    error_rate = m.tool_error_count / m.tool_call_count
    score = 100.0 - error_rate * 120.0
    if prompt.interrupted:
        score -= 45.0
    return max(0.0, min(100.0, score))


def _convergence(m: PromptMetrics, repeated_edit_max: int) -> float:
    """턴과 재편집이 적을수록 높다. 도구를 안 쓴 프롬프트는 중립."""
    if m.tool_call_count == 0 and m.assistant_turns <= 1:
        return 70.0
    score = 100.0
    score -= max(0, m.assistant_turns - 2) * 6.0
    score -= max(0, m.tool_call_count - 4) * 2.0
    score -= max(0, repeated_edit_max - 1) * 9.0
    if m.output_tokens > 6000:
        score -= 8.0
    return max(0.0, min(100.0, score))


def _persistence(prompt: PromptUnit, git: GitIndex | None) -> tuple[float, int]:
    files = prompt.edited_files
    if not files:
        # 파일을 안 건드린 프롬프트는 지속성 개념이 없다. 중립값.
        return 60.0, 0
    if git is None:
        return 60.0, 0
    survived = sum(1 for f in set(files) if git.committed_after(f, prompt.timestamp))
    ratio = survived / len(set(files))
    return 25.0 + ratio * 75.0, survived


def _acceptance(m: PromptMetrics) -> float:
    if m.followed_by_approval:
        return 100.0
    if m.followed_by_correction:
        return 15.0
    return 60.0


WEIGHTS = {"immediate": 0.35, "convergence": 0.25, "persistence": 0.20, "acceptance": 0.20}


def score_prompt(
    prompt: PromptUnit, m: PromptMetrics, git: GitIndex | None
) -> OutcomeScore:
    counts = Counter(prompt.edited_files)
    repeated = max(counts.values()) if counts else 0

    immediate = _immediate(prompt, m)
    convergence = _convergence(m, repeated)
    persistence, committed = _persistence(prompt, git)
    acceptance = _acceptance(m)

    total = (
        immediate * WEIGHTS["immediate"]
        + convergence * WEIGHTS["convergence"]
        + persistence * WEIGHTS["persistence"]
        + acceptance * WEIGHTS["acceptance"]
    )
    return OutcomeScore(
        session_id=prompt.session_id,
        index=prompt.index,
        immediate=round(immediate, 1),
        convergence=round(convergence, 1),
        persistence=round(persistence, 1),
        acceptance=round(acceptance, 1),
        total=round(total, 1),
        committed_files=committed,
        repeated_edit_max=repeated,
    )
