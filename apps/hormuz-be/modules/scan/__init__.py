from functools import lru_cache

from modules.scan.adapters.outbound.git_repository import GitRepositoryPreparer
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
