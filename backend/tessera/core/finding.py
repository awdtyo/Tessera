"""Finding and status models. Evidence, not verdicts: confidence is a range."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Status(StrEnum):
    """Three-state label. Absence of evidence is not contradiction."""

    CONFIRMED = "confirmed"
    SUSPICIOUS = "suspicious"
    CANNOT_DETERMINE = "cannot_determine"


class Reliability(StrEnum):
    """How much to trust this signal."""

    OK = "ok"
    DEGRADED = "degraded"
    UNRELIABLE = "unreliable"
    ERROR = "error"


class Applicability(BaseModel):
    """Whether a module applies to a given media + claim."""

    model_config = ConfigDict(frozen=True)

    applicable: bool
    reason: str


class Finding(BaseModel):
    """One module's result. Confidence is always a range, never one number."""

    model_config = ConfigDict(frozen=True)

    module_id: str
    status: Status
    confidence_low: float = Field(ge=0.0, le=1.0)
    confidence_high: float = Field(ge=0.0, le=1.0)
    summary: str
    reasoning: str
    reliability: Reliability
    reliability_note: str
    artifacts: dict[str, str] = Field(default_factory=dict)
    runtime_ms: int = Field(ge=0)

    @field_validator("summary", "reasoning", "reliability_note")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must be a non-empty string")
        return v

    @model_validator(mode="after")
    def _check_range(self) -> "Finding":
        if self.confidence_low > self.confidence_high:
            raise ValueError("confidence_low must be <= confidence_high")
        return self
