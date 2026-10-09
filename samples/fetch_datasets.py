"""Fetch helper for real-world sample images/video. YOU run this; nothing downloads itself.

I (the agent) did not download anything: dataset hosts, URLs and licenses
change, and per project rules I must not invent URLs. So this script takes
URLs YOU provide and handles the boring parts: download, sha256 verify,
unpack, and print the manifest row to append.

Usage:
    python3 samples/fetch_datasets.py --list
        Print candidate datasets (certain ones + verify-first ones).

    python3 samples/fetch_datasets.py --url <URL> --sha256 <HEX> \\
        --dest samples/external/<name>.zip [--unpack-dir samples/external/<name>]
        Download, verify the hash, optionally unzip, then print a manifest
        entry template with the real sha256 filled in.

After fetching, append the printed row to samples/manifest.json with the
right category (real, gan, diffusion, video-real, ...) and split. Keep new
downloads in "dev" unless you are deliberately extending "heldout" — and
never tune thresholds on heldout entries.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import urllib.request
import zipfile
from pathlib import Path

CHUNK = 1024 * 1024

CANDIDATES_CERTAIN = """
Certain to exist (I am confident these datasets/projects exist; VERIFY the
current download URL + license yourself before fetching):

1. COCO 2017 (Common Objects in Context, Lin et al.)
   Why:   permissively-collected real photos for the "real" category.
   License: PER-IMAGE, varies (mostly Flickr CC variants) — NOT uniform.
            Filter by license before redistributing anything.
   Size:  ~1 GB val2017 images (+annotations). Start with val, not train.
   Split: dev real.

2. FFHQ (Flickr-Faces-HQ, NVIDIA / Karras et al.)
   Why:   70k high-quality real faces; baseline "real" for face work.
   License: VERIFY — reported as CC BY-NC-SA with Flickr ToS strings
            attached; confirm current terms before use/redistribution.
   Size:  full set is large (~90 GB images); fetch a small subset first.
   Split: dev real.

3. FaceForensics++ (Rossler et al.)
   Why:   real + manipulated face videos incl. heavily compressed (c40)
           versions — the closest public proxy to chat-app recompression
           and to video-real / video-spliced categories.
   License: VERIFY — research-use access terms; confirm before use.
   Size:  tens of GB full; fetch one compression level + a few videos first.
   Split: dev video-real / manipulated video.
"""

CANDIDATES_VERIFY_FIRST = """
NOT verified — widely cited, but I could not confirm current hosting/URLs
from here. Confirm existence, host, license and size yourself first:

- CASIA v1/v2 image tampering (splice + copy-move with masks).
- Columbia uncompressed image splicing detection set.
- Any "WhatsApp-recompressed" paired set — likely does not exist publicly;
  our generated q30 fixtures + FF++ c40 are the honest fallback.
- Diffusion-face sets (e.g. DFDC-style diffusion extensions): confirm host.
"""


def cmd_list() -> None:
    print(CANDIDATES_CERTAIN)
    print(CANDIDATES_VERIFY_FIRST)


def download(url: str, dest: Path, expect_sha256: str | None) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {url} ...")
    with urllib.request.urlopen(url) as resp, open(dest, "wb") as fh:
        h = hashlib.sha256()
        while True:
            chunk = resp.read(CHUNK)
            if not chunk:
                break
            fh.write(chunk)
            h.update(chunk)
    got = h.hexdigest()
    print(f"sha256: {got}")
    if expect_sha256 and got != expect_sha256.lower():
        dest.unlink(missing_ok=True)
        raise SystemExit("Hash mismatch — deleted partial file. Check the URL/hash.")
    return dest


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(
        description="User-run dataset fetch helper (no hardcoded URLs)."
    )
    ap.add_argument(
        "--list", action="store_true", help="print candidate datasets and exit"
    )
    ap.add_argument("--url", help="download URL (you provide it)")
    ap.add_argument(
        "--sha256", default=None, help="expected sha256 hex (you provide it)"
    )
    ap.add_argument(
        "--dest",
        default=None,
        help="where to save, e.g. samples/external/ffhq-subset.zip",
    )
    ap.add_argument(
        "--unpack-dir", default=None, help="if set and file is a zip, unpack here"
    )
    args = ap.parse_args(argv)

    if args.list or not args.url:
        cmd_list()
        if not args.url:
            return

    if not args.dest:
        raise SystemExit("--dest is required with --url")
    dest = download(args.url, Path(args.dest), args.sha256)
    print(f"Saved {dest} ({dest.stat().st_size / 1024 / 1024:.1f} MiB)")

    if args.unpack_dir and zipfile.is_zipfile(dest):
        out = Path(args.unpack_dir)
        out.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(dest) as zf:
            zf.extractall(out)
        n = sum(1 for _ in out.rglob("*") if _.is_file())
        print(f"Unpacked {n} files to {out}")
    elif args.unpack_dir:
        print("Not a zip file; skipping unpack.", file=sys.stderr)

    print(
        """
Next: add one manifest row per file, e.g.
  {"file": "external/<name>/<file>", "category": "real", "source": "<dataset paper/site>",
   "license": "<confirmed license>", "ground_truth": {"manipulated": false},
   "split": "dev", "notes": "<subset + access date>"}
Then run: pytest backend/tests/test_samples.py (add rows to missing_files check if needed).
"""
    )


if __name__ == "__main__":
    main()
