from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class Severity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AgentStatus(StrEnum):
    IDLE = "idle"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"


class ScanStatus(StrEnum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    FAILED = "failed"


class FixOutputType(StrEnum):
    LOCAL_DIFF = "local_diff"
    GITHUB_PR = "github_pr"


class RegulationRef(BaseModel):
    framework: Literal["GDPR", "APP"]
    clause: str
    title: str
    summary: str
    requirement: str
    max_penalty: str
    severity: Severity


class Finding(BaseModel):
    id: str
    violation_type: str
    agent: str
    category: str
    severity: Severity
    file_path: str
    line: int | None = None
    context: str | None = None
    title: str
    description: str
    snippet: str | None = None
    regulations: list[RegulationRef] = Field(default_factory=list)
    regulation_warning: str | None = None
    recommendation: str
    remediation_hint: str


class ScanRequest(BaseModel):
    repo_path: str = Field(min_length=1)


class AgentUpdate(BaseModel):
    agent: str
    status: AgentStatus
    message: str
    progress: int = Field(ge=0, le=100)


class AgentFailure(BaseModel):
    agent: str
    message: str


class ScanSummary(BaseModel):
    scan_status: ScanStatus
    score: int = Field(ge=0, le=100)
    total_findings: int
    counts_by_severity: dict[Severity, int]
    counts_by_agent: dict[str, int]
    findings: list[Finding]
    failed_agents: list[AgentFailure]


class FixRequest(BaseModel):
    repo_path: str = Field(min_length=1)
    findings: list[Finding] = Field(default_factory=list)
    finding: Finding | None = None
    apply: bool = False
    create_pr: bool = False
    rescan: bool = False
    patch_dir: str | None = None

    @model_validator(mode="after")
    def normalize_selected_finding(self) -> "FixRequest":
        if self.finding is not None and not self.findings:
            self.findings = [self.finding]
        if not self.findings:
            raise ValueError("At least one finding is required.")
        return self


class FixPatch(BaseModel):
    finding_id: str
    file_path: str
    diff: str
    patch_path: str | None = None
    applied: bool = False


class FixFailure(BaseModel):
    finding_id: str | None = None
    file_path: str | None = None
    code: str
    message: str


class FixSummary(BaseModel):
    output_type: FixOutputType
    pr_url: str | None = None
    patch_path: str | None = None
    diff: str
    patches: list[FixPatch]
    failures: list[FixFailure] = Field(default_factory=list)
    applied: bool = False
    rescan_summary: ScanSummary | None = None


class ErrorDetail(BaseModel):
    code: str
    message: str
