from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from modules.scan.domain.entities import AgentStatus, AgentUpdate, Finding, RegulationRef, Severity
from modules.scan.domain.ports import EventEmitter, ScanAgent

SOURCE_SUFFIXES = {".py", ".js", ".jsx", ".ts", ".tsx"}
SKIP_DIRS = {".git", ".venv", "__pycache__", "node_modules", "dist", "build"}
PROMPT_DIR = Path(__file__).resolve().parents[1] / "prompts"


@dataclass(frozen=True)
class SourceMatch:
    rule_id: str
    title: str
    category: str
    severity: Severity
    description: str
    recommendation: str
    regulations: tuple[RegulationRef, ...]
    file_path: Path
    line: int | None = None
    snippet: str | None = None
    violation_type: str | None = None
    context: str | None = None
    remediation_hint: str | None = None


class BackendScannerAgent(ScanAgent):
    name: str
    category: str
    prompt_name: str | None = None

    def __init__(self, name: str, category: str) -> None:
        self.name = name
        self.category = category

    async def scan(self, repo_path: Path, emit: EventEmitter) -> list[Finding]:
        files = list(self.iter_source_files(repo_path))
        findings: list[Finding] = []
        seen: set[tuple[str, str, int, str | None]] = set()

        await emit_update(emit, self.name, AgentStatus.RUNNING, "Scanning source files", 5)

        total = max(len(files), 1)
        for index, file_path in enumerate(files, start=1):
            text = file_path.read_text(errors="ignore")
            for match in self.find_matches(file_path, text, repo_path):
                line = match.line or 0
                key = (match.rule_id, str(match.file_path), line, match.context)
                if key in seen:
                    continue
                seen.add(key)
                finding = self.to_finding(match, repo_path)
                findings.append(finding)
                await emit({"type": "finding", "finding": finding.model_dump(mode="json")})

            progress = 5 + round(index / total * 90)
            await emit_update(emit, self.name, AgentStatus.RUNNING, file_path.name, progress)

        await emit_update(emit, self.name, AgentStatus.DONE, "Scan complete", 100)
        return findings

    def iter_source_files(self, repo_path: Path) -> Iterable[Path]:
        for file_path in sorted(repo_path.rglob("*")):
            if any(part in SKIP_DIRS for part in file_path.parts):
                continue
            if file_path.is_file() and file_path.suffix in SOURCE_SUFFIXES:
                yield file_path

    def find_matches(
        self, file_path: Path, text: str, repo_path: Path
    ) -> Iterable[SourceMatch]:
        raise NotImplementedError

    def prompt_text(self) -> str | None:
        if self.prompt_name is None:
            return None
        return (PROMPT_DIR / self.prompt_name).read_text()

    def to_finding(self, match: SourceMatch, repo_path: Path) -> Finding:
        relative_path = match.file_path.relative_to(repo_path)
        return Finding(
            id=f"{match.rule_id}:{relative_path}:{match.line or 0}",
            agent=self.name,
            category=match.category,
            violation_type=match.violation_type,
            severity=match.severity,
            file_path=str(relative_path),
            line=match.line,
            context=match.context,
            title=match.title,
            description=match.description,
            snippet=match.snippet,
            regulations=list(match.regulations),
            recommendation=match.recommendation,
            remediation_hint=match.remediation_hint or match.recommendation,
        )


async def emit_update(
    emit: EventEmitter, agent: str, status: AgentStatus, message: str, progress: int
) -> None:
    update = AgentUpdate(agent=agent, status=status, message=message, progress=progress)
    await emit({"type": "agent_update", "update": update.model_dump(mode="json")})
