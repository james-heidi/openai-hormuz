import re
from collections.abc import Iterable
from pathlib import Path

from modules.scan.application.scanners.base import BackendScannerAgent, SourceMatch
from modules.scan.domain.entities import RegulationRef, Severity

API_OVEREXPOSURE = "API_OVEREXPOSURE"

_ENDPOINT_RE = re.compile(
    r"^\s*@[\w.]+\.(?P<method>get|post|put|patch|delete)\("
    r"\s*(?P<quote>[\"'])(?P<path>.*?)(?P=quote)",
    re.IGNORECASE,
)
_FUNCTION_RE = re.compile(r"^\s*(?:async\s+)?def\s+(?P<name>\w+)\(")
_CLASS_RE = re.compile(r"^\s*class\s+(?P<name>\w+)\b")
_RAW_RETURN_RE = re.compile(
    r"\breturn\b.*(?:__dict__|\.dict\(\)|\.model_dump\(\)|jsonable_encoder\()"
)
_ORM_RETURN_RE = re.compile(
    r"\breturn\s+(?:db|session)\.query\((?P<model>\w+)\)\."
    r"(?P<operation>all|first|get)\("
)
_ASSIGNMENT_MODEL_RE = re.compile(
    r"\b(?P<variable>\w+)\s*=\s*(?:db|session)\.query\((?P<model>\w+)\)"
)
_RETURN_DICT_RE = re.compile(r"\breturn\s+(?P<variable>\w+)\.__dict__")


class ApiAuditorAgent(BackendScannerAgent):
    prompt_name = "api_overexposure.md"

    def __init__(self) -> None:
        super().__init__(name="API Auditor", category="api")

    def find_matches(
        self, file_path: Path, text: str, _repo_path: Path
    ) -> Iterable[SourceMatch]:
        lines = text.splitlines()
        for index, line in enumerate(lines):
            line_number = index + 1
            if _RAW_RETURN_RE.search(line) or _ORM_RETURN_RE.search(line):
                context = _endpoint_or_model_context(lines, index)
                model = _infer_model(lines, index)
                description = _api_overexposure_description(context, model)
                yield SourceMatch(
                    rule_id="api-overexposure",
                    title="API response over-exposes personal data",
                    category=self.category,
                    severity=Severity.HIGH,
                    description=description,
                    recommendation="Return an explicit response DTO with only the fields required by the caller.",
                    regulations=(_gdpr_data_minimisation(), _app_collection_and_use()),
                    file_path=file_path,
                    line=line_number,
                    snippet=line.strip(),
                    violation_type=API_OVEREXPOSURE,
                    context=_combine_context(context, model),
                    remediation_hint=(
                        "Map ORM/domain objects into a response schema that excludes credentials, tokens, "
                        "internal IDs, and unrelated profile fields."
                    ),
                )
                continue

            if "traceback.format_exc" in line:
                yield SourceMatch(
                    rule_id="stack-trace-leakage",
                    title="Stack trace leaked to client",
                    category=self.category,
                    severity=Severity.HIGH,
                    description="Exception details and tracebacks are returned to callers.",
                    recommendation="Return a stable error code and log the traceback server-side.",
                    regulations=(_gdpr_32(), _app_11()),
                    file_path=file_path,
                    line=line_number,
                    snippet=line.strip(),
                    violation_type="ERROR_DISCLOSURE",
                    context=_endpoint_or_model_context(lines, index),
                )
                continue

            if "No deletion policy" in line:
                yield SourceMatch(
                    rule_id="missing-retention-policy",
                    title="Missing data retention policy",
                    category=self.category,
                    severity=Severity.MEDIUM,
                    description="The model has no retention timestamp or deletion policy marker.",
                    recommendation="Add retention metadata and a deletion workflow.",
                    regulations=(_gdpr_storage_limitation(), _app_11()),
                    file_path=file_path,
                    line=line_number,
                    snippet=line.strip(),
                    violation_type="MISSING_RETENTION_POLICY",
                    context=_endpoint_or_model_context(lines, index),
                )
                continue

            if "allow_origins" in line and '"*"' in line:
                yield SourceMatch(
                    rule_id="permissive-cors",
                    title="Permissive CORS policy",
                    category=self.category,
                    severity=Severity.MEDIUM,
                    description="CORS allows all origins.",
                    recommendation="Restrict CORS to known frontend origins.",
                    regulations=(_gdpr_32(), _app_11()),
                    file_path=file_path,
                    line=line_number,
                    snippet=line.strip(),
                    violation_type="PERMISSIVE_CORS",
                    context=_endpoint_or_model_context(lines, index),
                )


def _endpoint_or_model_context(lines: list[str], index: int) -> str | None:
    endpoint = _nearest_endpoint_context(lines, index)
    if endpoint:
        return endpoint
    return _nearest_model_context(lines, index)


def _nearest_endpoint_context(lines: list[str], index: int) -> str | None:
    function_name: str | None = None
    for cursor in range(index, -1, -1):
        function_match = _FUNCTION_RE.match(lines[cursor])
        if function_match and function_name is None:
            function_name = function_match.group("name")
            continue
        endpoint_match = _ENDPOINT_RE.match(lines[cursor])
        if endpoint_match:
            method = endpoint_match.group("method").upper()
            path = endpoint_match.group("path")
            if function_name:
                return f"{method} {path} -> {function_name}"
            return f"{method} {path}"
    return None


def _nearest_model_context(lines: list[str], index: int) -> str | None:
    for cursor in range(index, -1, -1):
        class_match = _CLASS_RE.match(lines[cursor])
        if class_match:
            return f"model {class_match.group('name')}"
    return None


def _infer_model(lines: list[str], index: int) -> str | None:
    orm_return = _ORM_RETURN_RE.search(lines[index])
    if orm_return:
        return orm_return.group("model")

    returned_dict = _RETURN_DICT_RE.search(lines[index])
    if not returned_dict:
        return None

    variable = returned_dict.group("variable")
    for cursor in range(index - 1, -1, -1):
        if _FUNCTION_RE.match(lines[cursor]):
            return None
        assignment = _ASSIGNMENT_MODEL_RE.search(lines[cursor])
        if assignment and assignment.group("variable") == variable:
            return assignment.group("model")
    return None


def _api_overexposure_description(context: str | None, model: str | None) -> str:
    subject = context or "API response"
    object_label = f"raw {model} objects or dictionaries" if model else "raw objects or dictionaries"
    return f"{subject} returns {object_label} that can expose unnecessary personal data."


def _combine_context(context: str | None, model: str | None) -> str | None:
    if context and model:
        return f"{context}; model {model}"
    return context or (f"model {model}" if model else None)


def _gdpr_data_minimisation() -> RegulationRef:
    return RegulationRef(
        framework="GDPR",
        clause="Article 5(1)(c)",
        summary="Data minimisation",
    )


def _gdpr_storage_limitation() -> RegulationRef:
    return RegulationRef(
        framework="GDPR",
        clause="Article 5(1)(e)",
        summary="Storage limitation",
    )


def _gdpr_32() -> RegulationRef:
    return RegulationRef(
        framework="GDPR",
        clause="Article 32",
        summary="Security of processing",
    )


def _app_collection_and_use() -> RegulationRef:
    return RegulationRef(
        framework="APP",
        clause="APP 3 and APP 6",
        summary="Collection and use",
    )


def _app_11() -> RegulationRef:
    return RegulationRef(
        framework="APP",
        clause="APP 11",
        summary="Security of personal information",
    )
