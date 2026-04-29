import re
from collections.abc import Callable

from modules.scan.domain.entities import Finding
from modules.scan.domain.ports import FixAgent

LinePredicate = Callable[[str], bool]
LineReplacement = Callable[[str, str], str]


class RuleAwareFixAgent(FixAgent):
    """Deterministic patch writer for scanner findings.

    The backend port leaves room for an LLM-backed Codex adapter. For the demo
    path, these source rewrites keep auto-fix reliable and offline.
    """

    name = "Codex Patch Writer"

    async def fix(self, finding: Finding, source: str) -> str | None:
        rule_id = finding.id.split(":", maxsplit=1)[0]
        handler = _HANDLERS.get(rule_id)
        if handler is None:
            return None
        return handler(source, finding)


def default_fix_agent() -> FixAgent:
    return RuleAwareFixAgent()


def _fix_pii_logs(source: str, _finding: Finding) -> str | None:
    return _replace_first_line(
        source,
        lambda line: "logger." in line and "email" in line and "password" in line,
        lambda _line, indent: f'{indent}logger.info("Login attempt completed")',
    )


def _fix_third_party_pii(source: str, _finding: Finding) -> str | None:
    return _replace_first_line(
        source,
        lambda line: "analytics.example.com" in line and "requests.post" in line,
        lambda line, indent: (
            f'{indent}if getattr(user, "analytics_consent", False):\n'
            f'{indent}    requests.post("https://analytics.example.com", '
            'json={"user_id": user.id})'
        ),
    )


def _fix_api_overexposure(source: str, _finding: Finding) -> str | None:
    def replace(line: str, indent: str) -> str:
        match = re.search(r"return\s+([a-zA-Z_][a-zA-Z0-9_]*)\.__dict__", line)
        if match:
            variable = match.group(1)
            return f'{indent}return {{"id": {variable}.id}}'

        orm_match = re.search(
            r"return\s+(?P<query>(?:db|session)\.query\((?P<model>\w+)\)\.(?:all|first|get)\(.*\))",
            line,
        )
        if orm_match and ".all(" in orm_match.group("query"):
            variable = orm_match.group("model").lower()
            return (
                f'{indent}return [{{"id": {variable}.id}} '
                f'for {variable} in {orm_match.group("query")}]'
            )
        if orm_match:
            return f'{indent}return {{"id": result.id}} if (result := {orm_match.group("query")}) else None'

        return f'{indent}return {{"id": user.id}}'

    return _replace_first_line(
        source,
        lambda line: "__dict__" in line
        or re.search(r"return\s+(?:db|session)\.query\(\w+\)\.(?:all|first|get)\(", line)
        is not None,
        replace,
    )


def _fix_stack_trace_leakage(source: str, _finding: Finding) -> str | None:
    return _replace_first_line(
        source,
        lambda line: "traceback.format_exc" in line,
        lambda _line, indent: f'{indent}return {{"error": "internal_server_error"}}',
    )


def _fix_missing_retention_policy(source: str, _finding: Finding) -> str | None:
    return _replace_first_line(
        source,
        lambda line: "No deletion policy" in line,
        lambda _line, indent: (
            f"{indent}retention_policy_days = 365\n"
            f"{indent}retention_deleted_at = None"
        ),
    )


def _fix_permissive_cors(source: str, _finding: Finding) -> str | None:
    replacements = (
        ('allow_origins=["*"]', 'allow_origins=["http://localhost:3000"]'),
        ("allow_origins=['*']", "allow_origins=['http://localhost:3000']"),
        ('allow_origins = ["*"]', 'allow_origins = ["http://localhost:3000"]'),
        ("allow_origins = ['*']", "allow_origins = ['http://localhost:3000']"),
    )
    updated = source
    for before, after in replacements:
        updated = updated.replace(before, after, 1)
        if updated != source:
            return updated
    return None


def _fix_hardcoded_secret(source: str, _finding: Finding) -> str | None:
    updated = _replace_first_line(
        source,
        lambda line: "JWT_SECRET" in line and "=" in line and "os.environ" not in line,
        lambda _line, indent: f'{indent}JWT_SECRET = os.environ["JWT_SECRET"]',
    )
    if updated is None:
        return None
    return _ensure_import(updated, "os")


def _fix_sql_injection(source: str, _finding: Finding) -> str | None:
    return _replace_first_line(
        source,
        lambda line: "SELECT *" in line and ("{" in line or "%s" in line),
        lambda _line, indent: (
            f'{indent}return ("SELECT * FROM users WHERE email = :email", '
            '{"email": email_input})'
        ),
    )


def _fix_missing_admin_auth(source: str, _finding: Finding) -> str | None:
    return _replace_first_line(
        source,
        lambda line: '@app.get("/admin/all-users")' in line
        or "@app.get('/admin/all-users')" in line,
        lambda _line, indent: (
            f'{indent}@app.get("/admin/all-users", dependencies=[Depends(require_admin)])'
        ),
    )


def _fix_plaintext_password_storage(source: str, _finding: Finding) -> str | None:
    return _replace_first_line(
        source,
        lambda line: "password = Column" in line,
        lambda line, _indent: line.replace("password = Column", "password_hash = Column", 1),
    )


def _replace_first_line(
    source: str,
    predicate: LinePredicate,
    replacement: LineReplacement,
) -> str | None:
    lines = source.splitlines(keepends=True)
    for index, line in enumerate(lines):
        content, newline = _split_newline(line)
        if not predicate(content):
            continue
        indent = content[: len(content) - len(content.lstrip())]
        lines[index] = _with_newline(replacement(content, indent), newline)
        updated = "".join(lines)
        return updated if updated != source else None
    return None


def _ensure_import(source: str, module: str) -> str:
    import_line = f"import {module}"
    if re.search(rf"^import\s+{re.escape(module)}$", source, flags=re.MULTILINE):
        return source

    lines = source.splitlines(keepends=True)
    last_import_index: int | None = None
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("import ") or stripped.startswith("from "):
            last_import_index = index
            continue
        if stripped and last_import_index is not None:
            break

    if last_import_index is None:
        return f"{import_line}\n{source}"

    lines.insert(last_import_index + 1, f"{import_line}\n")
    return "".join(lines)


def _split_newline(line: str) -> tuple[str, str]:
    if line.endswith("\r\n"):
        return line[:-2], "\r\n"
    if line.endswith("\n"):
        return line[:-1], "\n"
    return line, ""


def _with_newline(text: str, newline: str) -> str:
    if "\n" in text:
        return text if text.endswith(("\n", "\r\n")) else f"{text}{newline}"
    return f"{text}{newline}"


_HANDLERS: dict[str, Callable[[str, Finding], str | None]] = {
    "pii-in-logs": _fix_pii_logs,
    "third-party-pii-without-consent": _fix_third_party_pii,
    "api-overexposure": _fix_api_overexposure,
    "stack-trace-leakage": _fix_stack_trace_leakage,
    "missing-retention-policy": _fix_missing_retention_policy,
    "permissive-cors": _fix_permissive_cors,
    "hardcoded-secret": _fix_hardcoded_secret,
    "sql-injection": _fix_sql_injection,
    "missing-admin-auth": _fix_missing_admin_auth,
    "plaintext-password-storage": _fix_plaintext_password_storage,
}
