"""Measurement and evidence collection from change drills.

변경 비용 측정: git diff를 파싱해 파일 수, 라인 변경량, 테스트 파일 영향도 추출.
빌드/검증 실행: 저장소 타입에 맞는 단일 명령 탐지 및 실행 (결과 저장).
증거 수집: 측정값과 검증 결과를 ExperimentEvidence 객체로 구조화.
"""

import json
import subprocess
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict
from datetime import datetime


@dataclass
class FileDiff:
    """변경된 파일 하나의 정보"""
    path: str
    status: str  # A=added, M=modified, D=deleted, R=renamed
    lines_added: int = 0
    lines_deleted: int = 0
    is_test_file: bool = False


@dataclass
class VerificationResult:
    """빌드와 테스트 검증 결과"""
    build_success: bool
    test_success: bool
    build_output: str = ""
    test_output: str = ""
    build_command: str = ""
    test_command: str = ""


@dataclass
class ChangeCost:
    """전체 코드 변경량"""
    total_files_changed: int
    total_lines_added: int
    total_lines_deleted: int
    files_changed_list: List[FileDiff]
    test_files_changed: int
    unrelated_files_modified: int


def parse_diff(diff_text: str) -> ChangeCost:
    """
    git diff 결과를 분석하여 변경 파일 수와 코드 변경량 계산

    Args:
        diff_text: Output from `git diff`

    Returns:
        ChangeCost object with statistics
    """
    files_changed = {}
    lines_added = 0
    lines_deleted = 0

    for line in diff_text.split("\n"):
        if line.startswith("diff --git"):
            parts = line.split()
            a_path = parts[2]
            b_path = parts[3]
            file_path = b_path[2:] if b_path.startswith("b/") else a_path[2:]
            files_changed[file_path] = FileDiff(path=file_path, status="M")

        elif line.startswith("+++"):
            continue
        elif line.startswith("---"):
            continue
        elif line.startswith("+") and not line.startswith("+++"):
            lines_added += 1
        elif line.startswith("-") and not line.startswith("---"):
            lines_deleted += 1

    file_diffs = list(files_changed.values())
    test_files = sum(1 for f in file_diffs if _is_test_file(f.path))

    return ChangeCost(
        total_files_changed=len(file_diffs),
        total_lines_added=lines_added,
        total_lines_deleted=lines_deleted,
        files_changed_list=file_diffs,
        test_files_changed=test_files,
        unrelated_files_modified=0,
    )


def _is_test_file(path: str) -> bool:
    """파일 경로를 보고 테스트 파일인지 추정"""
    return (
        "test" in path.lower()
        or "spec" in path.lower()
        or path.endswith(".test.js")
        or path.endswith(".spec.js")
        or path.endswith("_test.py")
    )


def detect_build_command(repo_path: Path) -> str:
    """
    저장소 파일 구조 보고 실행할 빌드/검증 명령어 추정

    Returns:
        Build command string (e.g., "make", "npm run build", "python -m pytest")
    """
    if (repo_path / "Makefile").exists():
        return "make"

    if (repo_path / "package.json").exists():
        return "npm test"

    if (repo_path / "pytest.ini").exists() or (repo_path / "setup.py").exists():
        return "python -m pytest"

    if (repo_path / "requirements.txt").exists():
        return "python -m pytest"

    return "make"  # Default fallback


def run_verification(worktree_path: Path, repo_path: Path) -> VerificationResult:
    """
    worktree 에서 빌드 명령 실행하고 성공/실패 및 출력결과를 verificationResult 로 반환

    Args:
        worktree_path: Path to the isolated worktree
        repo_path: Original repository path (for build detection)

    Returns:
        VerificationResult with success status and output
    """
    build_cmd = detect_build_command(repo_path)

    build_success = True
    build_output = ""
    test_success = True
    test_output = ""

    result = subprocess.run(
        build_cmd.split(),
        cwd=worktree_path,
        capture_output=True,
        text=True,
        timeout=300,
    )

    build_success = result.returncode == 0
    build_output = result.stdout + result.stderr if result.returncode != 0 else ""

    if build_success:
        test_success = True
        test_output = result.stdout

    return VerificationResult(
        build_success=build_success,
        test_success=test_success,
        build_output=build_output,
        test_output=test_output,
        build_command=build_cmd,
        test_command="",
    )


@dataclass
class ExperimentEvidence:
    """하나의 agent 실험에서 발생한 모든 측정 근거"""
    scenario_id: str
    scenario_name: str
    timestamp: str
    base_commit: str
    completed: bool
    change_cost: ChangeCost
    verification: VerificationResult
    diff: str
    git_status: str
    notes: str = ""

    def to_dict(self) -> Dict:
        """ExperimentEvidence 객체를 JSON 저장이 가능한 dictionary 형태로 변환"""
        return {
            "scenario_id": self.scenario_id,
            "scenario_name": self.scenario_name,
            "timestamp": self.timestamp,
            "base_commit": self.base_commit,
            "completed": self.completed,
            "change_cost": asdict(self.change_cost),
            "verification": asdict(self.verification),
            "notes": self.notes,
        }

    def to_json(self) -> str:
        """ExperimentEvidence 를 JSON 문자열로 직렬화"""
        return json.dumps(self.to_dict(), indent=2)
