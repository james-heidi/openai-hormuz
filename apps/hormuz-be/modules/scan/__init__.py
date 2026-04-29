from functools import lru_cache

from modules.scan.application.orchestrator import ScanOrchestrator
from modules.scan.application.rule_catalog import default_agents


@lru_cache
def get_scan_orchestrator() -> ScanOrchestrator:
    return ScanOrchestrator(default_agents())

