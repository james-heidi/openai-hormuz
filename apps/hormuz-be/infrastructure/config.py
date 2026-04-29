import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from modules.scan.domain.errors import ScanConfigurationError


PLACEHOLDER_OPENAI_KEYS = {
    "your-api-key-here",
    "sk-...",
    "sk-your-api-key",
}


class BackendSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    api_port: int = Field(default=4000, validation_alias="API_PORT")
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000"],
        validation_alias="CORS_ORIGINS",
    )
    scan_allowed_roots: list[Path] = Field(
        default_factory=lambda: [_repo_root()],
        validation_alias="SCAN_ALLOWED_ROOTS",
    )
    scan_worktree_root: Path = Field(
        default_factory=lambda: _repo_root() / ".worktrees",
        validation_alias="SCAN_WORKTREE_ROOT",
    )

    openai_api_key: str | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    openai_agent_model: str | None = Field(default=None, validation_alias="OPENAI_AGENT_MODEL")
    openai_project: str | None = Field(default=None, validation_alias="OPENAI_PROJECT")
    openai_org_id: str | None = Field(default=None, validation_alias="OPENAI_ORG_ID")
    openai_base_url: str | None = Field(default=None, validation_alias="OPENAI_BASE_URL")

    github_token: str | None = Field(default=None, validation_alias="GITHUB_TOKEN")
    github_repository: str | None = Field(default=None, validation_alias="GITHUB_REPOSITORY")
    github_base_branch: str = Field(default="main", validation_alias="GITHUB_BASE_BRANCH")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors_origins(cls, value: Any) -> list[str]:
        if value is None or value == "":
            return ["http://localhost:3000"]
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("scan_allowed_roots", mode="before")
    @classmethod
    def _parse_scan_allowed_roots(cls, value: Any) -> list[Path]:
        if value is None or value == "":
            return [_repo_root()]
        if isinstance(value, str):
            return [
                _resolve_path(root)
                for root in value.split(os.pathsep)
                if root.strip()
            ]
        return value

    @field_validator("scan_allowed_roots", mode="after")
    @classmethod
    def _resolve_scan_allowed_roots(cls, value: list[Path]) -> list[Path]:
        return [_resolve_path(root) for root in value]

    @field_validator("scan_worktree_root", mode="after")
    @classmethod
    def _resolve_scan_worktree_root(cls, value: Path) -> Path:
        return _resolve_path(value)

    @property
    def github_pr_creation_enabled(self) -> bool:
        return bool(_clean_secret(self.github_token) and _clean_text(self.github_repository))

    def validate_for_scan(self) -> None:
        if not _clean_secret(self.openai_api_key):
            raise ScanConfigurationError(
                code="missing_openai_config",
                message=(
                    "OPENAI_API_KEY is required to run scans. Set it in .env "
                    "or export it before starting task be:dev."
                ),
            )


@lru_cache
def get_backend_settings() -> BackendSettings:
    return BackendSettings()


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _resolve_path(path: str | Path) -> Path:
    expanded = Path(path).expanduser()
    if not expanded.is_absolute():
        expanded = _repo_root() / expanded
    return expanded.resolve()


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _clean_secret(value: str | None) -> str | None:
    cleaned = _clean_text(value)
    if cleaned is None:
        return None
    if cleaned.lower() in PLACEHOLDER_OPENAI_KEYS:
        return None
    if "your-api-key" in cleaned.lower():
        return None
    return cleaned
