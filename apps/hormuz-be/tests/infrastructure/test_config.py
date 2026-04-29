import os
from pathlib import Path

import pytest

from infrastructure.config import BackendSettings
from modules.scan.domain.errors import ScanConfigurationError


def test_backend_settings_rejects_missing_openai_key() -> None:
    settings = BackendSettings(OPENAI_API_KEY="")

    with pytest.raises(ScanConfigurationError, match="OPENAI_API_KEY"):
        settings.validate_for_scan()


def test_backend_settings_rejects_placeholder_openai_key() -> None:
    settings = BackendSettings(OPENAI_API_KEY="your-api-key-here")

    with pytest.raises(ScanConfigurationError, match="OPENAI_API_KEY"):
        settings.validate_for_scan()


def test_backend_settings_parses_scan_roots(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    settings = BackendSettings(
        SCAN_ALLOWED_ROOTS=os.pathsep.join([str(first), str(second)])
    )

    assert settings.scan_allowed_roots == [first.resolve(), second.resolve()]


def test_backend_settings_resolves_relative_worktree_root_from_repo_root() -> None:
    settings = BackendSettings(SCAN_WORKTREE_ROOT=".worktrees")
    repo_root = Path(__file__).resolve().parents[4]

    assert settings.scan_worktree_root == repo_root / ".worktrees"


def test_github_pr_creation_is_opt_in() -> None:
    assert not BackendSettings(OPENAI_API_KEY="sk-test").github_pr_creation_enabled
    assert not BackendSettings(
        OPENAI_API_KEY="sk-test",
        GITHUB_TOKEN="ghp_test",
    ).github_pr_creation_enabled
    assert BackendSettings(
        OPENAI_API_KEY="sk-test",
        GITHUB_TOKEN="ghp_test",
        GITHUB_REPOSITORY="owner/repo",
    ).github_pr_creation_enabled
