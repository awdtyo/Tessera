"""Typed loader for samples/manifest.json.

Split discipline: use dev_entries() for development and threshold tuning.
heldout_entries() is for final benchmark reporting ONLY (benchmarks/).
Never tune on heldout — tests enforce that dev helpers exclude it.
"""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Category = Literal[
    "real",
    "splice",
    "copy-move",
    "gan",
    "diffusion",
    "whatsapp-recompressed",
    "video-real",
    "video-spliced",
]
CATEGORIES: tuple[str, ...] = (
    "real",
    "splice",
    "copy-move",
    "gan",
    "diffusion",
    "whatsapp-recompressed",
    "video-real",
    "video-spliced",
)

Split = Literal["dev", "heldout"]
MANIFEST_VERSION = 1


class SampleEntry(BaseModel):
    """One row of the sample manifest."""

    model_config = ConfigDict(frozen=True)

    file: str
    category: Category
    source: str
    license: str
    ground_truth: dict[str, object] = Field(default_factory=dict)
    split: Split
    width: int | None = None
    height: int | None = None
    sha256: str | None = None
    notes: str = ""


class _ManifestFile(BaseModel):
    model_config = ConfigDict(frozen=True)

    version: int
    entries: list[SampleEntry]


def default_manifest_path() -> Path:
    """Repo-root samples/manifest.json, resolved from this file's location."""
    return Path(__file__).resolve().parents[3] / "samples" / "manifest.json"


def load_manifest(path: Path | str | None = None) -> list[SampleEntry]:
    """Load and validate the manifest. Raises on bad version or bad rows."""
    manifest_path = Path(path) if path is not None else default_manifest_path()
    parsed = _ManifestFile.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    if parsed.version != MANIFEST_VERSION:
        raise ValueError(f"Unsupported manifest version {parsed.version}")
    return list(parsed.entries)


def dev_entries(entries: list[SampleEntry]) -> list[SampleEntry]:
    """Entries safe for development and tuning."""
    return [e for e in entries if e.split == "dev"]


def heldout_entries(entries: list[SampleEntry]) -> list[SampleEntry]:
    """Held-out entries: final reporting only, never for tuning."""
    return [e for e in entries if e.split == "heldout"]


def by_category(entries: list[SampleEntry], category: Category) -> list[SampleEntry]:
    """Filter entries by category."""
    return [e for e in entries if e.category == category]


def resolve(entry: SampleEntry, root: Path | str | None = None) -> Path:
    """Absolute file path for an entry (root defaults to samples/)."""
    base = Path(root) if root is not None else default_manifest_path().parent
    return base / entry.file


def missing_files(entries: list[SampleEntry], root: Path | str | None = None) -> list[str]:
    """Relative paths of entries whose files are absent. Empty means complete."""
    return [e.file for e in entries if not resolve(e, root).is_file()]
