from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any, Protocol

from modules.scan.domain.entities import Finding

ScanEvent = dict[str, Any]
EventEmitter = Callable[[ScanEvent], Awaitable[None]]


class ScanAgent(Protocol):
    name: str
    category: str

    async def scan(self, repo_path: Path, emit: EventEmitter) -> list[Finding]:
        """Scan a repository path and emit progress events."""

