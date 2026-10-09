"""Media descriptor passed to every module.

Signal: none (input carrier). Failure modes: wrong media_type label,
missing file path. Reliability: n/a — modules decide applicability.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict

MediaType = Literal["image", "video"]


class Media(BaseModel):
    """Minimal local-media reference. Media never leaves the device."""

    model_config = ConfigDict(frozen=True)

    path: str
    media_type: MediaType
    sha256: str | None = None
    width: int | None = None
    height: int | None = None
    duration_s: float | None = None
