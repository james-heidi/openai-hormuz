import os
import re

from modules.scan.application.scanners.api_auditor import ApiAuditorAgent
from modules.scan.application.scanners.auth_checker import AuthCheckerAgent
from modules.scan.application.scanners.pii_scanner import PiiScanAgent
from modules.scan.domain.ports import ScanAgent

ENABLED_AGENTS_ENV = ("SCAN_ENABLED_AGENTS", "SCAN_ENABLED_SCANNERS")
DISABLED_AGENTS_ENV = ("SCAN_DISABLED_AGENTS", "SCAN_DISABLED_SCANNERS")


def default_agents() -> list[ScanAgent]:
    agents: list[ScanAgent] = [
        PiiScanAgent(),
        ApiAuditorAgent(),
        AuthCheckerAgent(),
    ]
    enabled = _configured_agent_keys(ENABLED_AGENTS_ENV)
    disabled = _configured_agent_keys(DISABLED_AGENTS_ENV)

    return [
        agent
        for agent in agents
        if (not enabled or _matches_agent(agent, enabled)) and not _matches_agent(agent, disabled)
    ]


def _configured_agent_keys(names: tuple[str, ...]) -> set[str]:
    values = (os.environ.get(name, "") for name in names)
    return {
        _agent_key(token)
        for value in values
        for token in re.split(r"[,:\s]+", value)
        if token.strip()
    }


def _matches_agent(agent: ScanAgent, keys: set[str]) -> bool:
    return bool(keys & {_agent_key(agent.category), _agent_key(agent.name)})


def _agent_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())
