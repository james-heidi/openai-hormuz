from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable, Mapping
from pathlib import Path
from typing import Any

from modules.scan.domain.entities import Finding

ScanEvent = dict[str, Any]
EventEmitter = Callable[[ScanEvent], Awaitable[None]]


class ScanAgent(ABC):
    name: str
    category: str

    @abstractmethod
    async def scan(self, repo_path: Path, emit: EventEmitter) -> list[Finding]:
        """Scan a repository path and emit progress events."""


class FixAgent(ABC):
    name: str

    @abstractmethod
    async def fix(self, finding: Finding, source: str) -> str | None:
        """Return updated source for one finding, or None when unsupported."""


class PullRequestPublisher(ABC):
    @abstractmethod
    def is_configured(self, repo_path: Path) -> bool:
        """Return whether PR creation has enough configuration to run."""

    @abstractmethod
    async def create_pull_request(
        self,
        repo_path: Path,
        title: str,
        body: str,
        changed_files: Mapping[str, str],
    ) -> str:
        """Create a pull request with changed file contents and return its URL."""
