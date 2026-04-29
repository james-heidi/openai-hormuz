from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from types import TracebackType
from typing import Protocol, Self


class RepositoryPreparationError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class PreparedRepository:
    source: str
    base_repo_path: Path
    worktrees: dict[str, Path]
    _cleanup: Callable[[], None] = field(repr=False, compare=False)

    def worktree_for(self, name: str) -> Path:
        try:
            return self.worktrees[name]
        except KeyError as exc:
            raise RepositoryPreparationError(
                "missing_worktree",
                f"No prepared worktree is available for scanner '{name}'.",
            ) from exc

    def cleanup(self) -> None:
        self._cleanup()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.cleanup()


class RepositoryPreparer(Protocol):
    def prepare(
        self,
        source: str,
        worktree_names: Sequence[str],
        *,
        branch: str | None = None,
    ) -> PreparedRepository:
        """Prepare isolated scan directories for scanners."""
