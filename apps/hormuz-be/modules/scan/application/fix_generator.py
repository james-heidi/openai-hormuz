import difflib
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from modules.scan.application.orchestrator import ScanOrchestrator
from modules.scan.application.repositories import RepositoryPreparationError, RepositoryPreparer
from modules.scan.domain.entities import (
    FixFailure,
    FixOutputType,
    FixPatch,
    FixRequest,
    FixSummary,
    ScanRequest,
)
from modules.scan.domain.ports import FixAgent, PullRequestPublisher


class FixRuntimeSettings(Protocol):
    scan_allowed_roots: Sequence[Path]
    scan_worktree_root: Path


@dataclass(frozen=True)
class FixSource:
    source: str
    local_repo_path: Path | None


class FixGenerator:
    def __init__(
        self,
        fix_agent: FixAgent,
        scan_orchestrator: ScanOrchestrator,
        repository_preparer: RepositoryPreparer,
        settings: FixRuntimeSettings,
        pr_publisher: PullRequestPublisher | None = None,
    ) -> None:
        self._fix_agent = fix_agent
        self._scan_orchestrator = scan_orchestrator
        self._repository_preparer = repository_preparer
        self._settings = settings
        self._pr_publisher = pr_publisher

    async def generate(self, request: FixRequest) -> FixSummary:
        fix_source = _validate_fix_source(request.repo_path, self._settings.scan_allowed_roots)
        original_by_file: dict[str, str] = {}
        updated_by_file: dict[str, str] = {}
        patches: list[FixPatch] = []
        failures: list[FixFailure] = []
        rescan_summary = None

        with self._repository_preparer.prepare(
            fix_source.source, [self._fix_agent.name]
        ) as prepared:
            repo_path = prepared.worktree_for(self._fix_agent.name)
            for finding in request.findings:
                try:
                    relative_path, absolute_path = _resolve_finding_file(repo_path, finding.file_path)
                    if relative_path not in original_by_file:
                        original = absolute_path.read_text(errors="ignore")
                        original_by_file[relative_path] = original
                        updated_by_file[relative_path] = original

                    before = updated_by_file[relative_path]
                    after = await self._fix_agent.fix(finding, before)
                    if after is None or after == before:
                        failures.append(
                            FixFailure(
                                finding_id=finding.id,
                                file_path=finding.file_path,
                                code="unsupported_finding",
                                message="No patch writer produced a change for this finding.",
                            )
                        )
                        continue

                    patches.append(
                        FixPatch(
                            finding_id=finding.id,
                            file_path=relative_path,
                            diff=_unified_diff(relative_path, before, after),
                        )
                    )
                    updated_by_file[relative_path] = after
                except Exception as exc:
                    failures.append(
                        FixFailure(
                            finding_id=finding.id,
                            file_path=finding.file_path,
                            code="fix_failed",
                            message=str(exc),
                        )
                    )

            changed_files = {
                relative_path: updated
                for relative_path, updated in updated_by_file.items()
                if updated != original_by_file[relative_path]
            }
            combined_diff = "".join(
                _unified_diff(relative_path, original_by_file[relative_path], updated)
                for relative_path, updated in changed_files.items()
            )
            patch_path = (
                _write_patch_file(fix_source, self._settings, request.patch_dir, combined_diff)
                if combined_diff
                else None
            )
            if patch_path is not None:
                patches = [patch.model_copy(update={"patch_path": patch_path}) for patch in patches]

            applied = _apply_changes(request, fix_source, changed_files, failures)
            if applied:
                patches = [patch.model_copy(update={"applied": True}) for patch in patches]

            output_type = FixOutputType.LOCAL_DIFF
            pr_url: str | None = None
            if request.create_pr and changed_files:
                pr_url = await self._try_create_pr(prepared.base_repo_path, changed_files, failures)
                if pr_url is not None:
                    output_type = FixOutputType.GITHUB_PR

            if request.rescan:
                try:
                    rescan_source = fix_source.source
                    if changed_files:
                        _write_changed_files(repo_path, changed_files)
                        _commit_temporary_fix(repo_path)
                        rescan_source = str(repo_path)
                    rescan_summary = await self._scan_orchestrator.run(
                        ScanRequest(repo_path=rescan_source),
                        _discard_event,
                    )
                except Exception as exc:
                    failures.append(
                        FixFailure(
                            code="rescan_failed",
                            message=str(exc),
                        )
                    )

        return FixSummary(
            output_type=output_type,
            pr_url=pr_url,
            patch_path=patch_path,
            diff=combined_diff,
            patches=patches,
            failures=failures,
            applied=applied,
            rescan_summary=rescan_summary,
        )

    async def _try_create_pr(
        self,
        repo_path: Path,
        changed_files: dict[str, str],
        failures: list[FixFailure],
    ) -> str | None:
        if self._pr_publisher is None or not self._pr_publisher.is_configured(repo_path):
            failures.append(
                FixFailure(
                    code="github_pr_unconfigured",
                    message="GitHub PR creation is not configured; returning a local diff instead.",
                )
            )
            return None

        try:
            return await self._pr_publisher.create_pull_request(
                repo_path=repo_path,
                title="Compliance Codex auto-fixes",
                body=_pull_request_body(changed_files),
                changed_files=changed_files,
            )
        except Exception as exc:
            failures.append(
                FixFailure(
                    code="github_pr_failed",
                    message=f"GitHub PR creation failed; returning a local diff instead: {exc}",
                )
            )
            return None


