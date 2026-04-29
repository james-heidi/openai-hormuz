import os
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Mapping

from modules.scan.domain.ports import PullRequestPublisher


class GitHubPullRequestPublisher(PullRequestPublisher):
    def __init__(
        self,
        token: str | None = None,
        repository: str | None = None,
        base_branch: str | None = None,
    ) -> None:
        self._token = token
        self._repository = repository
        self._base_branch = base_branch

    @classmethod
    def from_env(cls) -> "GitHubPullRequestPublisher":
        return cls(
            token=os.environ.get("HORMUZ_GITHUB_TOKEN") or os.environ.get("GITHUB_TOKEN"),
            repository=os.environ.get("HORMUZ_GITHUB_REPOSITORY")
            or os.environ.get("GITHUB_REPOSITORY"),
            base_branch=os.environ.get("HORMUZ_GITHUB_BASE_BRANCH")
            or os.environ.get("GITHUB_BASE_BRANCH"),
        )

    def is_configured(self, repo_path: Path) -> bool:
        return bool(self._token and (self._repository or _infer_github_repository(repo_path)))

    async def create_pull_request(
        self,
        repo_path: Path,
        title: str,
        body: str,
        changed_files: Mapping[str, str],
    ) -> str:
        if not self._token:
            raise RuntimeError("GitHub token is not configured.")

        repository = self._repository or _infer_github_repository(repo_path)
        if repository is None:
            raise RuntimeError("GitHub repository is not configured.")

        try:
            from github import Github
        except ImportError as exc:
            raise RuntimeError("PyGithub is not installed.") from exc

        github = Github(self._token)
        repo = github.get_repo(repository)
        base_branch = self._base_branch or repo.default_branch
        branch_name = f"hormuz/autofix-{datetime.now(UTC).strftime('%Y%m%d%H%M%S%f')}"
        base = repo.get_branch(base_branch)
        repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=base.commit.sha)

        for relative_path, content in changed_files.items():
            existing = repo.get_contents(relative_path, ref=branch_name)
            if isinstance(existing, list):
                raise RuntimeError(f"Cannot update directory path {relative_path}.")
            repo.update_file(
                path=relative_path,
                message=f"Apply Compliance Codex fix for {relative_path}",
                content=content,
                sha=existing.sha,
                branch=branch_name,
            )

        pull_request = repo.create_pull(
            title=title,
            body=body,
            head=branch_name,
            base=base_branch,
        )
        return pull_request.html_url


def _infer_github_repository(repo_path: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            cwd=repo_path,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return None

    if result.returncode != 0:
        return None
    return _parse_github_repository(result.stdout.strip())


def _parse_github_repository(remote_url: str) -> str | None:
    patterns = (
        r"^https://github\.com/(?P<repo>[^/]+/[^/]+?)(?:\.git)?$",
        r"^git@github\.com:(?P<repo>[^/]+/[^/]+?)(?:\.git)?$",
    )
    for pattern in patterns:
        match = re.match(pattern, remote_url)
        if match:
            return match.group("repo")
    return None
