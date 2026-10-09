"""Optional user claim (e.g. "this is from today's flood").

Signal: none (input carrier). Failure modes: empty claim — claim checks
must return cannot_determine, never contradiction. Reliability: n/a.
"""

from pydantic import BaseModel, ConfigDict


class Claim(BaseModel):
    """Structured claim with optional free text. All fields optional."""

    model_config = ConfigDict(frozen=True)

    text: str | None = None
    place: str | None = None
    time: str | None = None
    event_type: str | None = None
