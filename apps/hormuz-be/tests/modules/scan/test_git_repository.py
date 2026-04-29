import subprocess
from pathlib import Path

import pytest

from modules.scan.adapters.outbound.git_repository import GitRepositoryPreparer
from modules.scan.application.repositories import RepositoryPreparationError


def test_preparer_creates_isolated_worktrees_for_scanners(tmp_path: Path) -> None:
    source_repo = tmp_path / "source"
    _write_repo(source_repo)
    preparer = GitRepositoryPreparer(tmp_path / "scan-storage")

    prepared = preparer.prepare(
        str(source_repo),
        ["PII Scanner", "API Auditor", "Auth Checker"],
    )

    try:
        assert set(prepared.worktrees) == {"PII Scanner", "API Auditor", "Auth Checker"}
        assert len(set(prepared.worktrees.values())) == 3
        for worktree_path in prepared.worktrees.values():
            assert (worktree_path / "app.py").read_text() == "print('hello')\n"
            assert _git_output(worktree_path, "rev-parse", "--is-inside-work-tree") == "true"
    finally:
        worktree_paths = list(prepared.worktrees.values())
        prepared.cleanup()

    assert all(not worktree_path.exists() for worktree_path in worktree_paths)


def test_preparer_clones_repository_links(tmp_path: Path) -> None:
    source_repo = tmp_path / "source"
    _write_repo(source_repo)
    preparer = GitRepositoryPreparer(tmp_path / "scan-storage")

    prepared = preparer.prepare(source_repo.as_uri(), ["PII Scanner"])

    try:
        worktree_path = prepared.worktree_for("PII Scanner")
        assert (worktree_path / "app.py").read_text() == "print('hello')\n"
    finally:
        prepared.cleanup()


def test_preparer_rejects_invalid_repositories(tmp_path: Path) -> None:
    not_repo = tmp_path / "not-repo"
    not_repo.mkdir()

    with pytest.raises(RepositoryPreparationError) as exc_info:
        GitRepositoryPreparer(tmp_path / "scan-storage").prepare(str(not_repo), ["PII Scanner"])

    assert exc_info.value.code == "invalid_repository"


def test_preparer_reports_missing_branch(tmp_path: Path) -> None:
    source_repo = tmp_path / "source"
    _write_repo(source_repo)

    with pytest.raises(RepositoryPreparationError) as exc_info:
        GitRepositoryPreparer(tmp_path / "scan-storage").prepare(
            str(source_repo),
            ["PII Scanner"],
            branch="missing-branch",
        )

    assert exc_info.value.code == "missing_branch"


def test_preparer_cleans_up_after_failed_worktree_setup(tmp_path: Path) -> None:
    source_repo = tmp_path / "source"
    _write_repo(source_repo)
    workspace_root = tmp_path / "fixed-workspace"
    blocked_path = workspace_root / "worktrees" / "02-api-auditor"
    blocked_path.mkdir(parents=True)

    class FixedWorkspacePreparer(GitRepositoryPreparer):
        def _create_workspace_root(self) -> Path:
            return workspace_root

    with pytest.raises(RepositoryPreparationError) as exc_info:
        FixedWorkspacePreparer().prepare(str(source_repo), ["PII Scanner", "API Auditor"])

    assert exc_info.value.code == "worktree_already_exists"
    assert not workspace_root.exists()


def _write_repo(repo_path: Path) -> None:
    repo_path.mkdir()
    (repo_path / "app.py").write_text("print('hello')\n")
    _git(repo_path, "init")
    _git(repo_path, "checkout", "-b", "main")
    _git(repo_path, "config", "user.name", "Hormuz Test")
    _git(repo_path, "config", "user.email", "hormuz@example.com")
    _git(repo_path, "add", ".")
    _git(repo_path, "commit", "-m", "initial")


def _git(repo_path: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=repo_path,
        check=True,
        capture_output=True,
        text=True,
    )


def _git_output(repo_path: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=repo_path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
