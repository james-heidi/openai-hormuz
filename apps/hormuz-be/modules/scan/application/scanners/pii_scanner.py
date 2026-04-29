import re
from pathlib import Path

from modules.scan.application.scanners.pattern import PatternScanAgent, Rule
from modules.scan.domain.entities import RegulationRef, Severity

PII_IN_LOGS = "PII_IN_LOGS"
THIRD_PARTY_PII_WITHOUT_CONSENT = "THIRD_PARTY_PII_WITHOUT_CONSENT"

LOG_CALL_RE = re.compile(
    r"\b(?:logger|logging|log|console)\."
    r"(?:debug|info|log|warn|warning|error|exception|critical)\s*\("
    r"|\bprint\s*\(",
    re.IGNORECASE,
)
PII_TOKEN_RE = re.compile(
    r"\b(?:email|e-mail|password|passwd|pwd|phone|mobile|address|dob|date_of_birth|"
    r"birthdate|ssn|tax_file_number|tfn|passport|medicare|credit_card|card_number|"
    r"first_name|last_name|full_name|ip_address|token|credential|secret)\b",
    re.IGNORECASE,
)


class PiiScanAgent(PatternScanAgent):
    prompt_name = "pii_scanner.md"

    def __init__(self) -> None:
        super().__init__("PII Scanner", "pii", _pii_rules())


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
            predicate=_is_pii_log_line,
            violation_type=PII_IN_LOGS,
        ),
        Rule(
            id="third-party-pii-without-consent",
            title="PII sent to third party without consent boundary",
            category="pii",
            severity=Severity.HIGH,
            description="Personal data is posted to an analytics endpoint without an explicit consent gate.",
            recommendation="Gate the transfer behind consent and minimize the payload.",
            regulations=(
                RegulationRef(
                    framework="GDPR", clause="Article 6", summary="Lawfulness of processing"
                ),
                RegulationRef(framework="APP", clause="APP 6", summary="Use or disclosure"),
            ),
            predicate=lambda line, _text, _path: "analytics.example.com" in line,
            violation_type=THIRD_PARTY_PII_WITHOUT_CONSENT,
        ),
    ]


def _is_pii_log_line(line: str, _text: str, _path: Path) -> bool:
    stripped = line.strip()
    if stripped.startswith(("#", "//")):
        return False
    return bool(LOG_CALL_RE.search(line) and PII_TOKEN_RE.search(line))


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
