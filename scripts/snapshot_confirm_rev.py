#!/usr/bin/env python3
"""Snapshot live {VER}_CONFIRM_DRAFT.zip as next revN (same factory v) — INTERNAL only.

Usage:
  python3 scripts/snapshot_confirm_rev.py REVISION_OR_NAMED_RELEASE_DIR [optional note]

- Finds {VER}_CONFIRM_DRAFT.zip (VER from dirname, or from the zip filename prefix).
- Computes next revN from existing *_CONFIRM_DRAFT_rev*.zip (start at 0).
- Copies current zip to {VER}_CONFIRM_DRAFT_revN.zip and writes matching .sha256
  sidecar (hex + two spaces + basename), matching live CONFIRM_DRAFT.zip.sha256 style.
- Appends one line to {VER}_CHANGELOG.txt (create if missing):
  YYYY-MM-DD HH:MM Asia/Shanghai | revN | note | sha256=<hex>
- Prints paths and sha256. Does NOT bump factory v.

NOTE (user t43u/t44u / skill v2.8.11): for any NEW outbound CONFIRM_DRAFT the user will
download/unzip (including PDF style/layout, packaging/zip naming, README, and geometry
changes), prefer bumping factory trailing vN (v1→v2→v3…) with a full rename — do NOT
treat revN under an old …-v1 name as the preferred user-facing unzip folder. This
script remains for optional internal snapshots under the *current* factory VER.
Stdlib only: pathlib, hashlib, shutil, re, sys, datetime ZoneInfo.
"""
from __future__ import annotations

import hashlib
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

REV_RE = re.compile(r"_CONFIRM_DRAFT_rev(\d+)\.zip$", re.IGNORECASE)
LIVE_RE = re.compile(r"^(.+)_CONFIRM_DRAFT\.zip$", re.IGNORECASE)
SH = ZoneInfo("Asia/Shanghai")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_sha256_sidecar(zip_path: Path, digest: str) -> Path:
    side = Path(str(zip_path) + ".sha256")
    side.write_text(f"{digest}  {zip_path.name}\n", encoding="ascii")
    return side


def detect_ver(root: Path) -> tuple[str, Path]:
    live = root / f"{root.name}_CONFIRM_DRAFT.zip"
    if live.is_file():
        return root.name, live
    matches = sorted(root.glob("*_CONFIRM_DRAFT.zip"))
    # Prefer exact live name pattern; ignore *_CONFIRM_DRAFT_rev*.zip and before_* by pattern
    live_candidates = []
    for p in matches:
        m = LIVE_RE.match(p.name)
        if not m:
            continue
        if "_CONFIRM_DRAFT_rev" in p.name or "_CONFIRM_DRAFT_before_" in p.name:
            continue
        live_candidates.append((m.group(1), p))
    if len(live_candidates) == 1:
        return live_candidates[0]
    if not live_candidates:
        raise SystemExit(f"ERROR: no live *_CONFIRM_DRAFT.zip under {root}")
    raise SystemExit(
        "ERROR: multiple live CONFIRM_DRAFT zips: "
        + ", ".join(p.name for _, p in live_candidates)
    )


def next_rev_n(root: Path, ver: str) -> int:
    highest = -1
    for p in root.glob(f"{ver}_CONFIRM_DRAFT_rev*.zip"):
        m = REV_RE.search(p.name)
        if m:
            highest = max(highest, int(m.group(1)))
    return highest + 1


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[1] in ("-h", "--help"):
        print(
            "Usage: snapshot_confirm_rev.py REVISION_OR_NAMED_RELEASE_DIR [note]",
            file=sys.stderr,
        )
        return 2
    root = Path(argv[1]).expanduser().resolve()
    if not root.is_dir():
        raise SystemExit(f"ERROR: not a directory: {root}")
    note = " ".join(argv[2:]).strip() if len(argv) > 2 else "same-factory-v confirm-draft snapshot"
    # ASCII-safe note for CHANGELOG (keep printable)
    note = "".join(c if 32 <= ord(c) < 127 or ord(c) > 127 else "?" for c in note)
    if not note:
        note = "same-factory-v confirm-draft snapshot"

    ver, live = detect_ver(root)
    if not live.is_file():
        raise SystemExit(f"ERROR: missing live zip: {live}")

    rev_n = next_rev_n(root, ver)
    rev_zip = root / f"{ver}_CONFIRM_DRAFT_rev{rev_n}.zip"
    if rev_zip.exists():
        raise SystemExit(f"ERROR: target already exists: {rev_zip}")

    shutil.copy2(live, rev_zip)
    digest = sha256_file(rev_zip)
    live_digest = sha256_file(live)
    if digest != live_digest:
        rev_zip.unlink(missing_ok=True)
        raise SystemExit("ERROR: copied rev zip sha256 != live zip sha256")
    side = write_sha256_sidecar(rev_zip, digest)

    now = datetime.now(SH).strftime("%Y-%m-%d %H:%M Asia/Shanghai")
    line = f"{now} | rev{rev_n} | {note} | sha256={digest}\n"
    changelog = root / f"{ver}_CHANGELOG.txt"
    with changelog.open("a", encoding="utf-8") as f:
        f.write(line)

    print(f"VER={ver}")
    print(f"live={live}")
    print(f"live_sha256={live_digest}")
    print(f"revN=rev{rev_n}")
    print(f"rev_zip={rev_zip}")
    print(f"rev_sha256={digest}")
    print(f"rev_sidecar={side}")
    print(f"changelog={changelog}")
    print(f"changelog_line={line.rstrip()}")
    print("factory_v_bumped=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
