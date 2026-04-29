import os
import re

from modules.scan.application.scanners.api_auditor import ApiAuditorAgent
from modules.scan.application.scanners.pattern import PatternScanAgent, Rule
from modules.scan.domain.entities import RegulationRef, Severity
from modules.scan.domain.ports import ScanAgent

ENABLED_AGENTS_ENV = ("SCAN_ENABLED_AGENTS", "SCAN_ENABLED_SCANNERS")
DISABLED_AGENTS_ENV = ("SCAN_DISABLED_AGENTS", "SCAN_DISABLED_SCANNERS")


def default_agents() -> list[ScanAgent]:
    agents: list[ScanAgent] = [
        PatternScanAgent("PII Scanner", "pii", _pii_rules()),
        ApiAuditorAgent(),
        PatternScanAgent("Auth Checker", "auth", _auth_rules()),
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


def _gdpr_32() -> RegulationRef:
    return RegulationRef(
        framework="GDPR",
        clause="Article 32",
        summary="Security of processing",
    )


def _app_11() -> RegulationRef:
    return RegulationRef(
        framework="APP",
        clause="APP 11",
        summary="Security of personal information",
    )


def _pii_rules() -> list[Rule]:
    return [
        Rule(
            id="pii-in-logs",
            title="PII and password written to logs",
            category="pii",
            severity=Severity.CRITICAL,
            description="The log statement includes email and password values.",
            recommendation="Log a correlation ID and outcome only. Never log credentials or direct identifiers.",
            regulations=(_gdpr_32(), _app_11()),
            predicate=lambda line, _text, _path: "logger." in line
            and "email" in line
            and "password" in line,
        ),
        Rule(
            id="third-party-pii-without-consent",
            title="PII sent to third party without consent boundary",
            category="pii",
            severity=Severity.HIGH,
            description="Personal data is posted to an analytics endpoint without an explicit consent gate.",
            recommendation="Gate the transfer behind consent and minimize the payload.",
            regulations=(
                RegulationRef(framework="GDPR", clause="Article 6", summary="Lawfulness of processing"),
                RegulationRef(framework="APP", clause="APP 6", summary="Use or disclosure"),
            ),
            predicate=lambda line, _text, _path: "analytics.example.com" in line,
        ),
    ]


def _auth_rules() -> list[Rule]:
    return [
        Rule(
            id="hardcoded-secret",
            title="Hardcoded secret",
            category="auth",
            severity=Severity.CRITICAL,
            description="A JWT secret is committed directly in source code.",
            recommendation="Read secrets from the runtime environment or a secret manager.",
            regulations=(_gdpr_32(), _app_11()),
            predicate=lambda line, _text, _path: "JWT_SECRET" in line and "secret" in line.lower(),
        ),
        Rule(
            id="sql-injection",
            title="SQL query built with string interpolation",
            category="auth",
            severity=Severity.CRITICAL,
            description="User input is interpolated into SQL.",
            recommendation="Use parameterized queries or an ORM query builder.",
            regulations=(_gdpr_32(), _app_11()),
            predicate=lambda line, _text, _path: "SELECT *" in line and ("{" in line or "%s" in line),
        ),
        Rule(
            id="missing-admin-auth",
            title="Admin endpoint missing auth boundary",
            category="auth",
            severity=Severity.CRITICAL,
            description="The admin route returns all users without an auth dependency.",
            recommendation="Require an admin permission dependency before returning user records.",
            regulations=(
                RegulationRef(
                    framework="GDPR",
                    clause="Article 25",
                    summary="Data protection by design and by default",
                ),
                _app_11(),
            ),
            predicate=lambda line, _text, _path: "/admin/all-users" in line,
        ),
        Rule(
            id="plaintext-password-storage",
            title="Plaintext password storage",
            category="auth",
            severity=Severity.CRITICAL,
            description="The model stores a password field without a hash boundary.",
            recommendation="Store only salted password hashes using a modern password hashing algorithm.",
            regulations=(_gdpr_32(), _app_11()),
            predicate=lambda line, _text, _path: "password = Column" in line,
        ),
    ]