async def _discard_event(_event: dict) -> None:
    return None


def _validate_fix_source(source: str, allowed_roots: Sequence[Path]) -> FixSource:
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
        return FixSource(source=str(repo_path), local_repo_path=repo_path)

    return FixSource(source=source, local_repo_path=None)


def _resolve_finding_file(repo_path: Path, file_path: str) -> tuple[str, Path]:
    absolute_path = (repo_path / file_path).resolve()
    if not _is_relative_to(absolute_path, repo_path):
        raise ValueError("Finding file path is outside the repository.")
    if not absolute_path.exists() or not absolute_path.is_file():
        raise ValueError("Finding file path does not exist.")
    return absolute_path.relative_to(repo_path).as_posix(), absolute_path


def _unified_diff(relative_path: str, before: str, after: str) -> str:
    return "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=f"a/{relative_path}",
            tofile=f"b/{relative_path}",
        )
    )


def _write_patch_file(
    fix_source: FixSource,
    settings: FixRuntimeSettings,
    patch_dir: str | None,
    diff: str,
) -> str:
    output_dir = _resolve_patch_dir(fix_source, settings, patch_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")
    patch_path = output_dir / f"hormuz-autofix-{timestamp}.patch"
    patch_path.write_text(diff)
    return str(patch_path)


def _resolve_patch_dir(
    fix_source: FixSource,
    settings: FixRuntimeSettings,
    patch_dir: str | None,
) -> Path:
    if patch_dir is None:
        if fix_source.local_repo_path is not None:
            return fix_source.local_repo_path / ".hormuz" / "fixes"
        return settings.scan_worktree_root / "fixes"

    candidate = Path(patch_dir).expanduser()
    if not candidate.is_absolute():
        base = fix_source.local_repo_path or settings.scan_worktree_root
        candidate = base / candidate
    resolved = candidate.resolve()
    if fix_source.local_repo_path is not None and not _is_relative_to(
        resolved, fix_source.local_repo_path
    ):
        raise ValueError("The patch directory must be inside the repository.")
    return resolved


def _apply_changes(
    request: FixRequest,
    fix_source: FixSource,
    changed_files: dict[str, str],
    failures: list[FixFailure],
) -> bool:
    if not request.apply or not changed_files:
        return False
    if fix_source.local_repo_path is None:
        failures.append(
            FixFailure(
                code="apply_unavailable",
                message="Fixes can only be applied directly when repo_path is a local repository.",
            )
        )
        return False

    for relative_path, updated in changed_files.items():
        (fix_source.local_repo_path / relative_path).write_text(updated)
    return True


def _write_changed_files(repo_path: Path, changed_files: dict[str, str]) -> None:
    for relative_path, updated in changed_files.items():
        (repo_path / relative_path).write_text(updated)


def _commit_temporary_fix(repo_path: Path) -> None:
    subprocess.run(
        ["git", "add", "."],
        cwd=repo_path,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Hormuz Auto Fix",
            "-c",
            "user.email=hormuz@example.com",
            "commit",
            "-m",
            "Apply Compliance Codex fixes",
        ],
        cwd=repo_path,
        check=True,
        capture_output=True,
        text=True,
    )


def _pull_request_body(changed_files: dict[str, str]) -> str:
    files = "\n".join(f"- `{relative_path}`" for relative_path in sorted(changed_files))
    return (
        "Generated by Compliance Codex auto-fix.\n\n"
        "Changed files:\n"
        f"{files}\n\n"
        "If GitHub publishing fails, the API response still includes a local diff."
    )


def _is_allowed_scan_root(repo_path: Path, allowed_roots: Sequence[Path]) -> bool:
    return any(_is_relative_to(repo_path, root) for root in allowed_roots)


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True
