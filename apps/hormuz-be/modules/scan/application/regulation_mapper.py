from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from modules.scan.domain.entities import Finding, RegulationRef, Severity

DATA_DIR = Path(__file__).with_name("regulations")
MAPPING_FILES = ("gdpr.json", "au_privacy_act_app.json")


class RegulationMapping(BaseModel):
    clause: str
    title: str
    summary: str
    requirement: str
    max_penalty: str
    severity: Severity


class RegulationMappingFile(BaseModel):
    framework: Literal["GDPR", "APP"]
    mappings: dict[str, RegulationMapping]


@lru_cache
def _mapping_catalog() -> dict[str, list[RegulationRef]]:
    catalog: dict[str, list[RegulationRef]] = {}
    for file_name in MAPPING_FILES:
        mapping_file = RegulationMappingFile.model_validate_json(
            (DATA_DIR / file_name).read_text()
        )
        for raw_violation_type, mapping in mapping_file.mappings.items():
            violation_type = _normalize_violation_type(raw_violation_type)
            catalog.setdefault(violation_type, []).append(
                RegulationRef(
                    framework=mapping_file.framework,
                    clause=mapping.clause,
                    title=mapping.title,
                    summary=mapping.summary,
                    requirement=mapping.requirement,
                    max_penalty=mapping.max_penalty,
                    severity=mapping.severity,
                )
            )
    return catalog


def attach_regulation_metadata(finding: Finding) -> Finding:
    violation_type = _normalize_violation_type(finding.violation_type)
    regulations = _mapping_catalog().get(violation_type)
    if not regulations:
        return finding.model_copy(
            update={
                "violation_type": violation_type,
                "regulations": [],
                "regulation_warning": (
                    f"No regulation mapping found for violation type {violation_type}."
                ),
            }
        )

    return finding.model_copy(
        update={
            "violation_type": violation_type,
            "regulations": regulations,
            "regulation_warning": None,
        }
    )


def _normalize_violation_type(violation_type: str) -> str:
    return violation_type.strip().upper().replace("-", "_")
