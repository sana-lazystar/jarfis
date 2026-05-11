"""JARFIS IA — Information Architecture snapshot/load/validate/merge.

This module implements the IA (Information Architecture) primitives shared by
all phases that read or write `ia/` (manifest.json + pages/{slug}.md +
shared.json). Per ADR ia-as-po-ssot:
  - PO Phase 1b writes IA (SSOT).
  - All downstream phases read IA.
  - Phase 6 merges work IA back into Org IA using 3-way confirm-merge.

Subcommands (jarfis_cli.py registration):
    snapshot --src P --dest P [--create-empty-if-missing]
        Read-only copy of Org IA → baseline (work start).
    validate <ia_dir> [--non-strict]
        Run R1~R12 validation. Exits 2 on failure.
    merge --baseline P --current P --work P (--dry-run|--apply [--dest P])
        3-way confirm-merge. Conflicts surfaced; caller resolves.
    list-pages --work P [--slugs s1,s2]
        Query pages from work IA.

Validation rules (R1~R12):
    R1  manifest.json exists                                always
    R2  manifest.version == "2.0"                           always
    R3  slug matches ^[a-z][a-z0-9-]*$                      always
    R4  no duplicate slugs                                  always
    R5  no duplicate routes                                 always
    R6  parent in slug set or null                          always
    R7  pages/{slug}.md exists for each manifest entry     always
    R8  frontmatter.slug == manifest.slug                   always
    R9  no orphan pages/*.md (1:1 with manifest)            always
    R10 required frontmatter fields present                 strict
    R11 navigation.entry_from/exits_to refs valid           strict
    R12 parent chain acyclic (error) + depth <= 8 (warning) always (cycle) / strict (depth)

IMPORTANT (audit R-2 mitigation): hash/equality comparison uses canonical
JSON (sort_keys=True, ensure_ascii=False) so different key orderings do
not yield false conflicts. For pages, frontmatter (canonical dict) and
notes_body (raw str) compare separately, not raw bytes.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml

from .utils import json_error, json_output


# ─────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────

MANIFEST_VERSION = "2.0"
SLUG_RE = re.compile(r"^[a-z][a-z0-9-]*$")
MAX_PARENT_DEPTH = 8  # Audit R-3: warning-only threshold for sitemap tree depth.
REQUIRED_FRONTMATTER_FIELDS = ("slug", "route", "title", "role", "depth")
VALID_ROLES = ("public", "auth", "admin")


# ─────────────────────────────────────────────────────────────────────
# Dataclasses
# ─────────────────────────────────────────────────────────────────────


@dataclass
class PageDoc:
    slug: str
    route: str
    title: str
    role: str
    parent: Optional[str]
    depth: int
    frontmatter: dict
    notes_body: str
    detail_path: Path


@dataclass
class IADocument:
    manifest: dict
    pages: dict  # {slug: PageDoc}
    shared: dict
    ia_dir: Path


@dataclass
class SnapshotResult:
    src: Path
    dest: Path
    files_copied: int
    pages_count: int
    created_empty: bool


@dataclass
class ValidationResult:
    valid: bool
    errors: list
    warnings: list
    rules_checked: list


@dataclass
class MergeChange:
    slug: str
    action: str  # "added" | "modified" | "removed" | "conflict"
    detail: dict


@dataclass
class MergeResult:
    changes: list
    conflicts: list
    applied: bool
    dest_dir: Optional[Path]


@dataclass
class PageInfo:
    slug: str
    route: str
    title: str
    detail_path: Path
    role: str


# ─────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────


def _canonical_json(obj) -> str:
    """Canonical JSON representation for stable equality comparison.

    Audit R-2 mitigation: sort_keys=True ensures key ordering doesn't
    cause spurious diffs across baseline/current/work signatures.
    """
    return json.dumps(obj, sort_keys=True, ensure_ascii=False)


def _parse_frontmatter(md_path: Path) -> tuple[dict, str]:
    """Return (frontmatter_dict, body_after_frontmatter) for a markdown file.

    Supports YAML frontmatter delimited by `---` lines at the top.
    """
    content = md_path.read_text(encoding="utf-8")
    if not content.startswith("---"):
        return {}, content

    # Strip leading '---' (with optional trailing newline)
    rest = content[3:]
    if rest.startswith("\n"):
        rest = rest[1:]

    # Find closing '---' delimiter on its own line
    end_marker_idx = -1
    end_marker_len = 0
    for marker in ("\n---\n", "\n---\r\n", "\n---"):
        idx = rest.find(marker)
        if idx != -1:
            end_marker_idx = idx
            end_marker_len = len(marker)
            break

    if end_marker_idx == -1:
        return {}, content

    yaml_str = rest[:end_marker_idx]
    body = rest[end_marker_idx + end_marker_len:]
    if body.startswith("\n"):
        body = body[1:]

    try:
        fm = yaml.safe_load(yaml_str) or {}
    except yaml.YAMLError:
        fm = {}
    if not isinstance(fm, dict):
        fm = {}
    return fm, body


def _slug_signature(ia: Optional[IADocument], slug: str) -> Optional[dict]:
    """Return canonical signature for a slug from an IA, or None if absent.

    Signature shape:
        {
            "manifest": canonical JSON str of manifest entry (or None),
            "frontmatter": canonical JSON str of frontmatter (or None),
            "notes_body": raw body string (or None),
        }
    """
    if ia is None:
        return None
    entry = None
    for e in ia.manifest.get("pages", []) or []:
        if e.get("slug") == slug:
            entry = e
            break
    page = ia.pages.get(slug)
    if entry is None and page is None:
        return None
    return {
        "manifest": _canonical_json(entry) if entry is not None else None,
        "frontmatter": _canonical_json(page.frontmatter) if page is not None else None,
        "notes_body": page.notes_body if page is not None else None,
    }


def _classify(b, c, w) -> tuple[str, Optional[str]]:
    """Classify a slug given baseline / current / work signatures.

    Returns (action, winner) where:
        action ∈ {"unchanged", "modified", "added", "removed", "conflict"}
        winner ∈ {"work", "current", "either", None}
    """
    # All three identical (including all None — but caller filters that)
    if b == c == w:
        return ("unchanged", "either")

    # Pure adds — slug not in baseline
    if b is None:
        if c is None and w is not None:
            return ("added", "work")
        if c is not None and w is None:
            return ("added", "current")
        if c == w:
            return ("added", "either")
        return ("conflict", None)

    # Pure removes — slug not in either current or work
    if c is None and w is None:
        return ("removed", None)

    # Work removed
    if w is None:
        if b == c:
            return ("removed", None)  # current unchanged → accept work's removal
        return ("conflict", None)  # work removed, current changed

    # Current removed
    if c is None:
        if b == w:
            return ("removed", None)  # work unchanged → accept current's removal
        return ("conflict", None)  # current removed, work changed

    # All three present
    if b == c:
        return ("modified", "work")  # work changed
    if b == w:
        return ("modified", "current")  # current changed
    if c == w:
        return ("modified", "either")  # both moved to same point
    return ("conflict", None)


def _read_manifest(ia_dir: Path) -> dict:
    """Read manifest.json from an IA dir. Raises FileNotFoundError if absent."""
    manifest_path = ia_dir / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"manifest.json not found: {manifest_path}")
    with open(manifest_path, encoding="utf-8") as f:
        return json.load(f)


# ─────────────────────────────────────────────────────────────────────
# Public functions
# ─────────────────────────────────────────────────────────────────────


def load_ia(ia_dir: Path) -> IADocument:
    """Parse manifest.json + pages/{slug}.md + shared.json from `ia_dir`.

    Critic #1 fix — primitive shared by validate/merge/list-pages so they
    do not re-parse the IA on every call.

    Raises FileNotFoundError when manifest.json is missing. Lenient on
    missing detail files / orphan pages — those are surfaced by
    validate_ia.
    """
    ia_dir = Path(ia_dir)
    manifest = _read_manifest(ia_dir)

    pages: dict = {}
    for entry in manifest.get("pages", []) or []:
        slug = entry.get("slug")
        if not slug:
            continue
        detail_rel = entry.get("detail") or f"pages/{slug}.md"
        detail_path = ia_dir / detail_rel
        if not detail_path.is_file():
            # validate_ia will flag R7 — load_ia just skips silently.
            continue
        fm, body = _parse_frontmatter(detail_path)
        pages[slug] = PageDoc(
            slug=fm.get("slug", slug),
            route=fm.get("route", entry.get("route", "")),
            title=fm.get("title", entry.get("title", "")),
            role=fm.get("role", entry.get("role", "")),
            parent=fm.get("parent", entry.get("parent")),
            depth=int(fm.get("depth", entry.get("depth", 0)) or 0),
            frontmatter=fm,
            notes_body=body,
            detail_path=detail_path,
        )

    shared: dict = {}
    shared_path = ia_dir / "shared.json"
    if shared_path.is_file():
        try:
            with open(shared_path, encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                shared = loaded
        except json.JSONDecodeError:
            shared = {}

    return IADocument(manifest=manifest, pages=pages, shared=shared, ia_dir=ia_dir)


def snapshot_org_ia(
    src: Path,
    dest: Path,
    *,
    create_empty_if_missing: bool = False,
) -> SnapshotResult:
    """Read-only copy of Org IA from `src` to `dest`.

    Critic #2 fix (D10 cold-start support):
      - src missing + create_empty_if_missing=True → create minimal
        empty IA at dest (manifest v2.0 with no pages, empty shared).
      - src missing + create_empty_if_missing=False → FileNotFoundError.

    When src exists, the existing dest is removed first so the operation
    is deterministic (no leftovers from a prior snapshot).
    """
    src = Path(src)
    dest = Path(dest)

    if not src.exists():
        if not create_empty_if_missing:
            raise FileNotFoundError(f"Source IA dir not found: {src}")
        dest.mkdir(parents=True, exist_ok=True)
        manifest = {"version": MANIFEST_VERSION, "project": "", "pages": []}
        (dest / "manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        (dest / "pages").mkdir(exist_ok=True)
        (dest / "shared.json").write_text("{}\n", encoding="utf-8")
        return SnapshotResult(
            src=src,
            dest=dest,
            files_copied=0,
            pages_count=0,
            created_empty=True,
        )

    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest, symlinks=False)

    files_copied = 0
    pages_count = 0
    for path in dest.rglob("*"):
        if path.is_file():
            files_copied += 1
            if path.parent.name == "pages" and path.suffix == ".md":
                pages_count += 1

    return SnapshotResult(
        src=src,
        dest=dest,
        files_copied=files_copied,
        pages_count=pages_count,
        created_empty=False,
    )


def validate_ia(ia_dir: Path, *, strict: bool = True) -> ValidationResult:
    """Run schema + integrity validation against an IA dir.

    Always-checked rules: R1~R9, R12 (cycle).
    Strict-only rules: R10, R11, R12 (max_depth warning).
    """
    ia_dir = Path(ia_dir)
    errors: list[str] = []
    warnings: list[str] = []
    rules_checked: list[str] = []

    # R1
    rules_checked.append("R1")
    manifest_path = ia_dir / "manifest.json"
    if not manifest_path.is_file():
        errors.append(f"R1: manifest.json not found at {manifest_path}")
        return ValidationResult(
            valid=False,
            errors=errors,
            warnings=warnings,
            rules_checked=rules_checked,
        )

    try:
        with open(manifest_path, encoding="utf-8") as f:
            manifest = json.load(f)
    except json.JSONDecodeError as exc:
        errors.append(f"R1: manifest.json invalid JSON — {exc}")
        return ValidationResult(
            valid=False,
            errors=errors,
            warnings=warnings,
            rules_checked=rules_checked,
        )

    pages = manifest.get("pages", []) or []

    # R2 — version
    rules_checked.append("R2")
    version = manifest.get("version")
    if version != MANIFEST_VERSION:
        errors.append(
            f"R2: manifest.version is {version!r}, expected {MANIFEST_VERSION!r}"
        )

    # R3 — slug regex
    rules_checked.append("R3")
    for entry in pages:
        slug = entry.get("slug", "")
        if not isinstance(slug, str) or not SLUG_RE.match(slug):
            errors.append(
                f"R3: invalid slug {slug!r} (must match ^[a-z][a-z0-9-]*$)"
            )

    # R4 — duplicate slugs
    rules_checked.append("R4")
    slugs = [e.get("slug") for e in pages]
    seen = set()
    dups = []
    for s in slugs:
        if s in seen and s not in dups:
            dups.append(s)
        seen.add(s)
    for d in dups:
        errors.append(f"R4: duplicate slug {d!r}")

    # R5 — duplicate routes
    rules_checked.append("R5")
    routes = [e.get("route") for e in pages]
    seen_r = set()
    dups_r = []
    for r in routes:
        if r in seen_r and r not in dups_r:
            dups_r.append(r)
        seen_r.add(r)
    for d in dups_r:
        errors.append(f"R5: duplicate route {d!r}")

    # R6 — parent ref
    rules_checked.append("R6")
    slug_set = {s for s in slugs if isinstance(s, str)}
    for entry in pages:
        parent = entry.get("parent")
        if parent is not None and parent not in slug_set:
            errors.append(
                f"R6: parent {parent!r} for slug {entry.get('slug')!r} "
                "not in slug set"
            )

    # R7 — detail file exists
    rules_checked.append("R7")
    for entry in pages:
        slug = entry.get("slug")
        detail = entry.get("detail") or f"pages/{slug}.md"
        detail_path = ia_dir / detail
        if not detail_path.is_file():
            errors.append(
                f"R7: detail file missing for slug {slug!r}: {detail_path}"
            )

    # R8 — frontmatter slug matches manifest slug
    rules_checked.append("R8")
    for entry in pages:
        slug = entry.get("slug")
        detail = entry.get("detail") or f"pages/{slug}.md"
        detail_path = ia_dir / detail
        if not detail_path.is_file():
            continue  # R7 already flagged
        fm, _ = _parse_frontmatter(detail_path)
        fm_slug = fm.get("slug")
        if fm_slug != slug:
            errors.append(
                f"R8: frontmatter slug {fm_slug!r} != manifest slug "
                f"{slug!r} in {detail_path}"
            )

    # R9 — orphan pages
    rules_checked.append("R9")
    pages_dir = ia_dir / "pages"
    if pages_dir.is_dir():
        for md_path in sorted(pages_dir.glob("*.md")):
            stem = md_path.stem
            if stem not in slug_set:
                errors.append(
                    f"R9: orphan page {md_path.name} (no manifest entry)"
                )

    # R10 — required frontmatter fields (strict)
    if strict:
        rules_checked.append("R10")
        for entry in pages:
            slug = entry.get("slug")
            detail = entry.get("detail") or f"pages/{slug}.md"
            detail_path = ia_dir / detail
            if not detail_path.is_file():
                continue
            fm, _ = _parse_frontmatter(detail_path)
            for field_name in REQUIRED_FRONTMATTER_FIELDS:
                if field_name not in fm:
                    errors.append(
                        f"R10: missing required field {field_name!r} in {detail_path}"
                    )

    # R11 — navigation refs (strict)
    if strict:
        rules_checked.append("R11")
        for entry in pages:
            slug = entry.get("slug")
            detail = entry.get("detail") or f"pages/{slug}.md"
            detail_path = ia_dir / detail
            if not detail_path.is_file():
                continue
            fm, _ = _parse_frontmatter(detail_path)
            nav = fm.get("navigation") or {}
            if not isinstance(nav, dict):
                continue
            for direction in ("entry_from", "exits_to"):
                refs = nav.get(direction) or []
                if not isinstance(refs, list):
                    continue
                for ref in refs:
                    if ref not in slug_set:
                        errors.append(
                            f"R11: navigation.{direction} ref {ref!r} in "
                            f"{slug!r} not a valid slug"
                        )

    # R12 — parent chain DAG + max depth warning
    rules_checked.append("R12")
    parent_map = {
        e.get("slug"): e.get("parent")
        for e in pages
        if isinstance(e.get("slug"), str)
    }
    for slug in list(parent_map.keys()):
        visited: set = set()
        chain_len = 0
        current = slug
        cycle_found = False
        while current is not None:
            if current in visited:
                errors.append(f"R12: parent cycle detected involving {slug!r}")
                cycle_found = True
                break
            visited.add(current)
            chain_len += 1
            # Stop if current isn't in the parent_map (dangling, R6 will catch)
            if current not in parent_map:
                break
            current = parent_map.get(current)
        if cycle_found:
            continue
        if strict and chain_len > MAX_PARENT_DEPTH:
            warnings.append(
                f"R12: parent chain for {slug!r} exceeds "
                f"MAX_PARENT_DEPTH={MAX_PARENT_DEPTH} (depth={chain_len}); "
                "consider flattening (warning only — sitemap tree depth ≠ "
                "L0-L4 information layers)."
            )

    return ValidationResult(
        valid=not errors,
        errors=errors,
        warnings=warnings,
        rules_checked=rules_checked,
    )


def merge_3way(
    baseline: Path,
    current: Path,
    work: Path,
    *,
    dry_run: bool = True,
    dest: Optional[Path] = None,
) -> MergeResult:
    """3-way merge: baseline ↔ current ↔ work.

    - baseline: snapshot taken at work start (common ancestor).
    - current : Org IA right now.
    - work    : working copy being merged back.

    Conflict semantics:
      Same slug modified differently in BOTH current and work since baseline → conflict.

    Non-conflict cases (winner picked deterministically):
      - Only work changed   → fast-forward to work.
      - Only current changed → keep current.
      - Both moved to the same content → use it.
      - One side added / removed while other unchanged → take that change.

    dry_run=True → compute changes only, no writes.
    dry_run=False → write merged IA to `dest` (required). Caller is
                    responsible for git commit / user confirmation.

    Audit R-2 mitigation: equality uses canonical JSON for manifest and
    frontmatter, raw string for notes body — so reformatted JSON or
    re-ordered YAML keys do NOT produce false conflicts.
    """
    baseline = Path(baseline)
    current = Path(current)
    work = Path(work)

    if not dry_run and dest is None:
        raise ValueError("dest is required when dry_run=False (apply mode)")

    def _load_or_none(p: Path) -> Optional[IADocument]:
        if not p.exists() or not (p / "manifest.json").is_file():
            return None
        return load_ia(p)

    base_ia = _load_or_none(baseline)
    cur_ia = _load_or_none(current)
    work_ia = _load_or_none(work)

    # Collect all slugs across the three sides
    all_slugs: set = set()
    for ia_doc in (base_ia, cur_ia, work_ia):
        if ia_doc is None:
            continue
        for entry in ia_doc.manifest.get("pages", []) or []:
            if isinstance(entry.get("slug"), str):
                all_slugs.add(entry["slug"])
        for slug in ia_doc.pages.keys():
            all_slugs.add(slug)

    changes: list[MergeChange] = []
    conflicts: list[MergeChange] = []

    # Determine action + winner per slug
    winners: dict = {}  # slug → "work" | "current" | "either" | None | "conflict"
    for slug in sorted(all_slugs):
        b = _slug_signature(base_ia, slug)
        c = _slug_signature(cur_ia, slug)
        w = _slug_signature(work_ia, slug)
        action, winner = _classify(b, c, w)

        if action == "unchanged":
            winners[slug] = winner
            continue

        if action == "conflict":
            change = MergeChange(
                slug=slug,
                action="conflict",
                detail={"baseline": b, "current": c, "work": w},
            )
            changes.append(change)
            conflicts.append(change)
            winners[slug] = "conflict"
        else:
            change = MergeChange(
                slug=slug,
                action=action,
                detail={"winner": winner},
            )
            changes.append(change)
            winners[slug] = winner if action != "removed" else None

    applied = False
    dest_dir: Optional[Path] = None

    if not dry_run:
        dest_dir = Path(dest)
        if dest_dir.exists():
            shutil.rmtree(dest_dir)
        dest_dir.mkdir(parents=True)
        (dest_dir / "pages").mkdir(exist_ok=True)

        def _entry_map(ia_doc: Optional[IADocument]) -> dict:
            if ia_doc is None:
                return {}
            return {
                e.get("slug"): e
                for e in ia_doc.manifest.get("pages", []) or []
                if isinstance(e.get("slug"), str)
            }

        cur_entries = _entry_map(cur_ia)
        work_entries = _entry_map(work_ia)
        base_entries = _entry_map(base_ia)

        # Project name resolution: prefer work, then current, then base.
        project_name = ""
        for ia_doc in (work_ia, cur_ia, base_ia):
            if ia_doc and ia_doc.manifest.get("project"):
                project_name = ia_doc.manifest["project"]
                break

        merged_pages = []
        for slug in sorted(winners.keys()):
            winner = winners[slug]
            if winner is None:
                continue  # removed

            # For "either" or "conflict", prefer work content (caller resolves
            # conflicts post-merge).
            if winner == "either":
                source_ia = work_ia or cur_ia or base_ia
                source_entries = (
                    work_entries if work_ia else (cur_entries if cur_ia else base_entries)
                )
            elif winner == "conflict":
                source_ia = work_ia or cur_ia
                source_entries = work_entries if work_ia else cur_entries
            elif winner == "work":
                source_ia = work_ia
                source_entries = work_entries
            elif winner == "current":
                source_ia = cur_ia
                source_entries = cur_entries
            else:
                continue

            entry = source_entries.get(slug)
            if entry:
                merged_pages.append(entry)
            if source_ia:
                page = source_ia.pages.get(slug)
                if page and page.detail_path.is_file():
                    shutil.copy2(page.detail_path, dest_dir / "pages" / f"{slug}.md")

        merged_manifest = {
            "version": MANIFEST_VERSION,
            "project": project_name,
            "pages": merged_pages,
        }
        (dest_dir / "manifest.json").write_text(
            json.dumps(merged_manifest, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        # shared.json: prefer work, fall back to current, then base.
        shared_data: dict = {}
        for ia_doc in (work_ia, cur_ia, base_ia):
            if ia_doc and ia_doc.shared:
                shared_data = ia_doc.shared
                break
        (dest_dir / "shared.json").write_text(
            json.dumps(shared_data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        applied = True

    return MergeResult(
        changes=changes,
        conflicts=conflicts,
        applied=applied,
        dest_dir=dest_dir,
    )


def list_pages_in_scope(
    work_ia: Path,
    *,
    slugs: Optional[list] = None,
) -> list:
    """Return PageInfo list for pages in `work_ia` (filtered by `slugs` if given).

    `slugs=None` returns all pages. Unknown slugs in the filter are silently
    skipped (no error — keeps caller code simple when constructing filters).
    """
    doc = load_ia(work_ia)
    results = []
    if slugs is None:
        target_slugs = list(doc.pages.keys())
    else:
        target_slugs = [s for s in slugs if s in doc.pages]
    for slug in target_slugs:
        page = doc.pages[slug]
        results.append(
            PageInfo(
                slug=page.slug,
                route=page.route,
                title=page.title,
                detail_path=page.detail_path,
                role=page.role,
            )
        )
    return results


# ─────────────────────────────────────────────────────────────────────
# CLI entry — invoked by jarfis_cli.py
# ─────────────────────────────────────────────────────────────────────


def _emit_snapshot(args) -> int:
    try:
        result = snapshot_org_ia(
            args.src,
            args.dest,
            create_empty_if_missing=args.create_empty_if_missing,
        )
    except FileNotFoundError as exc:
        json_error(str(exc))
        return 1  # unreachable — json_error exits
    json_output(
        {
            "src": str(result.src),
            "dest": str(result.dest),
            "files_copied": result.files_copied,
            "pages_count": result.pages_count,
            "created_empty": result.created_empty,
        }
    )
    return 0


def _emit_validate(args) -> int:
    strict = not args.non_strict
    result = validate_ia(args.ia_dir, strict=strict)
    payload = {
        "valid": result.valid,
        "errors": result.errors,
        "warnings": result.warnings,
        "rules_checked": result.rules_checked,
    }
    if not result.valid:
        # Print JSON to stdout (caller can still parse) then exit 2.
        print(json.dumps(payload, ensure_ascii=False))
        sys.exit(2)
    json_output(payload)
    return 0


def _emit_merge(args) -> int:
    try:
        result = merge_3way(
            args.baseline,
            args.current,
            args.work,
            dry_run=args.dry_run,
            dest=args.dest,
        )
    except ValueError as exc:
        json_error(str(exc))
        return 1
    json_output(
        {
            "changes": [
                {"slug": ch.slug, "action": ch.action, "detail": ch.detail}
                for ch in result.changes
            ],
            "conflicts": [
                {"slug": ch.slug, "action": ch.action, "detail": ch.detail}
                for ch in result.conflicts
            ],
            "applied": result.applied,
            "dest_dir": str(result.dest_dir) if result.dest_dir else None,
        }
    )
    return 0


def _emit_list_pages(args) -> int:
    slugs_filter = None
    if args.slugs:
        slugs_filter = [s.strip() for s in args.slugs.split(",") if s.strip()]
    try:
        pages = list_pages_in_scope(args.work, slugs=slugs_filter)
    except FileNotFoundError as exc:
        json_error(str(exc))
        return 1
    json_output(
        {
            "count": len(pages),
            "pages": [
                {
                    "slug": p.slug,
                    "route": p.route,
                    "title": p.title,
                    "detail_path": str(p.detail_path),
                    "role": p.role,
                }
                for p in pages
            ],
        }
    )
    return 0


def main(argv) -> int:
    """jarfis_cli.py entry — dispatches `jarfis ia <subcmd> ...`.

    Subcommands: snapshot | validate | merge | list-pages
    """
    parser = argparse.ArgumentParser(prog="jarfis ia", add_help=True)
    sub = parser.add_subparsers(dest="cmd")

    p_snap = sub.add_parser("snapshot", help="Read-only copy of Org IA → baseline.")
    p_snap.add_argument("--src", required=True, type=Path)
    p_snap.add_argument("--dest", required=True, type=Path)
    p_snap.add_argument("--create-empty-if-missing", action="store_true")

    p_val = sub.add_parser("validate", help="Run R1~R12 validation.")
    p_val.add_argument("ia_dir", type=Path)
    p_val.add_argument("--non-strict", action="store_true")

    p_mrg = sub.add_parser("merge", help="3-way merge baseline ↔ current ↔ work.")
    p_mrg.add_argument("--baseline", required=True, type=Path)
    p_mrg.add_argument("--current", required=True, type=Path)
    p_mrg.add_argument("--work", required=True, type=Path)
    group = p_mrg.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true")
    group.add_argument("--apply", action="store_true")
    p_mrg.add_argument("--dest", type=Path)

    p_lp = sub.add_parser("list-pages", help="Query pages from work IA.")
    p_lp.add_argument("--work", required=True, type=Path)
    p_lp.add_argument("--slugs", default=None, help="comma-separated slug filter")

    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        # argparse uses code 2 for arg errors — surface a JSON error too.
        if exc.code not in (0, None):
            json_error(
                "Usage: jarfis ia <snapshot|validate|merge|list-pages> [args...]"
            )
        raise

    if args.cmd is None:
        json_error(
            "Usage: jarfis ia <snapshot|validate|merge|list-pages> [args...]"
        )
        return 1  # unreachable

    # Translate apply flag → dry_run=False (mutually exclusive with --dry-run).
    if args.cmd == "merge":
        args.dry_run = bool(args.dry_run) and not bool(args.apply)
        if args.apply:
            args.dry_run = False

    handlers = {
        "snapshot": _emit_snapshot,
        "validate": _emit_validate,
        "merge": _emit_merge,
        "list-pages": _emit_list_pages,
    }
    handler = handlers.get(args.cmd)
    if handler is None:
        json_error(f"Unknown ia subcommand: {args.cmd}")
        return 1
    return handler(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
