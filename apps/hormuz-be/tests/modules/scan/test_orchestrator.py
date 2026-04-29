import asyncio
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

from modules.scan.adapters.outbound.git_repository import GitRepositoryPreparer
from modules.scan.application.orchestrator import ScanOrchestrator
from modules.scan.application.repositories import RepositoryPreparationError
from modules.scan.application.rule_catalog import default_agents
from modules.scan.application.scanners.api_auditor import API_OVEREXPOSURE, ApiAuditorAgent
from modules.scan.domain.entities import AgentStatus, Finding, ScanRequest, Severity
from modules.scan.domain.errors import ScanConfigurationError
from modules.scan.domain.ports import EventEmitter, ScanAgent


@dataclass(frozen=True)
class StaticRuntimeSettings:
    scan_allowed_roots: list[Path]
    openai_configured: bool = True

    def validate_for_scan(self) -> None:
        if not self.openai_configured:
            raise ScanConfigurationError(
                code="missing_openai_config",
                message="OPENAI_API_KEY is required to run scans.",
            )


@pytest.mark.asyncio
async def test_orchestrator_finds_demo_target_violations(tmp_path: Path) -> None:
    demo_target = tmp_path / "openai-hormuz-demo-repo"
    _write_demo_fixture(demo_target)
    scan_storage = tmp_path / "scan-workspaces"
    events: list[dict] = []

    async def emit(event: dict) -> None:
        events.append(event)

    summary = await ScanOrchestrator(
        default_agents(),
        GitRepositoryPreparer(scan_storage),
        StaticRuntimeSettings([tmp_path]),
    ).run(
        ScanRequest(repo_path=str(demo_target)),
        emit,
    )

    assert summary.total_findings == 11
    assert summary.counts_by_severity[Severity.CRITICAL] == 5
    assert summary.counts_by_severity[Severity.HIGH] == 4
    assert summary.counts_by_severity[Severity.MEDIUM] == 2
    assert events[0]["type"] == "scan_started"
    assert events[-1]["type"] == "scan_complete"
    assert not list(scan_storage.iterdir())
    assert _agents_with_status(events, AgentStatus.IDLE) == {
        "PII Scanner",
        "API Auditor",
        "Auth Checker",
    }
    first_finding_index = next(
        index for index, event in enumerate(events) if event["type"] == "finding"
    )
    first_finding_agent = events[first_finding_index]["finding"]["agent"]
    agent_done_index = next(
        index
        for index, event in enumerate(events)
        if event["type"] == "agent_update"
        and event["update"]["agent"] == first_finding_agent
        and event["update"]["status"] == AgentStatus.DONE
    )
    assert first_finding_index < agent_done_index

    overexposure_findings = [
        finding for finding in summary.findings if finding.violation_type == API_OVEREXPOSURE
    ]
    assert len(overexposure_findings) == 2
    assert {finding.context for finding in overexposure_findings} == {
        "GET /admin/all-users -> get_all_users; model User",
        "GET /users/{id} -> get_user; model User",
    }
    for finding in overexposure_findings:
        assert finding.agent == "API Auditor"
        assert finding.category == "api"
        assert finding.severity == Severity.HIGH
        assert finding.file_path == "api/users.py"
        assert finding.line is not None
        assert finding.description
        assert finding.remediation_hint
        assert finding.regulations


@pytest.mark.asyncio
async def test_orchestrator_rejects_paths_outside_allowed_roots() -> None:
    async def emit(_event: dict) -> None:
        return None

    with pytest.raises(RepositoryPreparationError, match="outside the configured scan roots"):
        await ScanOrchestrator(
            default_agents(),
            GitRepositoryPreparer(),
            StaticRuntimeSettings([Path.cwd()]),
        ).run(
            ScanRequest(repo_path="/"),
            emit,
        )


@pytest.mark.asyncio
async def test_orchestrator_rejects_missing_openai_config(tmp_path: Path) -> None:
    demo_target = tmp_path / "openai-hormuz-demo-repo"
    _write_demo_fixture(demo_target)

    async def emit(_event: dict) -> None:
        return None

    with pytest.raises(ScanConfigurationError, match="OPENAI_API_KEY"):
        await ScanOrchestrator(
            default_agents(),
            GitRepositoryPreparer(),
            StaticRuntimeSettings([tmp_path], openai_configured=False),
        ).run(
            ScanRequest(repo_path=str(demo_target)),
            emit,
        )


@pytest.mark.asyncio
async def test_orchestrator_starts_configured_agents_concurrently(tmp_path: Path) -> None:
    demo_target = tmp_path / "openai-hormuz-demo-repo"
    _write_demo_fixture(demo_target)
    release = asyncio.Event()
    agents = [
        BlockingAgent("PII Scanner", "pii", release),
        BlockingAgent("API Auditor", "api", release),
    ]

    async def emit(_event: dict) -> None:
        return None

    scan = asyncio.create_task(
        ScanOrchestrator(
            agents,
            GitRepositoryPreparer(tmp_path / "scan-workspaces"),
            StaticRuntimeSettings([tmp_path]),
        ).run(ScanRequest(repo_path=str(demo_target)), emit)
    )

    await asyncio.wait_for(
        asyncio.gather(*(agent.started.wait() for agent in agents)),
        timeout=0.2,
    )
    release.set()
    summary = await scan

    assert summary.total_findings == 0


