import re
from collections.abc import Iterable
from pathlib import Path

from modules.scan.application.scanners.base import BackendScannerAgent, SourceMatch
from modules.scan.domain.entities import Severity

HARDCODED_SECRET = "HARDCODED_SECRET"
SQL_INJECTION = "SQL_INJECTION"
MISSING_AUTH = "MISSING_AUTH"
PLAINTEXT_PASSWORD_STORAGE = "PLAINTEXT_PASSWORD_STORAGE"

AUTH_BOUNDARY_TOKENS = (
    "Depends(",
    "Security(",
    "current_user",
    "require_auth",
    "require_admin",
    "authenticate",
    "authorize",
    "permission",
    "token",
    "jwt",
    "passport.",
    "isAuthenticated",
)

_PYTHON_ENDPOINT_RE = re.compile(
    r"^\s*@[\w.]+\.(?P<method>get|post|put|patch|delete)\("
    r"\s*(?P<quote>[\"'])(?P<path>.*?)(?P=quote)",
    re.IGNORECASE,
)
_JS_ENDPOINT_RE = re.compile(
    r"(?:app|router)\.(?P<method>get|post|put|patch|delete)\("
    r"\s*(?P<quote>[\"'])(?P<path>.*?)(?P=quote)",
    re.IGNORECASE,
)
_FUNCTION_RE = re.compile(r"^\s*(?:async\s+)?def\s+(?P<name>\w+)\(")


class AuthCheckerAgent(BackendScannerAgent):
    prompt_name = "auth_checker.md"

    def __init__(self) -> None:
        super().__init__(name="Auth Checker", category="auth")

    def find_matches(
        self, file_path: Path, text: str, _repo_path: Path
    ) -> Iterable[SourceMatch]:
        lines = text.splitlines()
        for index, line in enumerate(lines):
            line_number = index + 1
            if (
                "JWT_SECRET" in line
                and "secret" in line.lower()
                and "os.environ" not in line
                and "getenv" not in line
            ):
                yield SourceMatch(
                    rule_id="hardcoded-secret",
                    title="Hardcoded secret",
                    category=self.category,
                    severity=Severity.CRITICAL,
                    description="A JWT secret is committed directly in source code.",
                    recommendation="Read secrets from the runtime environment or a secret manager.",
                    file_path=file_path,
                    line=line_number,
                    snippet=line.strip(),
                    violation_type=HARDCODED_SECRET,
                    context=_nearest_function_context(lines, index),
                )
                continue

            if "SELECT *" in line and ("{" in line or "%s" in line):
                yield SourceMatch(
                    rule_id="sql-injection",
                    title="SQL query built with string interpolation",
                    category=self.category,
                    severity=Severity.CRITICAL,
                    description="User input is interpolated into SQL.",
                    recommendation="Use parameterized queries or an ORM query builder.",
                    file_path=file_path,
                    line=line_number,
                    snippet=line.strip(),
                    violation_type=SQL_INJECTION,
                    context=_nearest_function_context(lines, index),
                )
                continue

            route = _endpoint_match(line)
            if route and _is_sensitive_admin_route(route[1]) and not _has_auth_boundary(lines, index):
                yield SourceMatch(
                    rule_id="missing-admin-auth",
                    title="Admin endpoint missing auth boundary",
                    category=self.category,
                    severity=Severity.CRITICAL,
                    description="The admin route returns all users without an auth dependency.",
                    recommendation="Require an admin permission dependency before returning user records.",
                    file_path=file_path,
                    line=line_number,
                    snippet=line.strip(),
                    violation_type=MISSING_AUTH,
                    context=_route_context(lines, index, route),
                )
                continue

            if "password = Column" in line:
                yield SourceMatch(
                    rule_id="plaintext-password-storage",
                    title="Plaintext password storage",
                    category=self.category,
                    severity=Severity.CRITICAL,
                    description="The model stores a password field without a hash boundary.",
                    recommendation=(
                        "Store only salted password hashes using a modern password hashing algorithm."
                    ),
                    file_path=file_path,
                    line=line_number,
                    snippet=line.strip(),
                    violation_type=PLAINTEXT_PASSWORD_STORAGE,
                    context=_nearest_function_context(lines, index),
                )


def _endpoint_match(line: str) -> tuple[str, str] | None:
    match = _PYTHON_ENDPOINT_RE.search(line) or _JS_ENDPOINT_RE.search(line)
    if not match:
        return None
    return match.group("method").upper(), match.group("path")


def _route_context(lines: list[str], index: int, route: tuple[str, str]) -> str:
    method, route_path = route
    function_name = _next_python_function(lines, index)
    route_label = f"{method} {route_path}"
    if function_name:
        return f"{route_label} -> {function_name}"
    return route_label


def _next_python_function(lines: list[str], index: int) -> str | None:
    for line in lines[index + 1 : index + 9]:
        match = _FUNCTION_RE.match(line)
        if match:
            return match.group("name")
    return None


def _nearest_function_context(lines: list[str], index: int) -> str | None:
    for cursor in range(index, -1, -1):
        match = _FUNCTION_RE.match(lines[cursor])
        if match:
            return match.group("name")
    return None


def _is_sensitive_admin_route(route_path: str) -> bool:
    normalized = route_path.lower()
    return "/admin" in normalized or "all-users" in normalized


def _has_auth_boundary(lines: list[str], index: int) -> bool:
    nearby = "\n".join(lines[max(index - 3, 0) : index + 9])
    nearby_lower = nearby.lower()
    return any(token.lower() in nearby_lower for token in AUTH_BOUNDARY_TOKENS)
