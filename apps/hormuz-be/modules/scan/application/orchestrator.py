import asyncio
import os
from itertools import chain
from pathlib import Path

from modules.scan.domain.entities import (
    AgentStatus,
    AgentUpdate,
    Finding,
    ScanRequest,
    ScanSummary,
    Severity,
)
from modules.scan.domain.ports import EventEmitter, ScanAgent
from modules.scan.application.repositories import RepositoryPreparationError, RepositoryPreparer

SEVERITY_WEIGHTS = {
    Severity.CRITICAL: 18,
    Severity.HIGH: 10,
    Severity.MEDIUM: 5,
    Severity.LOW: 2,
}


class ScanOrchestrator:
    def __init__(self, agents: list[ScanAgent], repository_preparer: RepositoryPreparer) -> None:
        self._agents = agents
        self._repository_preparer = repository_preparer

    async def run(self, request: ScanRequest, emit: EventEmitter) -> ScanSummary:
        source = _validate_scan_source(request.repo_path)

        await emit(
            {
                "type": "scan_started",
                "repo_path": source,
                "agents": [agent.name for agent in self._agents],
            }
        )

        with self._repository_preparer.prepare(source, [agent.name for agent in self._agents]) as repo:
            results = await asyncio.gather(
                *(
                    self._run_agent(agent, repo.worktree_for(agent.name), emit)
                    for agent in self._agents
                )
            )
        findings = sorted(
            chain.from_iterable(results),
            key=lambda finding: (finding.file_path, finding.line or 0, finding.id),
        )

        for finding in findings:
            await emit({"type": "finding", "finding": finding.model_dump(mode="json")})

        summary = ScanSummary(
            score=_score(findings),
            total_findings=len(findings),
            counts_by_severity=_counts_by_severity(findings),
            findings=findings,
        )
        await emit({"type": "scan_complete", "summary": summary.model_dump(mode="json")})
        return summary

    async def _run_agent(
        self, agent: ScanAgent, repo_path: Path, emit: EventEmitter
    ) -> list[Finding]:
        try:
            return await agent.scan(repo_path, emit)
        except Exception as exc:
            update = AgentUpdate(
                agent=agent.name,
                status=AgentStatus.ERROR,
                message=str(exc),
                progress=100,
            )
            await emit({"type": "agent_update", "update": update.model_dump(mode="json")})
            return []


def _counts_by_severity(findings: list[Finding]) -> dict[Severity, int]:
    counts = {severity: 0 for severity in Severity}
    for finding in findings:
        counts[finding.severity] += 1
    return counts


def _score(findings: list[Finding]) -> int:
    penalty = sum(SEVERITY_WEIGHTS[finding.severity] for finding in findings)
    return max(0, 100 - penalty)


def _is_allowed_scan_root(repo_path: Path) -> bool:
    return any(_is_relative_to(repo_path, root) for root in _allowed_scan_roots())


def _validate_scan_source(source: str) -> str:
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
        if not _is_allowed_scan_root(repo_path):
            raise RepositoryPreparationError(
                "invalid_repo_path",
                "The repository path is outside the configured scan roots.",
            )
        return str(repo_path)

    return source


def _allowed_scan_roots() -> list[Path]:
    configured = os.environ.get("SCAN_ALLOWED_ROOTS")
    if configured:
        return [
            Path(root).expanduser().resolve()
            for root in configured.split(os.pathsep)
            if root.strip()
        ]
    return [Path(__file__).resolve().parents[5]]


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True
