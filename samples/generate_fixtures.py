"""Generate tiny synthetic fixtures + manifest.json. Offline, deterministic.

Usage (run from repo root):
    python3 samples/generate_fixtures.py [--root samples]

What it creates:
    <root>/fixtures/*.png|*.jpg|*.gif   small generated media files
    <root>/manifest.json                 one entry per file (see loader schema)

Method (seeded RNG, no downloads):
- real:       smooth gradient + seeded noise, saved as PNG
- splice:     left half of image A + right half of image B, PNG
- copy-move:  24x24 block copied within the same image, PNG
- whatsapp-recompressed: real image re-saved as JPEG quality 30
  (proxy for heavy chat-app recompression; also downscaled to 96px)
- video-real / video-spliced: 8-frame animated GIFs (no ffmpeg here);
  replaced by mp4 fixtures in Phase 4. Labelled honestly in manifest.

The heldout split uses a different seed. NEVER tune thresholds on it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw

SIZE = (128, 128)
SMALL = (96, 96)
VIDEO_SIZE = (64, 64)
N_VIDEO_FRAMES = 8
JPEG_QUALITY = 30
SEED_DEV = 7
SEED_HELDOUT = 99
MANIFEST_VERSION = 1
LOCAL_LICENSE = (
    "CC0-1.0 (generated locally by generate_fixtures.py; no rights reserved)"
)
LOCAL_SOURCE = "synthetic (tessera samples/generate_fixtures.py)"


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def base_array(rng: np.random.Generator, size: tuple[int, int] = SIZE) -> np.ndarray:
    """Smooth two-axis gradient plus seeded noise (looks unnatural on purpose)."""
    w, h = size
    xs = np.linspace(0, 255, w, dtype=np.float64)
    ys = np.linspace(0, 255, h, dtype=np.float64)
    gx, gy = np.meshgrid(xs, ys)
    r = (0.6 * gx + 0.4 * gy + rng.integers(0, 40, size=(h, w))).clip(0, 255)
    g = (0.5 * gy + 0.3 * gx + rng.integers(0, 40, size=(h, w))).clip(0, 255)
    b = (255 - 0.5 * gx + rng.integers(0, 40, size=(h, w))).clip(0, 255)
    return np.stack([r, g, b], axis=-1).astype(np.uint8)


def save_png(arr: np.ndarray, path: Path) -> None:
    Image.fromarray(arr, mode="RGB").save(path, format="PNG")


def make_video_frames(spliced: bool) -> list[Image.Image]:
    """8 deterministic frames. Spliced version changes scene halfway (hard cut)."""
    frames: list[Image.Image] = []
    for i in range(N_VIDEO_FRAMES):
        img = Image.new("RGB", VIDEO_SIZE, (18, 20, 30))
        d = ImageDraw.Draw(img)
        if not spliced or i < N_VIDEO_FRAMES // 2:
            x = 4 + i * 6  # square glides right (terracotta)
            d.rectangle([x, 26, x + 12, 38], fill=(203, 92, 60))
        else:
            y = 4 + (i - N_VIDEO_FRAMES // 2) * 10  # circle drops (verdigris)
            d.ellipse([26, y, 38, y + 12], fill=(64, 145, 140))
        frames.append(img)
    return frames


def save_gif(frames: list[Image.Image], path: Path) -> None:
    frames[0].save(
        path,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=200,
        loop=0,
    )


def entry(
    path: Path,
    root: Path,
    category: str,
    split: str,
    ground_truth: dict[str, Any],
    notes: str,
) -> dict[str, Any]:
    rel = path.relative_to(root).as_posix()
    img = Image.open(path)
    return {
        "file": rel,
        "category": category,
        "source": LOCAL_SOURCE,
        "license": LOCAL_LICENSE,
        "ground_truth": ground_truth,
        "split": split,
        "width": img.width,
        "height": img.height,
        "sha256": sha256_of(path),
        "notes": notes,
    }


def build_images(
    fx: Path, seed: int, split: str
) -> list[tuple[Path, str, dict[str, Any], str]]:
    """Return (path, category, ground_truth, notes) for image fixtures; writes files."""
    rng = np.random.default_rng(seed)
    a = base_array(rng)
    b = base_array(rng)
    specs: list[tuple[Path, str, dict[str, Any], str]] = []

    p_real = fx / f"{split}_real.png"
    save_png(a, p_real)
    specs.append(
        (
            p_real,
            "real",
            {"manipulated": False},
            "Seeded gradient+noise; unedited reference.",
        )
    )

    p_splice = fx / f"{split}_splice.png"
    splice = np.concatenate([a[:, : SIZE[0] // 2], b[:, SIZE[0] // 2 :]], axis=1)
    save_png(splice, p_splice)
    specs.append(
        (
            p_splice,
            "splice",
            {"manipulated": True, "type": "splice", "seam_x": SIZE[0] // 2},
            "Left half from seed-A image, right half from seed-B image; vertical seam at x=64.",
        )
    )

    if split == "dev":
        p_cm = fx / f"{split}_copymove.png"
        cm = a.copy()
        block, dst = (16, 16, 24, 24), (80, 80)
        cm[dst[1] : dst[1] + block[3], dst[0] : dst[0] + block[2]] = a[
            block[1] : block[1] + block[3], block[0] : block[0] + block[2]
        ]
        save_png(cm, p_cm)
        specs.append(
            (
                p_cm,
                "copy-move",
                {
                    "manipulated": True,
                    "type": "copy-move",
                    "copied_region": [16, 16, 24, 24],
                    "pasted_at": [80, 80],
                },
                "24x24 block copied from (16,16) to (80,80) within the same image.",
            )
        )

        p_wa = fx / f"{split}_recompressed_q30.jpg"
        Image.fromarray(a, mode="RGB").resize(SMALL).save(
            p_wa, format="JPEG", quality=JPEG_QUALITY
        )
        specs.append(
            (
                p_wa,
                "whatsapp-recompressed",
                {
                    "manipulated": False,
                    "recompressed": True,
                    "jpeg_quality": JPEG_QUALITY,
                },
                "Proxy for chat-app recompression: downscaled to 96px, JPEG quality 30.",
            )
        )
    return specs


def build_videos(fx: Path, split: str) -> list[tuple[Path, str, dict[str, Any], str]]:
    specs: list[tuple[Path, str, dict[str, Any], str]] = []
    if split != "dev":
        return specs
    p_real = fx / f"{split}_video_real.gif"
    save_gif(make_video_frames(spliced=False), p_real)
    specs.append(
        (
            p_real,
            "video-real",
            {"manipulated": False, "frames": N_VIDEO_FRAMES, "format": "gif"},
            "Single smooth motion; GIF placeholder until Phase 4 mp4 fixtures land.",
        )
    )
    p_sp = fx / f"{split}_video_spliced.gif"
    save_gif(make_video_frames(spliced=True), p_sp)
    specs.append(
        (
            p_sp,
            "video-spliced",
            {
                "manipulated": True,
                "type": "hard-cut",
                "cut_at_frame": N_VIDEO_FRAMES // 2,
                "frames": N_VIDEO_FRAMES,
                "format": "gif",
            },
            "Scene changes abruptly at frame 4; GIF placeholder until Phase 4 mp4 fixtures land.",
        )
    )
    return specs


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Generate offline synthetic fixtures + manifest.json"
    )
    ap.add_argument(
        "--root", default="samples", help="samples directory (default: samples)"
    )
    args = ap.parse_args()
    root = Path(args.root)
    fx = root / "fixtures"
    fx.mkdir(parents=True, exist_ok=True)

    entries: list[dict[str, Any]] = []
    for split, seed in (("dev", SEED_DEV), ("heldout", SEED_HELDOUT)):
        for path, category, gt, notes in build_images(fx, seed, split) + build_videos(
            fx, split
        ):
            entries.append(entry(path, root, category, split, gt, notes))

    manifest = {"version": MANIFEST_VERSION, "entries": entries}
    (root / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    total_bytes = sum((root / e["file"]).stat().st_size for e in entries)
    print(f"Wrote {len(entries)} fixtures ({total_bytes / 1024:.1f} KiB) to {fx}")
    print(f"Manifest: {root / 'manifest.json'}")


if __name__ == "__main__":
    main()