@pytest.mark.asyncio
async def test_orchestrator_keeps_successful_findings_when_one_agent_fails(
    tmp_path: Path,
) -> None:
    demo_target = tmp_path / "openai-hormuz-demo-repo"
    _write_demo_fixture(demo_target)
    events: list[dict] = []

    async def emit(event: dict) -> None:
        events.append(event)

    summary = await ScanOrchestrator(
        [
            FindingAgent("PII Scanner", "pii", _finding(agent="PII Scanner", category="pii")),
            FailingAgent("Auth Checker", "auth"),
        ],
        GitRepositoryPreparer(tmp_path / "scan-workspaces"),
        StaticRuntimeSettings([tmp_path]),
    ).run(ScanRequest(repo_path=str(demo_target)), emit)

    assert summary.total_findings == 1
    assert summary.findings[0].agent == "PII Scanner"
    assert any(event["type"] == "finding" for event in events)
    assert any(
        event["type"] == "agent_update"
        and event["update"]["agent"] == "Auth Checker"
        and event["update"]["status"] == AgentStatus.ERROR
        and event["update"]["message"] == "auth agent unavailable"
        for event in events
    )


def test_api_auditor_prompt_forces_structured_json() -> None:
    prompt = ApiAuditorAgent().prompt_text()

    assert prompt is not None
    assert "Return only valid JSON" in prompt
    assert API_OVEREXPOSURE in prompt
    assert '"findings"' in prompt


def test_default_agents_can_fall_back_to_two_scanners(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SCAN_ENABLED_AGENTS", "pii,api")

    agents = default_agents()

    assert [agent.category for agent in agents] == ["pii", "api"]


def _write_demo_fixture(repo_path: Path) -> None:
    (repo_path / "api").mkdir(parents=True)
    (repo_path / "auth.py").write_text(
        """
import logging

logger = logging.getLogger(__name__)

JWT_SECRET = "super-secret-key-do-not-share-12345"


def login(email, password):
    logger.info(f"Login attempt: email={email}, password={password}")


def get_user(email_input):
    return f"SELECT * FROM users WHERE email = '{email_input}'"
""".lstrip()
    )
    (repo_path / "api" / "users.py").write_text(
        """
class User:
    pass


@app.get("/users/{id}")
def get_user(id: int):
    user = db.query(User).get(id)
    return user.__dict__


@app.get("/admin/all-users")
def get_all_users():
    return db.query(User).all()
""".lstrip()
    )
    (repo_path / "models.py").write_text(
        """
class User:
    password = Column(String)
    # No deletion policy, no retention timestamp
""".lstrip()
    )
    (repo_path / "middleware.py").write_text(
        """
import traceback

app.add_middleware(CORSMiddleware, allow_origins=["*"])


def handle_error(request, exc):
    return {"trace": traceback.format_exc()}
""".lstrip()
    )
    (repo_path / "email_service.py").write_text(
        """
def send_analytics(user):
    requests.post("https://analytics.example.com", json={"email": user.email})
""".lstrip()
    )
    _commit_fixture(repo_path)


def _commit_fixture(repo_path: Path) -> None:
    _git(repo_path, "init")
    _git(repo_path, "checkout", "-b", "main")
    _git(repo_path, "config", "user.name", "Hormuz Test")
    _git(repo_path, "config", "user.email", "hormuz@example.com")
    _git(repo_path, "add", ".")
    _git(repo_path, "commit", "-m", "demo fixture")


def _git(repo_path: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=repo_path,
        check=True,
        capture_output=True,
        text=True,
    )


def _agents_with_status(events: list[dict], status: AgentStatus) -> set[str]:
    return {
        event["update"]["agent"]
        for event in events
        if event["type"] == "agent_update" and event["update"]["status"] == status
    }


def _finding(agent: str, category: str) -> Finding:
    return Finding(
        id=f"{category}:fixture.py:1",
        agent=agent,
        category=category,
        severity=Severity.HIGH,
        file_path="fixture.py",
        line=1,
        title="Fixture finding",
        description="A deterministic test finding.",
        recommendation="Fix the deterministic test finding.",
    )


class BlockingAgent(ScanAgent):
    def __init__(self, name: str, category: str, release: asyncio.Event) -> None:
        self.name = name
        self.category = category
        self.release = release
        self.started = asyncio.Event()

    async def scan(self, _repo_path: Path, _emit: EventEmitter) -> list[Finding]:
        self.started.set()
        await self.release.wait()
        return []


class FindingAgent(ScanAgent):
    def __init__(self, name: str, category: str, finding: Finding) -> None:
        self.name = name
        self.category = category
        self.finding = finding

    async def scan(self, _repo_path: Path, _emit: EventEmitter) -> list[Finding]:
        return [self.finding]


class FailingAgent(ScanAgent):
    def __init__(self, name: str, category: str) -> None:
        self.name = name
        self.category = category

    async def scan(self, _repo_path: Path, _emit: EventEmitter) -> list[Finding]:
        raise RuntimeError("auth agent unavailable")
