import asyncio
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

SEVERITY_WEIGHTS = {
    Severity.CRITICAL: 18,
    Severity.HIGH: 10,
    Severity.MEDIUM: 5,
    Severity.LOW: 2,
}


class ScanOrchestrator:
    def __init__(self, agents: list[ScanAgent]) -> None:
        self._agents = agents

    async def run(self, request: ScanRequest, emit: EventEmitter) -> ScanSummary:
        repo_path = Path(request.repo_path).expanduser().resolve()
        if not repo_path.exists() or not repo_path.is_dir():
            raise ValueError("The repository path does not exist or is not a directory.")

        await emit(
            {
                "type": "scan_started",
                "repo_path": str(repo_path),
                "agents": [agent.name for agent in self._agents],
            }
        )

        results = await asyncio.gather(
            *(self._run_agent(agent, repo_path, emit) for agent in self._agents)
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

