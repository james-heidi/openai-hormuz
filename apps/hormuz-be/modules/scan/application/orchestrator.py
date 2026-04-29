import asyncio
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import chain
from pathlib import Path
from typing import Any, Protocol

from modules.scan.application.regulation_mapper import attach_regulation_metadata
from modules.scan.application.repositories import RepositoryPreparationError, RepositoryPreparer
from modules.scan.domain.entities import (
    AgentFailure,
    AgentStatus,
    AgentUpdate,
    Finding,
    ScanRequest,
    ScanSummary,
    ScanStatus,
    Severity,
)
from modules.scan.domain.ports import EventEmitter, ScanAgent

SEVERITY_WEIGHTS = {
    Severity.CRITICAL: 18,
    Severity.HIGH: 10,
    Severity.MEDIUM: 5,
    Severity.LOW: 2,
}


class ScanRuntimeSettings(Protocol):
    scan_allowed_roots: Sequence[Path]

    def validate_for_scan(self) -> None:
        """Raise when required scan-time configuration is missing."""


@dataclass(frozen=True)
class AgentRunResult:
    findings: list[Finding]
    failure: AgentFailure | None = None


class ScanOrchestrator:
    def __init__(
        self,
        agents: list[ScanAgent],
        repository_preparer: RepositoryPreparer,
        settings: ScanRuntimeSettings,
    ) -> None:
        self._agents = agents
        self._repository_preparer = repository_preparer
        self._settings = settings

    async def run(self, request: ScanRequest, emit: EventEmitter) -> ScanSummary:
        self._settings.validate_for_scan()
        source = _validate_scan_source(request.repo_path, self._settings.scan_allowed_roots)
        events = _ScanRunEvents(emit)

        await events.emit(
            {
                "type": "scan_started",
                "repo_path": source,
                "agents": [agent.name for agent in self._agents],
            }
        )
        for agent in self._agents:
            await events.emit_update(agent.name, AgentStatus.IDLE, "Waiting", 0)

        with self._repository_preparer.prepare(
            source, [agent.name for agent in self._agents]
        ) as repo:
            results = await asyncio.gather(
                *(
                    self._run_agent(agent, repo.worktree_for(agent.name), events)
                    for agent in self._agents
                )
            )
        findings = sorted(
            (
                attach_regulation_metadata(finding)
                for finding in chain.from_iterable(result.findings for result in results)
            ),
            key=lambda finding: (finding.file_path, finding.line or 0, finding.id),
        )
        failed_agents = [result.failure for result in results if result.failure is not None]

        summary = ScanSummary(
            scan_status=_scan_status(
                total_agents=len(self._agents), failed_agents=len(failed_agents)
            ),
            score=_score(findings),
            total_findings=len(findings),
            counts_by_severity=_counts_by_severity(findings),
            counts_by_agent=_counts_by_agent(findings, [agent.name for agent in self._agents]),
            findings=findings,
            failed_agents=failed_agents,
        )
        await events.emit({"type": "scan_complete", "summary": summary.model_dump(mode="json")})
        return summary

    async def _run_agent(
        self, agent: ScanAgent, repo_path: Path, events: "_ScanRunEvents"
    ) -> AgentRunResult:
        try:
            findings = await agent.scan(repo_path, events.emit)
            for finding in findings:
                await events.emit_finding(finding)
            return AgentRunResult(findings=findings)
        except Exception as exc:
            failure = AgentFailure(agent=agent.name, message=str(exc))
            await events.emit_update(agent.name, AgentStatus.ERROR, str(exc), 100)
            return AgentRunResult(findings=[], failure=failure)


class _ScanRunEvents:
    def __init__(self, emit: EventEmitter) -> None:
        self._emit = emit
        self._lock = asyncio.Lock()
        self._emitted_finding_ids: set[str] = set()

    async def emit(self, event: dict[str, Any]) -> None:
        async with self._lock:
            if event.get("type") == "finding":
                event = _enriched_finding_event(event)
                finding = event.get("finding")
                finding_id = finding.get("id") if isinstance(finding, dict) else None
                if finding_id in self._emitted_finding_ids:
                    return
                if finding_id:
                    self._emitted_finding_ids.add(finding_id)
            await self._emit(event)

    async def emit_update(
        self, agent: str, status: AgentStatus, message: str, progress: int
    ) -> None:
        update = AgentUpdate(agent=agent, status=status, message=message, progress=progress)
        await self.emit({"type": "agent_update", "update": update.model_dump(mode="json")})

    async def emit_finding(self, finding: Finding) -> None:
        await self.emit({"type": "finding", "finding": finding.model_dump(mode="json")})


def _enriched_finding_event(event: dict[str, Any]) -> dict[str, Any]:
    finding = event.get("finding")
    if isinstance(finding, Finding):
        enriched = attach_regulation_metadata(finding)
    elif isinstance(finding, dict):
        enriched = attach_regulation_metadata(Finding.model_validate(finding))
    else:
        return event
    return {**event, "finding": enriched.model_dump(mode="json")}


def _counts_by_severity(findings: list[Finding]) -> dict[Severity, int]:
    counts = {severity: 0 for severity in Severity}
    for finding in findings:
        counts[finding.severity] += 1
    return counts


def _counts_by_agent(findings: list[Finding], agent_names: list[str]) -> dict[str, int]:
    counts = dict.fromkeys(agent_names, 0)
    for finding in findings:
        counts[finding.agent] = counts.get(finding.agent, 0) + 1
    return counts


def _scan_status(total_agents: int, failed_agents: int) -> ScanStatus:
    if failed_agents == 0:
        return ScanStatus.COMPLETE
    if failed_agents == total_agents:
        return ScanStatus.FAILED
    return ScanStatus.PARTIAL


def _score(findings: list[Finding]) -> int:
    penalty = sum(SEVERITY_WEIGHTS[finding.severity] for finding in findings)
    return max(0, 100 - penalty)


def _validate_scan_source(source: str, allowed_roots: Sequence[Path]) -> str:
    source = source.strip()
    if not source:
        raise RepositoryPreparationError("invalid_repo_source", "The repository source is empty.")

    repo_path = Path(source).expanduser()
    if repo_path.exists():
        repo_path = repo_path.resolve()
        if not repo_path.is_dir():
            raise RepositoryPreparationError(
                "invalid_repo_path",
                "The repository path does not exist or is not a directory.",
            )
        if not _is_allowed_scan_root(repo_path, allowed_roots):
            raise RepositoryPreparationError(
                "invalid_repo_path",
                "The repository path is outside the configured scan roots.",
            )
        return str(repo_path)

    return source


def _is_allowed_scan_root(repo_path: Path, allowed_roots: Sequence[Path]) -> bool:
    return any(_is_relative_to(repo_path, root) for root in allowed_roots)


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True
