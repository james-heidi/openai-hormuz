from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from modules.scan.domain.entities import AgentStatus, AgentUpdate, Finding, RegulationRef, Severity
from modules.scan.domain.ports import EventEmitter, ScanAgent

SOURCE_SUFFIXES = {".py", ".js", ".jsx", ".ts", ".tsx"}
SKIP_DIRS = {".git", ".venv", "__pycache__", "node_modules", "dist", "build"}


Predicate = Callable[[str, str, Path], bool]


@dataclass(frozen=True)
class Rule:
    id: str
    title: str
    category: str
    severity: Severity
    description: str
    recommendation: str
    regulations: tuple[RegulationRef, ...]
    predicate: Predicate


class PatternScanAgent(ScanAgent):
    def __init__(self, name: str, category: str, rules: list[Rule]) -> None:
        self.name = name
        self.category = category
        self._rules = rules

    async def scan(self, repo_path: Path, emit: EventEmitter) -> list[Finding]:
        files = list(_iter_source_files(repo_path))
        findings: list[Finding] = []
        seen: set[tuple[str, str, int]] = set()

        await _emit_update(emit, self.name, AgentStatus.RUNNING, "Scanning source files", 5)

        total = max(len(files), 1)
        for index, file_path in enumerate(files, start=1):
            text = file_path.read_text(errors="ignore")
            for line_number, line in enumerate(text.splitlines(), start=1):
                for rule in self._rules:
                    if not rule.predicate(line, text, file_path):
                        continue
                    key = (rule.id, str(file_path), line_number)
                    if key in seen:
                        continue
                    seen.add(key)
                    relative_path = file_path.relative_to(repo_path)
                    findings.append(
                        Finding(
                            id=f"{rule.id}:{relative_path}:{line_number}",
                            agent=self.name,
                            category=rule.category,
                            severity=rule.severity,
                            file_path=str(relative_path),
                            line=line_number,
                            title=rule.title,
                            description=rule.description,
                            snippet=line.strip(),
                            regulations=list(rule.regulations),
                            recommendation=rule.recommendation,
                        )
                    )

            progress = 5 + round(index / total * 90)
            await _emit_update(emit, self.name, AgentStatus.RUNNING, file_path.name, progress)

        await _emit_update(emit, self.name, AgentStatus.DONE, "Scan complete", 100)
        return findings


def default_agents() -> list[ScanAgent]:
    return [
        PatternScanAgent("PII Scanner", "pii", _pii_rules()),
        PatternScanAgent("API Auditor", "api", _api_rules()),
        PatternScanAgent("Auth Checker", "auth", _auth_rules()),
    ]


def _iter_source_files(repo_path: Path):
    for file_path in sorted(repo_path.rglob("*")):
        if any(part in SKIP_DIRS for part in file_path.parts):
            continue
        if file_path.is_file() and file_path.suffix in SOURCE_SUFFIXES:
            yield file_path


async def _emit_update(
    emit: EventEmitter, agent: str, status: AgentStatus, message: str, progress: int
) -> None:
    update = AgentUpdate(agent=agent, status=status, message=message, progress=progress)
    await emit({"type": "agent_update", "update": update.model_dump(mode="json")})


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


def _api_rules() -> list[Rule]:
    return [
        Rule(
            id="api-overexposure",
            title="API response over-exposes user fields",
            category="api",
            severity=Severity.HIGH,
            description="Returning raw object dictionaries can expose secrets and unnecessary PII.",
            recommendation="Return an explicit response DTO with only required fields.",
            regulations=(
                RegulationRef(
                    framework="GDPR",
                    clause="Article 5(1)(c)",
                    summary="Data minimisation",
                ),
                RegulationRef(framework="APP", clause="APP 3 and APP 6", summary="Collection and use"),
            ),
            predicate=lambda line, _text, _path: ".__dict__" in line or "__dict__" in line,
        ),
        Rule(
            id="stack-trace-leakage",
            title="Stack trace leaked to client",
            category="api",
            severity=Severity.HIGH,
            description="Exception details and tracebacks are returned to callers.",
            recommendation="Return a stable error code and log the traceback server-side.",
            regulations=(_gdpr_32(), _app_11()),
            predicate=lambda line, _text, _path: "traceback.format_exc" in line,
        ),
        Rule(
            id="missing-retention-policy",
            title="Missing data retention policy",
            category="api",
            severity=Severity.MEDIUM,
            description="The model has no retention timestamp or deletion policy marker.",
            recommendation="Add retention metadata and a deletion workflow.",
            regulations=(
                RegulationRef(
                    framework="GDPR",
                    clause="Article 5(1)(e)",
                    summary="Storage limitation",
                ),
                _app_11(),
            ),
            predicate=lambda line, _text, _path: "No deletion policy" in line,
        ),
        Rule(
            id="permissive-cors",
            title="Permissive CORS policy",
            category="api",
            severity=Severity.MEDIUM,
            description="CORS allows all origins.",
            recommendation="Restrict CORS to known frontend origins.",
            regulations=(_gdpr_32(), _app_11()),
            predicate=lambda line, _text, _path: "allow_origins" in line and '"*"' in line,
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
