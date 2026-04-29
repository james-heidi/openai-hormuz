from pathlib import Path

import pytest

from modules.scan.application.orchestrator import ScanOrchestrator
from modules.scan.application.rule_catalog import default_agents
from modules.scan.domain.entities import ScanRequest, Severity


@pytest.mark.asyncio
async def test_orchestrator_finds_demo_target_violations(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    demo_target = tmp_path / "openai-hormuz-demo-repo"
    _write_demo_fixture(demo_target)
    monkeypatch.setenv("SCAN_ALLOWED_ROOTS", str(tmp_path))
    events: list[dict] = []

    async def emit(event: dict) -> None:
        events.append(event)

    summary = await ScanOrchestrator(default_agents()).run(
        ScanRequest(repo_path=str(demo_target)),
        emit,
    )

    assert summary.total_findings == 10
    assert summary.counts_by_severity[Severity.CRITICAL] == 5
    assert summary.counts_by_severity[Severity.HIGH] == 3
    assert summary.counts_by_severity[Severity.MEDIUM] == 2
    assert events[0]["type"] == "scan_started"
    assert events[-1]["type"] == "scan_complete"


@pytest.mark.asyncio
async def test_orchestrator_rejects_paths_outside_allowed_roots() -> None:
    async def emit(_event: dict) -> None:
        return None

    with pytest.raises(ValueError, match="outside the configured scan roots"):
        await ScanOrchestrator(default_agents()).run(
            ScanRequest(repo_path="/"),
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
