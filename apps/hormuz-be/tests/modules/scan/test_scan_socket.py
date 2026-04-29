import subprocess
from pathlib import Path

from fastapi.testclient import TestClient

from infrastructure.config import get_backend_settings
from main import app
from modules.scan import get_scan_orchestrator


def test_scan_socket_streams_findings_and_complete(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_path = tmp_path / "target"
    repo_path.mkdir()
    (repo_path / "auth.py").write_text('JWT_SECRET = "super-secret"\n')
    _commit_fixture(repo_path)
    _configure_scan_env(monkeypatch, tmp_path)

    with TestClient(app) as client:
        with client.websocket_connect("/ws/scan") as websocket:
            websocket.send_json({"repo_path": str(repo_path)})
            events = _receive_until_scan_complete(websocket)

    assert [event["type"] for event in events][-1] == "scan_complete"
    assert any(event["type"] == "scan_started" for event in events)
    assert any(event["type"] == "agent_update" for event in events)
    assert any(event["type"] == "finding" for event in events)
    assert events[-1]["summary"]["total_findings"] == 1


def test_scan_socket_returns_structured_validation_error() -> None:
    with TestClient(app) as client:
        with client.websocket_connect("/ws/scan") as websocket:
            websocket.send_json({})
            event = websocket.receive_json()

    assert event == {
        "type": "error",
        "detail": {
            "code": "invalid_scan_request",
            "message": "Scan request must include a non-empty repo_path.",
        },
    }


def test_scan_socket_returns_structured_json_error() -> None:
    with TestClient(app) as client:
        with client.websocket_connect("/ws/scan") as websocket:
            websocket.send_text("not json")
            event = websocket.receive_json()

    assert event == {
        "type": "error",
        "detail": {
            "code": "invalid_scan_request",
            "message": "Scan request must be valid JSON.",
        },
    }


def _configure_scan_env(monkeypatch, allowed_root: Path) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("SCAN_ALLOWED_ROOTS", str(allowed_root))
    get_backend_settings.cache_clear()
    get_scan_orchestrator.cache_clear()


def _receive_until_scan_complete(websocket) -> list[dict]:
    events: list[dict] = []
    while True:
        event = websocket.receive_json()
        events.append(event)
        if event["type"] == "scan_complete":
            return events


def _commit_fixture(repo_path: Path) -> None:
    _git(repo_path, "init")
    _git(repo_path, "checkout", "-b", "main")
    _git(repo_path, "config", "user.name", "Hormuz Test")
    _git(repo_path, "config", "user.email", "hormuz@example.com")
    _git(repo_path, "add", ".")
    _git(repo_path, "commit", "-m", "socket fixture")


def _git(repo_path: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=repo_path,
        check=True,
        capture_output=True,
        text=True,
    )
