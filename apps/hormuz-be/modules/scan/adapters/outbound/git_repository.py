import re
import shutil
import subprocess
import tempfile
from collections.abc import Sequence
from pathlib import Path
from urllib.parse import urlparse

from modules.scan.application.repositories import PreparedRepository, RepositoryPreparationError


class GitRepositoryPreparer:
    def __init__(self, storage_root: Path | None = None) -> None:
        self._storage_root = storage_root

    def prepare(
        self,
        source: str,
        worktree_names: Sequence[str],
        *,
        branch: str | None = None,
    ) -> PreparedRepository:
        names = _validate_worktree_names(worktree_names)
        workspace_root = self._create_workspace_root()
        added_worktrees: dict[str, Path] = {}

        try:
            base_repo_path = self._prepare_base_repository(source, workspace_root)
            _run_git(
                ["worktree", "prune"],
                cwd=base_repo_path,
                error_code="worktree_prune_failed",
                error_message="Could not prune stale git worktree metadata.",
            )
            commit = _resolve_commit(base_repo_path, branch or "HEAD")
            worktree_root = workspace_root / "worktrees"
            worktree_root.mkdir(parents=True, exist_ok=True)

            for index, name in enumerate(names, start=1):
                worktree_path = worktree_root / f"{index:02d}-{_slug(name)}"
                if worktree_path.exists():
                    raise RepositoryPreparationError(
                        "worktree_already_exists",
                        f"Worktree path already exists: {worktree_path}",
                    )
                _run_git(
                    ["worktree", "add", "--detach", str(worktree_path), commit],
                    cwd=base_repo_path,
                    error_code="worktree_setup_failed",
                    error_message=f"Could not create worktree for scanner '{name}'.",
                )
                added_worktrees[name] = worktree_path
        except Exception:
            _cleanup_workspace(base_repo_path if "base_repo_path" in locals() else None, added_worktrees)
            shutil.rmtree(workspace_root, ignore_errors=True)
            raise

        def cleanup() -> None:
            _cleanup_workspace(base_repo_path, added_worktrees)
            shutil.rmtree(workspace_root, ignore_errors=True)

        return PreparedRepository(
            source=source,
            base_repo_path=base_repo_path,
            worktrees=added_worktrees,
            _cleanup=cleanup,
        )

    def _create_workspace_root(self) -> Path:
        if self._storage_root is not None:
            self._storage_root.mkdir(parents=True, exist_ok=True)
        return Path(tempfile.mkdtemp(prefix="hormuz-scan-", dir=self._storage_root))

    def _prepare_base_repository(self, source: str, workspace_root: Path) -> Path:
        source = source.strip()
        if not source:
            raise RepositoryPreparationError(
                "invalid_repo_source",
                "The repository source is empty.",
            )

        local_path = Path(source).expanduser()
        if local_path.exists():
            return _git_working_tree_root(local_path)

        if _looks_like_repo_link(source):
            clone_path = workspace_root / "source"
            _run_git(
                ["clone", source, str(clone_path)],
                cwd=None,
                error_code="repo_checkout_failed",
                error_message="Could not clone the repository link.",
            )
            return _git_working_tree_root(clone_path)

        raise RepositoryPreparationError(
            "invalid_repo_path",
            "The repository path does not exist or is not a repository link.",
        )


def _validate_worktree_names(worktree_names: Sequence[str]) -> list[str]:
    names = [name.strip() for name in worktree_names if name.strip()]
    if not names:
        raise RepositoryPreparationError(
            "missing_worktree_specs",
            "At least one scanner worktree must be requested.",
        )
    if len(set(names)) != len(names):
        raise RepositoryPreparationError(
            "duplicate_worktree_specs",
            "Scanner worktree names must be unique.",
        )
    return names


def _git_working_tree_root(path: Path) -> Path:
    if not path.is_dir():
        raise RepositoryPreparationError(
            "invalid_repo_path",
            "The repository path does not exist or is not a directory.",
        )

    result = _run_git(
        ["rev-parse", "--show-toplevel"],
        cwd=path,
        error_code="invalid_repository",
        error_message="The repository source is not a valid git working tree.",
    )
    return Path(result.stdout.strip()).resolve()


def _resolve_commit(repo_path: Path, ref: str) -> str:
    result = _run_git(
        ["rev-parse", "--verify", f"{ref}^{{commit}}"],
        cwd=repo_path,
        error_code="missing_branch",
        error_message=f"Could not resolve git branch or ref '{ref}'.",
    )
    return result.stdout.strip()


def _run_git(
    args: list[str],
    *,
    cwd: Path | None,
    error_code: str,
    error_message: str,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["git", *args],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise RepositoryPreparationError(
            "git_unavailable",
            "Git is not installed or is not available on PATH.",
        ) from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout).strip()
        message = f"{error_message} {detail}" if detail else error_message
        raise RepositoryPreparationError(error_code, message) from exc


def _cleanup_workspace(repo_path: Path | None, worktrees: dict[str, Path]) -> None:
    if repo_path is not None:
        for worktree_path in worktrees.values():
            if worktree_path.exists():
                subprocess.run(
                    ["git", "worktree", "remove", "--force", str(worktree_path)],
                    cwd=repo_path,
                    check=False,
                    capture_output=True,
                    text=True,
                )
        subprocess.run(
            ["git", "worktree", "prune"],
            cwd=repo_path,
            check=False,
            capture_output=True,
            text=True,
        )

    for worktree_path in worktrees.values():
        shutil.rmtree(worktree_path, ignore_errors=True)


def _looks_like_repo_link(source: str) -> bool:
    parsed = urlparse(source)
    if parsed.scheme in {"file", "git", "http", "https", "ssh"}:
        return True
    return bool(re.match(r"^[^@\s]+@[^:\s]+:.+\.git$", source))


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "scanner"
