from functools import lru_cache

from modules.scan.adapters.outbound.git_repository import GitRepositoryPreparer
from modules.scan.adapters.outbound.github_pr import GitHubPullRequestPublisher
from modules.scan.application.fix_catalog import default_fix_agent
from modules.scan.application.fix_generator import FixGenerator
from modules.scan.application.orchestrator import ScanOrchestrator
from modules.scan.application.rule_catalog import default_agents


@lru_cache
def get_scan_orchestrator() -> ScanOrchestrator:
    from infrastructure.config import get_backend_settings

    settings = get_backend_settings()
    return ScanOrchestrator(
        default_agents(),
        GitRepositoryPreparer(settings.scan_worktree_root),
        settings,
    )


@lru_cache
def get_fix_generator() -> FixGenerator:
    from infrastructure.config import get_backend_settings

    settings = get_backend_settings()
    repository_preparer = GitRepositoryPreparer(settings.scan_worktree_root)
    return FixGenerator(
        fix_agent=default_fix_agent(),
        scan_orchestrator=get_scan_orchestrator(),
        repository_preparer=repository_preparer,
        settings=settings,
        pr_publisher=GitHubPullRequestPublisher(
            token=settings.github_token,
            repository=settings.github_repository,
            base_branch=settings.github_base_branch,
        ),
    )
