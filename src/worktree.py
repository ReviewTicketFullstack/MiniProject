"""Git worktree management for isolated experiments."""

import subprocess
import os
import tempfile
import shutil
from pathlib import Path
from typing import Optional, Tuple


class WorktreeError(Exception):
    """Worktree operation failed."""
    pass


class Worktree:
    """Manages an isolated Git worktree for a change drill."""

    def __init__(self, repo_path: str, scenario_id: str, base_commit: Optional[str] = None):
        """
        Initialize worktree manager.

        Args:
            repo_path: Path to the target Git repository
            scenario_id: Identifier for the change scenario
            base_commit: Specific commit to base worktree on (defaults to HEAD)
        """
        self.repo_path = Path(repo_path).resolve()
        self.scenario_id = scenario_id
        self.base_commit = base_commit
        self.worktree_path: Optional[Path] = None
        self.created = False

    def validate_repo(self) -> bool:
        """Check if repo_path is a valid Git repository."""
        if not self.repo_path.is_dir():
            raise WorktreeError(f"Repository path does not exist: {self.repo_path}")

        git_dir = self.repo_path / ".git"
        if not git_dir.exists():
            raise WorktreeError(f"Not a Git repository: {self.repo_path}")

        return True

    def get_base_commit(self) -> str:
        """Get the base commit, defaulting to HEAD if not specified."""
        if self.base_commit:
            return self.base_commit

        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            raise WorktreeError(f"Failed to get HEAD commit: {result.stderr}")

        return result.stdout.strip()

    def create(self) -> Path:
        """
        Create an isolated worktree.

        Returns:
            Path to the created worktree

        Raises:
            WorktreeError: If worktree creation fails
        """
        self.validate_repo()
        base_commit = self.get_base_commit()

        worktree_name = f"drill-{self.scenario_id}-{os.getpid()}"
        worktree_path = self.repo_path / ".git" / "worktrees" / worktree_name

        try:
            result = subprocess.run(
                ["git", "worktree", "add", "--detach", str(worktree_path), base_commit],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                raise WorktreeError(
                    f"git worktree add failed:\n{result.stderr}"
                )

            if not worktree_path.exists():
                raise WorktreeError(f"Worktree path does not exist after creation: {worktree_path}")

            self.worktree_path = worktree_path
            self.created = True
            return worktree_path

        except Exception as e:
            raise WorktreeError(f"Worktree creation failed: {e}")

    def cleanup(self) -> bool:
        """
        Remove the worktree safely.

        Returns:
            True if cleanup succeeded, False otherwise
        """
        if not self.worktree_path:
            return True

        try:
            result = subprocess.run(
                ["git", "worktree", "remove", "--force", str(self.worktree_path)],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                print(f"Warning: git worktree remove failed: {result.stderr}")
                return False

            return True

        except Exception as e:
            print(f"Warning: Worktree cleanup raised exception: {e}")
            return False

    def get_diff(self, base_commit: Optional[str] = None) -> str:
        """
        Get unified diff from base commit to current state.

        Args:
            base_commit: Commit to diff against (defaults to worktree base)

        Returns:
            Unified diff text
        """
        if not self.worktree_path:
            raise WorktreeError("Worktree not created yet")

        target_commit = base_commit or self.get_base_commit()

        result = subprocess.run(
            ["git", "diff", target_commit],
            cwd=self.worktree_path,
            capture_output=True,
            text=True,
            check=False,
        )

        return result.stdout

    def get_status(self) -> str:
        """Get git status output."""
        if not self.worktree_path:
            raise WorktreeError("Worktree not created yet")

        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=self.worktree_path,
            capture_output=True,
            text=True,
            check=False,
        )

        return result.stdout

    def __enter__(self):
        """Context manager entry."""
        self.create()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit. Always attempt cleanup."""
        self.cleanup()
        return False
