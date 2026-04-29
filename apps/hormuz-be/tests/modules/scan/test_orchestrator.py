import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

from modules.scan.adapters.outbound.git_repository import GitRepositoryPreparer
from modules.scan.application.orchestrator import ScanOrchestrator
from modules.scan.application.repositories import RepositoryPreparationError
from modules.scan.application.rule_catalog import default_agents
from modules.scan.domain.entities import ScanRequest, Severity
from modules.scan.domain.errors import ScanConfigurationError


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

    assert summary.total_findings == 10
    assert summary.counts_by_severity[Severity.CRITICAL] == 5
    assert summary.counts_by_severity[Severity.HIGH] == 3
    assert summary.counts_by_severity[Severity.MEDIUM] == 2
    assert events[0]["type"] == "scan_started"
    assert events[-1]["type"] == "scan_complete"
    assert not list(scan_storage.iterdir())


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
