from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
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

