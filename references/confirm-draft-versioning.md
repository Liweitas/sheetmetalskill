# Confirm-draft versioning (factory vN vs revN)

**Source:** user t69u, 2026-10-28 (Asia/Shanghai); **superseding bump policy** user t43u/t44u, 2026-10-28 (v2.8.11).
**Hard rule pointers:** SKILL.md user hard rule 11 (partially superseded) + **rule 14** (new default).

Outbound trust: only the live `{VER}_CONFIRM_DRAFT.zip` + matching `{VER}_CONFIRM_DRAFT.zip.sha256` is authoritative. Never treat older chat attachments, `_before_*` archives, or `*_CONFIRM_DRAFT_revN.zip` as the current outbound package.


## Outbound zip filename + single top-level (user t40u / v2.8.10)

Hard rule pointer: SKILL.md user hard rule 13.

- Outbound zip **filenames must start with the factory code VER**:
  `{VER}_CONFIRM_DRAFT.zip`, `{VER}_CONFIRM_DRAFT_revN.zip`, `{VER}_OPEN_ME.zip`.
- **Forbidden** as outbound live / chat attachments: bare `CONFIRM_DRAFT.zip`,
  `CONFIRM_DRAFT_revN.zip`, `CONFIRM_DRAFT_current.zip` (download name collisions;
  macOS Archive Utility creates a folder named after the zip when there are multiple
  top-level entries, which then collides across orders).
- Zip **interior must have exactly one top-level directory**, named `{VER}/`.
  Put CHANGELOG inside that tree (prefer `{VER}/DOC/{VER}_CHANGELOG.txt` or
  `{VER}/{VER}_CHANGELOG.txt`). No loose top-level files beside `{VER}/`.
- Chat attachments must point at the VER-prefixed paths so the downloaded
  filename on disk also carries VER.

## When to bump factory vN (NEW DEFAULT — user t43u/t44u / v2.8.11)

**Each new confirmation package the user will download/unzip must bump the factory trailing `vN`** (v1→v2→v3…). This **supersedes** the older t69u sentence that said PDF layout / README / packaging-only tweaks do **not** bump factory v.

Bump factory `vN` for **any** new outbound `CONFIRM_DRAFT` the user is meant to download — including:

- PDF style / layout changes
- packaging / zip naming / README changes
- **and** geometry / hole / structure changes

Do **not** keep shipping the same `…-v1` folder for successive confirm drafts just because geometry is unchanged. After unzip, the folder and every file prefix must show the new trailing `vN`.

Full rename requirements on bump:

- Zip filename = `{NEW_VER}_CONFIRM_DRAFT.zip` (optional same-payload `{NEW_VER}_OPEN_ME.zip`)
- Zip has exactly one top-level dir = `{NEW_VER}/`
- Every file inside is prefixed with `{NEW_VER}` (PDF pages, STEP headers, DXF names, DOC, NEST, etc.)
- Old factory VER’s complete live zip(+sha256) moves into `SUPERSEDED/`
- Write a CHANGELOG line explaining the bump reason
- Keep `production_release=false` unless the user said otherwise

Still keep:

- First five segments `S-材质-板厚-日期-编号` unchanged when only revising the same order; only bump trailing `-vN`
- Geometry-hash-preserving rename when geometry is unchanged (`scripts/release_package.py rename`; re-render PDFs so every page prints `NEW_VER`)

## revN (optional internal snapshot — not the preferred user-facing path)

`revN` under the *current* factory VER is fine as an **internal** snapshot (same live `{VER}_CONFIRM_DRAFT.zip`, plus `{VER}_CONFIRM_DRAFT_revN.zip` + CHANGELOG line). Helper:

```bash
python3 scripts/snapshot_confirm_rev.py /ABS/named_release_or_order_dir "short what changed"
```

That script finds the live `{VER}_CONFIRM_DRAFT.zip`, picks next revN, copies zip + writes sha256, appends the CHANGELOG line, prints paths/sha256. It does **not** bump factory v — and **must not** be treated as the preferred outbound distinction for the user. Prefer bumping factory `vN` for any new package the user will download/unzip; do not rely on bare `CONFIRM_DRAFT_revN` under an old `…-v1` name as the user-facing unzip folder.

When you *do* take an internal same-v revN snapshot:

1. Keep the live file named `{VER}_CONFIRM_DRAFT.zip` (always = current). Rebuild or overwrite that live zip as usual; refresh `{VER}_CONFIRM_DRAFT.zip.sha256`.
2. **Also** copy the current live zip to `{VER}_CONFIRM_DRAFT_revN.zip` and write matching `{VER}_CONFIRM_DRAFT_revN.zip.sha256` (same sidecar style: `hex  basename`).
3. `N` = next integer among existing `*_CONFIRM_DRAFT_rev*.zip` in that folder; start at `0` if none.
4. Append **one** line to `{VER}_CHANGELOG.txt` (create if missing):

```text
YYYY-MM-DD HH:MM Asia/Shanghai | revN | short what changed | sha256=<hex>
```

## Stop ad-hoc backup names

Once revN + CHANGELOG exist for a VER (or after a factory-v bump with SUPERSEDED), stop inventing new ad-hoc names such as `_CONFIRM_DRAFT_before_t67u_pdf_home` for future backups. Existing `before_*` archives may be **copied** (or renamed) into `revN` / `SUPERSEDED` for backfill; do not delete them without a verified copy. Prefer moving verified ad-hoc backups into `SUPERSEDED/` under the order to reduce clutter (keep their `.sha256` with them).

## SUPERSEDED on factory bump

When factory v does bump:

1. Publish the new `…-v(N+1)` named_release / stage as usual (full prefix rename + PDF re-render).
2. Move the previous factory-v complete confirm ZIP + `.sha256` (and OPEN_ME if present) into `SUPERSEDED/` (order-root or named_release-local pattern already in use).
3. Do not delete the superseded package without a verified copy in `SUPERSEDED/`.

## Checklist (new outbound confirm draft)

- [ ] Decide next factory `NEW_VER` (same first five segments, bump trailing vN).
- [ ] Geometry unchanged → `release_package.py rename` (geom hashes equal) + re-render PDFs with NEW_VER; geometry changed → rebuild then package under NEW_VER.
- [ ] Live `{NEW_VER}_CONFIRM_DRAFT.zip` (+ optional OPEN_ME) written; sha256 refreshed.
- [ ] Zip has exactly one top-level directory = NEW_VER; every file prefixed NEW_VER; CHANGELOG inside that tree with bump reason.
- [ ] Old factory VER live zip(+sha256) moved to `SUPERSEDED/`.
- [ ] Outbound message attaches only live NEW_VER zip + its sha256 (no bare CONFIRM_DRAFT*.zip).
- [ ] `production_release=false` unless user authorized otherwise.
- [ ] Prefer factory-v bump over shipping another revN under the old v folder for user download.
