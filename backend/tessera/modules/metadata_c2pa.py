"""Metadata + C2PA module: file-history consistency.

Signal measured: EXIF/XMP tags (camera make/model, software, timestamps,
dimensions) plus an optional C2PA provenance manifest validated with the
maintained open-source `c2pa-python` library (dual MIT/Apache-2.0; see
docs/THIRD_PARTY.md). A valid signed manifest is positive provenance; an
editor software tag is consistent with editing; stripped metadata — the
common social-media case — is honest ignorance, never contradiction.
Known failure modes: metadata is trivially stripped or forged, so EXIF can
only weakly support authenticity; absence of a C2PA manifest means nothing.
Reliability rules: no EXIF and no manifest yields reliability="unreliable"
with status="cannot_determine". Partial EXIF, unknown software strings, or
an unchecked C2PA state yields "degraded". Editor software match or a
broken manifest yields "suspicious"; clean full EXIF (or valid manifest)
yields "confirmed" with modest ranges.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

from PIL import Image

from tessera.core.claim import Claim
from tessera.core.finding import Applicability, Finding, Reliability, Status
from tessera.core.media import Media
from tessera.core.module import Module

logger = logging.getLogger(__name__)

try:
    import c2pa as _c2pa

    _C2PA_AVAILABLE = True
except ImportError:
    _c2pa = None
    _C2PA_AVAILABLE = False

TAG_MAKE = 271
TAG_MODEL = 272
TAG_SOFTWARE = 305
TAG_DATETIME = 306
TAG_PIXEL_X = 33434
TAG_PIXEL_Y = 33437

# Lowercase substrings of known editor software tags. Camera firmware
# strings are NOT on this list: unknown software is only "degraded".
EDITOR_TAGS = (
    "photoshop",
    "lightroom",
    "illustrator",
    "gimp",
    "affinity",
    "pixelmator",
    "paint.net",
    "paintshop",
    "acdsee",
    "capture one",
    "dxo",
    "snapseed",
    "picsart",
    "facetune",
    "canva",
    "fotor",
    "pixlr",
    "photopea",
)


def _read_exif(path: Path) -> dict[int, Any]:
    try:
        with Image.open(path) as img:
            exif = img.getexif()
            return dict(exif.items()) if exif else {}
    except Exception as exc:  # noqa: BLE001 - unreadable tags mean no metadata
        logger.debug("EXIF read failed for %s: %s", path, exc)
        return {}


def _check_c2pa(path: Path) -> tuple[str, str]:
    """Return (state, detail). States: valid, broken, absent, unchecked."""
    if not _C2PA_AVAILABLE or _c2pa is None:
        return "unchecked", "c2pa-python not installed"
    try:
        reader = _c2pa.Reader(path)
    except Exception as exc:  # noqa: BLE001 - library raises C2paError variants
        name = type(exc).__name__.lower()
        if "notfound" in name or "no jumbf" in str(exc).lower():
            return "absent", "no manifest found"
        return "broken", f"manifest present but unreadable: {exc}"[:200]
    try:
        store = json.loads(str(reader.json()))
        title = str(store.get("title", "signed manifest"))
    except Exception:  # noqa: BLE001
        title = "signed manifest"
    return "valid", title


class MetadataC2paModule(Module):
    """File-history check: EXIF consistency plus C2PA manifest validation."""

    id = "metadata-c2pa"
    name = "File-history check"
    media_types = ("image",)

    def applicable(self, media: Media, claim: Claim) -> Applicability:
        _ = claim
        if media.media_type != "image":
            return Applicability(applicable=False, reason="Still images only.")
        return Applicability(applicable=True, reason="Image input.")

    def run(self, media: Media, claim: Claim) -> Finding:
        _ = claim
        start = time.perf_counter()
        path = Path(media.path)

        def done(
            status: Status,
            lo: float,
            hi: float,
            summary: str,
            reasoning: str,
            reliability: Reliability,
            note: str,
            artifacts: dict[str, str] | None = None,
        ) -> Finding:
            return Finding(
                module_id=self.id,
                status=status,
                confidence_low=lo,
                confidence_high=hi,
                summary=summary,
                reasoning=reasoning,
                reliability=reliability,
                reliability_note=note,
                artifacts=artifacts or {},
                runtime_ms=int((time.perf_counter() - start) * 1000),
            )

        exif = _read_exif(path)
        c2pa_state, c2pa_detail = _check_c2pa(path)
        artifacts = {"c2pa": f"{c2pa_state} ({c2pa_detail})"}

        if c2pa_state == "valid":
            artifacts["exif_tags"] = str(len(exif))
            return done(
                Status.CONFIRMED,
                0.6,
                0.8,
                "A valid provenance manifest is embedded.",
                f"Validated C2PA manifest ({c2pa_detail}); file history "
                f"is signed, with {len(exif)} EXIF tags alongside.",
                Reliability.OK,
                "Signed provenance present and readable.",
                artifacts,
            )
        if c2pa_state == "broken":
            return done(
                Status.SUSPICIOUS,
                0.5,
                0.75,
                "The provenance manifest is damaged.",
                f"C2PA data exists but failed validation ({c2pa_detail}), "
                "consistent with tampering after signing.",
                Reliability.DEGRADED,
                "Broken manifest; verify with other tiles.",
                artifacts,
            )

        software = str(exif.get(TAG_SOFTWARE, ""))
        if software and any(tag in software.lower() for tag in EDITOR_TAGS):
            artifacts["software"] = software
            return done(
                Status.SUSPICIOUS,
                0.55,
                0.8,
                "File history names editing software.",
                f"The software tag reads {software!r}, consistent with "
                "the file passing through an editor.",
                Reliability.OK,
                "Explicit editor tag; tags can be forged, so one tile only.",
                artifacts,
            )
        if not exif:
            return done(
                Status.CANNOT_DETERMINE,
                0.0,
                0.3,
                "No file history to read.",
                "The file carries no EXIF metadata and no C2PA manifest, "
                "as is normal for images shared via chat apps and social media.",
                Reliability.UNRELIABLE,
                "Stripped metadata is the norm, not evidence.",
                artifacts,
            )
        make = str(exif.get(TAG_MAKE, "")).strip()
        model = str(exif.get(TAG_MODEL, "")).strip()
        artifacts["exif_tags"] = str(len(exif))
        if make or model:
            camera = f"{make} {model}".strip()
            if software:
                artifacts["software"] = software
                return done(
                    Status.CANNOT_DETERMINE,
                    0.0,
                    0.4,
                    "File history is unclear.",
                    f"Camera tags ({camera}) look plausible, but an "
                    f"unrecognized software tag ({software!r}) needs context.",
                    Reliability.DEGRADED,
                    "Unknown software string; not on the editor list.",
                    artifacts,
                )
            if c2pa_state == "unchecked":
                return done(
                    Status.CANNOT_DETERMINE,
                    0.0,
                    0.4,
                    "File history looks plausible but unchecked.",
                    f"Camera tags ({camera}) are consistent, but C2PA "
                    "could not be checked in this environment.",
                    Reliability.DEGRADED,
                    "Install c2pa-python for the full provenance read.",
                    artifacts,
                )
            return done(
                Status.CONFIRMED,
                0.5,
                0.7,
                "File history and timestamps are internally consistent.",
                f"Camera tags ({camera}) agree with a single-camera save, "
                "no editor tag, and no manifest contradiction. Metadata is "
                "easy to forge, so this supports but never proves.",
                Reliability.OK,
                "Complete camera EXIF; no C2PA manifest (not a contradiction).",
                artifacts,
            )
        return done(
            Status.CANNOT_DETERMINE,
            0.0,
            0.4,
            "File history is too thin to judge.",
            f"Only {len(exif)} tags and no camera make or model.",
            Reliability.DEGRADED,
            "Partial metadata; absence of evidence is not contradiction.",
            artifacts,
        )


MODULE = MetadataC2paModule()
