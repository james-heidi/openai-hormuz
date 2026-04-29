from pathlib import Path

import pytest

from modules.scan.application.orchestrator import ScanOrchestrator
from modules.scan.application.rule_catalog import default_agents
from modules.scan.domain.entities import ScanRequest, Severity


@pytest.mark.asyncio
async def test_orchestrator_finds_demo_repo_violations() -> None:
    repo_root = Path(__file__).resolve().parents[5]
    demo_repo = repo_root / "demo_repo"
    events: list[dict] = []

    async def emit(event: dict) -> None:
        events.append(event)

    summary = await ScanOrchestrator(default_agents()).run(
        ScanRequest(repo_path=str(demo_repo)),
        emit,
    )

    assert summary.total_findings == 10
    assert summary.counts_by_severity[Severity.CRITICAL] == 5
    assert summary.counts_by_severity[Severity.HIGH] == 3
    assert summary.counts_by_severity[Severity.MEDIUM] == 2
    assert events[0]["type"] == "scan_started"
    assert events[-1]["type"] == "scan_complete"

