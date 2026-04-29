from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

from modules.scan.application.scanners.base import BackendScannerAgent, SourceMatch
from modules.scan.domain.entities import Severity

Predicate = Callable[[str, str, Path], bool]


@dataclass(frozen=True)
class Rule:
    id: str
    title: str
    category: str
    severity: Severity
    description: str
    recommendation: str
    predicate: Predicate
    violation_type: str | None = None


class PatternScanAgent(BackendScannerAgent):
    def __init__(self, name: str, category: str, rules: list[Rule]) -> None:
        super().__init__(name=name, category=category)
        self._rules = rules

    def find_matches(
        self, file_path: Path, text: str, _repo_path: Path
    ) -> Iterable[SourceMatch]:
        for line_number, line in enumerate(text.splitlines(), start=1):
            for rule in self._rules:
                if not rule.predicate(line, text, file_path):
                    continue
                yield SourceMatch(
                    rule_id=rule.id,
                    title=rule.title,
                    category=rule.category,
                    severity=rule.severity,
                    description=rule.description,
                    recommendation=rule.recommendation,
                    file_path=file_path,
                    line=line_number,
                    snippet=line.strip(),
                    violation_type=rule.violation_type,
                    remediation_hint=rule.recommendation,
                )
