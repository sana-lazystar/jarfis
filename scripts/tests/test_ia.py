"""Tests for jarfis.ia — IA snapshot/load/validate/merge/list-pages module.

Coverage targets (per ia-as-po-ssot-v2-spine Stage 1 spec):
  - TestLoadIA (4 cases)            — Critic #1: load_ia primitive
  - TestSnapshotOrgIA (4 cases)     — Critic #2: cold-start contract (D10)
  - TestValidateIA (15 cases)       — R1~R12 + Audit R-3 (max_depth warning)
  - TestMerge3Way (8 cases)         — 3-way confirm-merge (D4)
  - TestListPagesInScope (3 cases)
  - TestDispatcher (4 cases)        — CLI entry

All tests use tmp_path fixtures — no env-var setup needed.
"""

import json
import sys

import pytest
import yaml

from jarfis import ia


# ─────────────────────────────────────────────────────────────────────
# Helpers — build IA dirs / pages
# ─────────────────────────────────────────────────────────────────────


def _write_page_md(pages_dir, slug, frontmatter, body="## Notes\n\n"):
    """Write pages/{slug}.md with YAML frontmatter."""
    fm_yaml = yaml.safe_dump(frontmatter, allow_unicode=True, sort_keys=False)
    (pages_dir / f"{slug}.md").write_text(
        f"---\n{fm_yaml}---\n\n{body}", encoding="utf-8"
    )


def _build_ia(
    root,
    name,
    pages_data,
    *,
    version="2.0",
    project="test-project",
    shared=None,
    skip_shared=False,
):
    """Create an IA directory with manifest + pages + shared.

    pages_data: list of dicts. Required keys: slug, route, title, role.
    Optional: parent, depth, detail (path override), status, extra_fm,
              skip_md (don't write detail file), skip_manifest_entry.
    """
    ia_dir = root / name
    ia_dir.mkdir(parents=True, exist_ok=True)
    pages_dir = ia_dir / "pages"
    pages_dir.mkdir(exist_ok=True)

    manifest_pages = []
    for p in pages_data:
        slug = p["slug"]
        depth = p.get("depth", 1)
        parent = p.get("parent")
        if not p.get("skip_manifest_entry"):
            manifest_pages.append(
                {
                    "slug": slug,
                    "route": p["route"],
                    "title": p["title"],
                    "role": p["role"],
                    "parent": parent,
                    "depth": depth,
                    "detail": p.get("detail", f"pages/{slug}.md"),
                    "status": p.get("status", "active"),
                    "created_in": p.get("created_in", "test-work"),
                    "last_updated_in": p.get("last_updated_in", "test-work"),
                }
            )
        if p.get("skip_md"):
            continue
        # Frontmatter — defaults then override
        fm = {
            "slug": p.get("fm_slug_override", slug),
            "route": p["route"],
            "title": p["title"],
            "role": p["role"],
            "parent": parent,
            "depth": depth,
        }
        # Optional default fields
        if "purpose" in p:
            fm["purpose"] = p["purpose"]
        if "navigation" in p:
            fm["navigation"] = p["navigation"]
        if p.get("extra_fm"):
            fm.update(p["extra_fm"])
        if "drop_fields" in p:
            for f in p["drop_fields"]:
                fm.pop(f, None)
        _write_page_md(pages_dir, slug, fm, body=p.get("notes_body", "## Notes\n\n"))

    manifest = {
        "version": version,
        "project": project,
        "pages": manifest_pages,
    }
    (ia_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    if not skip_shared:
        shared_data = shared if shared is not None else {}
        (ia_dir / "shared.json").write_text(
            json.dumps(shared_data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    return ia_dir


# ─────────────────────────────────────────────────────────────────────
# TestLoadIA — Critic #1
# ─────────────────────────────────────────────────────────────────────


class TestLoadIA:
    def test_load_valid_ia(self, tmp_path):
        ia_dir = _build_ia(
            tmp_path,
            "ia",
            [
                {
                    "slug": "home",
                    "route": "/",
                    "title": "Home",
                    "role": "public",
                    "depth": 0,
                },
                {
                    "slug": "dashboard",
                    "route": "/dashboard",
                    "title": "Dashboard",
                    "role": "auth",
                    "depth": 1,
                },
            ],
        )
        doc = ia.load_ia(ia_dir)
        assert doc.manifest["version"] == "2.0"
        assert "home" in doc.pages
        assert "dashboard" in doc.pages
        page = doc.pages["dashboard"]
        assert page.slug == "dashboard"
        assert page.route == "/dashboard"
        assert page.title == "Dashboard"
        assert page.role == "auth"
        assert page.depth == 1
        assert page.detail_path.is_file()
        assert "## Notes" in page.notes_body
        # shared loads as empty dict
        assert doc.shared == {}

    def test_load_missing_manifest_raises(self, tmp_path):
        (tmp_path / "ia").mkdir()
        with pytest.raises(FileNotFoundError):
            ia.load_ia(tmp_path / "ia")

    def test_load_orphan_page_returns_warning(self, tmp_path):
        """Orphan pages/*.md (no manifest entry) should still load,
        but validate_ia will flag them (R9). load_ia is lenient."""
        ia_dir = _build_ia(
            tmp_path,
            "ia",
            [{"slug": "home", "route": "/", "title": "Home", "role": "public"}],
        )
        # Add an orphan md file
        _write_page_md(
            ia_dir / "pages",
            "orphan",
            {
                "slug": "orphan",
                "route": "/orphan",
                "title": "Orphan",
                "role": "public",
                "parent": None,
                "depth": 1,
            },
        )
        doc = ia.load_ia(ia_dir)
        # Only manifest-listed pages loaded into pages dict
        assert "home" in doc.pages
        assert "orphan" not in doc.pages
        # validate_ia catches it
        result = ia.validate_ia(ia_dir)
        assert any("R9" in e for e in result.errors)

    def test_load_shared_optional(self, tmp_path):
        ia_dir = _build_ia(
            tmp_path,
            "ia",
            [{"slug": "home", "route": "/", "title": "Home", "role": "public"}],
            skip_shared=True,
        )
        doc = ia.load_ia(ia_dir)
        assert doc.shared == {}


# ─────────────────────────────────────────────────────────────────────
# TestSnapshotOrgIA — Critic #2 (D10 cold-start)
# ─────────────────────────────────────────────────────────────────────


class TestSnapshotOrgIA:
    def test_snapshot_copies_all_files(self, tmp_path):
        src = _build_ia(
            tmp_path,
            "src",
            [
                {"slug": "home", "route": "/", "title": "Home", "role": "public"},
                {"slug": "about", "route": "/about", "title": "About", "role": "public"},
            ],
        )
        dest = tmp_path / "baseline"
        result = ia.snapshot_org_ia(src, dest)
        assert dest.is_dir()
        assert (dest / "manifest.json").is_file()
        assert (dest / "pages" / "home.md").is_file()
        assert (dest / "pages" / "about.md").is_file()
        assert (dest / "shared.json").is_file()
        assert result.created_empty is False
        assert result.pages_count == 2
        assert result.files_copied >= 4  # manifest, shared, 2 pages

    def test_snapshot_src_missing_raises_by_default(self, tmp_path):
        src = tmp_path / "nonexistent"
        dest = tmp_path / "baseline"
        with pytest.raises(FileNotFoundError):
            ia.snapshot_org_ia(src, dest)

    def test_snapshot_create_empty_if_missing(self, tmp_path):
        """Critic #2 fix — D10 cold-start support."""
        src = tmp_path / "nonexistent"
        dest = tmp_path / "baseline"
        result = ia.snapshot_org_ia(src, dest, create_empty_if_missing=True)
        assert result.created_empty is True
        assert dest.is_dir()
        assert (dest / "manifest.json").is_file()
        assert (dest / "pages").is_dir()
        # Empty manifest content
        manifest = json.loads((dest / "manifest.json").read_text())
        assert manifest["version"] == "2.0"
        assert manifest["pages"] == []

    def test_snapshot_preserves_content(self, tmp_path):
        src = _build_ia(
            tmp_path,
            "src",
            [
                {
                    "slug": "home",
                    "route": "/",
                    "title": "Home",
                    "role": "public",
                    "extra_fm": {"purpose": "랜딩 페이지"},
                }
            ],
        )
        dest = tmp_path / "baseline"
        ia.snapshot_org_ia(src, dest)
        body = (dest / "pages" / "home.md").read_text(encoding="utf-8")
        assert "랜딩 페이지" in body


# ─────────────────────────────────────────────────────────────────────
# TestValidateIA — R1~R12 + Audit R-3
# ─────────────────────────────────────────────────────────────────────


class TestValidateIA:
    def test_r1_manifest_missing(self, tmp_path):
        ia_dir = tmp_path / "ia"
        ia_dir.mkdir()
        result = ia.validate_ia(ia_dir)
        assert result.valid is False
        assert any("R1" in e for e in result.errors)

    def test_r2_version_mismatch(self, tmp_path):
        ia_dir = _build_ia(
            tmp_path,
            "ia",
            [{"slug": "home", "route": "/", "title": "Home", "role": "public"}],
            version="1.0",
        )
        result = ia.validate_ia(ia_dir)
        assert result.valid is False
        assert any("R2" in e for e in result.errors)

    def test_r3_invalid_slug_regex(self, tmp_path):
        ia_dir = _build_ia(
            tmp_path,
            "ia",
            [
                {
                    "slug": "BadSlug",
                    "route": "/bad",
                    "title": "Bad",
                    "role": "public",
                }
            ],
        )
        result = ia.validate_ia(ia_dir)
        assert any("R3" in e for e in result.errors)

    def test_r4_duplicate_slug(self, tmp_path):
        # Build with one valid page then manually corrupt manifest
        ia_dir = _build_ia(
            tmp_path,
            "ia",
            [{"slug": "home", "route": "/", "title": "Home", "role": "public"}],
        )
        manifest = json.loads((ia_dir / "manifest.json").read_text())
        manifest["pages"].append(
            {
                "slug": "home",
                "route": "/dup",
                "title": "Dup",
                "role": "public",
                "parent": None,
                "depth": 1,
                "detail": "pages/home.md",
            }
        )
        (ia_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
        result = ia.validate_ia(ia_dir)
        assert any("R4" in e for e in result.errors)

    def test_r5_duplicate_route(self, tmp_path):
        ia_dir = _build_ia(
            tmp_path,
            "ia",
            [
                {"slug": "home", "route": "/", "title": "Home", "role": "public"},
                {"slug": "landing", "route": "/", "title": "Landing", "role": "public"},
            ],
        )
        result = ia.validate_ia(ia_dir)
        assert any("R5" in e for e in result.errors)

    def test_r6_invalid_parent_ref(self, tmp_path):
        ia_dir = _build_ia(
            tmp_path,
            "ia",
            [
                {
                    "slug": "child",
                    "route": "/child",
                    "title": "Child",
                    "role": "public",
                    "parent": "ghost-parent",
                }
            ],
        )
        result = ia.validate_ia(ia_dir)
        assert any("R6" in e for e in result.errors)

    def test_r7_missing_detail_file(self, tmp_path):
        ia_dir = _build_ia(
            tmp_path,
            "ia",
            [
                {
                    "slug": "home",
                    "route": "/",
                    "title": "Home",
                    "role": "public",
                    "skip_md": True,
                }
            ],
        )
        result = ia.validate_ia(ia_dir)
        assert any("R7" in e for e in result.errors)

    def test_r8_frontmatter_slug_mismatch(self, tmp_path):
        ia_dir = _build_ia(
            tmp_path,
            "ia",
            [
                {
                    "slug": "home",
                    "route": "/",
                    "title": "Home",
                    "role": "public",
                    "fm_slug_override": "different",
                }
            ],
        )
        result = ia.validate_ia(ia_dir)
        assert any("R8" in e for e in result.errors)

    def test_r9_orphan_page_md(self, tmp_path):
        ia_dir = _build_ia(
            tmp_path,
            "ia",
            [{"slug": "home", "route": "/", "title": "Home", "role": "public"}],
        )
        _write_page_md(
            ia_dir / "pages",
            "orphan",
            {
                "slug": "orphan",
                "route": "/orphan",
                "title": "Orphan",
                "role": "public",
                "parent": None,
                "depth": 1,
            },
        )
        result = ia.validate_ia(ia_dir)
        assert any("R9" in e for e in result.errors)

    def test_r10_missing_required_field_strict(self, tmp_path):
        ia_dir = _build_ia(
            tmp_path,
            "ia",
            [
                {
                    "slug": "home",
                    "route": "/",
                    "title": "Home",
                    "role": "public",
                    "drop_fields": ["title"],
                }
            ],
        )
        # strict=True (default)
        result = ia.validate_ia(ia_dir, strict=True)
        assert any("R10" in e for e in result.errors)
        # strict=False — R10 should not fail
        result_relax = ia.validate_ia(ia_dir, strict=False)
        assert not any("R10" in e for e in result_relax.errors)

    def test_r11_invalid_navigation_ref(self, tmp_path):
        ia_dir = _build_ia(
            tmp_path,
            "ia",
            [
                {
                    "slug": "home",
                    "route": "/",
                    "title": "Home",
                    "role": "public",
                    "navigation": {"entry_from": ["ghost"], "exits_to": []},
                }
            ],
        )
        result = ia.validate_ia(ia_dir, strict=True)
        assert any("R11" in e for e in result.errors)

    def test_r12_parent_cycle_detected(self, tmp_path):
        """Critic #3 — ERROR on cycle."""
        ia_dir = _build_ia(
            tmp_path,
            "ia",
            [
                {
                    "slug": "a",
                    "route": "/a",
                    "title": "A",
                    "role": "public",
                    "parent": "c",  # cycle: a → c → b → a
                },
                {
                    "slug": "b",
                    "route": "/b",
                    "title": "B",
                    "role": "public",
                    "parent": "a",
                },
                {
                    "slug": "c",
                    "route": "/c",
                    "title": "C",
                    "role": "public",
                    "parent": "b",
                },
            ],
        )
        result = ia.validate_ia(ia_dir)
        assert any("R12" in e for e in result.errors)

    def test_r12_max_depth_warning(self, tmp_path):
        """Audit R-3 — WARNING only, not error. depth > 8 (default)."""
        pages = []
        prev = None
        for i in range(10):  # chain of 10 — exceeds 8
            slug = f"p{i}"
            pages.append(
                {
                    "slug": slug,
                    "route": f"/{slug}",
                    "title": slug,
                    "role": "public",
                    "parent": prev,
                }
            )
            prev = slug
        ia_dir = _build_ia(tmp_path, "ia", pages)
        result = ia.validate_ia(ia_dir, strict=True)
        # R12 cycle errors must NOT be present
        assert not any(
            "R12" in e and "cycle" in e.lower() for e in result.errors
        )
        # But a warning must mention R12 depth
        assert any("R12" in w for w in result.warnings)

    def test_r12_max_depth_under_threshold(self, tmp_path):
        """depth <= 8 → no warning."""
        pages = []
        prev = None
        for i in range(5):
            slug = f"p{i}"
            pages.append(
                {
                    "slug": slug,
                    "route": f"/{slug}",
                    "title": slug,
                    "role": "public",
                    "parent": prev,
                }
            )
            prev = slug
        ia_dir = _build_ia(tmp_path, "ia", pages)
        result = ia.validate_ia(ia_dir, strict=True)
        assert not any("R12" in w for w in result.warnings)

    def test_valid_ia_passes_all(self, tmp_path):
        ia_dir = _build_ia(
            tmp_path,
            "ia",
            [
                {
                    "slug": "home",
                    "route": "/",
                    "title": "Home",
                    "role": "public",
                    "depth": 0,
                    "navigation": {"entry_from": [], "exits_to": ["dashboard"]},
                },
                {
                    "slug": "dashboard",
                    "route": "/dashboard",
                    "title": "Dashboard",
                    "role": "auth",
                    "parent": "home",
                    "depth": 1,
                    "navigation": {"entry_from": ["home"], "exits_to": []},
                },
            ],
        )
        result = ia.validate_ia(ia_dir, strict=True)
        assert result.valid is True
        assert result.errors == []
        # All 12 rules checked
        assert set(result.rules_checked) >= {f"R{i}" for i in range(1, 13)}


# ─────────────────────────────────────────────────────────────────────
# TestMerge3Way
# ─────────────────────────────────────────────────────────────────────


class TestMerge3Way:
    def _seed_three(self, tmp_path, baseline_pages, current_pages, work_pages):
        b = _build_ia(tmp_path, "baseline", baseline_pages)
        c = _build_ia(tmp_path, "current", current_pages)
        w = _build_ia(tmp_path, "work", work_pages)
        return b, c, w

    def test_no_changes(self, tmp_path):
        pages = [
            {"slug": "home", "route": "/", "title": "Home", "role": "public"}
        ]
        b, c, w = self._seed_three(tmp_path, pages, pages, pages)
        result = ia.merge_3way(b, c, w, dry_run=True)
        # No conflicts, no real changes
        assert result.conflicts == []
        # All changes (if any) should be non-conflict
        for ch in result.changes:
            assert ch.action != "conflict"

    def test_work_only_change_fast_forward(self, tmp_path):
        base = [{"slug": "home", "route": "/", "title": "Home", "role": "public"}]
        work = [
            {
                "slug": "home",
                "route": "/",
                "title": "Home v2",
                "role": "public",
            }
        ]
        b, c, w = self._seed_three(tmp_path, base, base, work)
        result = ia.merge_3way(b, c, w, dry_run=True)
        assert result.conflicts == []
        assert any(
            ch.slug == "home" and ch.action == "modified" for ch in result.changes
        )

    def test_current_only_change_kept(self, tmp_path):
        base = [{"slug": "home", "route": "/", "title": "Home", "role": "public"}]
        current = [
            {"slug": "home", "route": "/", "title": "Home v3", "role": "public"}
        ]
        b, c, w = self._seed_three(tmp_path, base, current, base)
        result = ia.merge_3way(b, c, w, dry_run=True)
        assert result.conflicts == []
        # current changed but work didn't — should still be a "modified" change
        # because the merge picks current.
        actions = [ch.action for ch in result.changes if ch.slug == "home"]
        assert "modified" in actions

    def test_conflict_same_slug_both_modified(self, tmp_path):
        base = [{"slug": "home", "route": "/", "title": "Home", "role": "public"}]
        current = [
            {"slug": "home", "route": "/", "title": "Home A", "role": "public"}
        ]
        work = [
            {"slug": "home", "route": "/", "title": "Home B", "role": "public"}
        ]
        b, c, w = self._seed_three(tmp_path, base, current, work)
        result = ia.merge_3way(b, c, w, dry_run=True)
        assert len(result.conflicts) >= 1
        assert any(
            ch.slug == "home" and ch.action == "conflict" for ch in result.conflicts
        )

    def test_added_in_work(self, tmp_path):
        base = [{"slug": "home", "route": "/", "title": "Home", "role": "public"}]
        work = base + [
            {"slug": "new", "route": "/new", "title": "New", "role": "public"}
        ]
        b, c, w = self._seed_three(tmp_path, base, base, work)
        result = ia.merge_3way(b, c, w, dry_run=True)
        assert any(
            ch.slug == "new" and ch.action == "added" for ch in result.changes
        )
        assert result.conflicts == []

    def test_removed_in_work(self, tmp_path):
        base = [
            {"slug": "home", "route": "/", "title": "Home", "role": "public"},
            {"slug": "old", "route": "/old", "title": "Old", "role": "public"},
        ]
        work = [base[0]]
        b, c, w = self._seed_three(tmp_path, base, base, work)
        result = ia.merge_3way(b, c, w, dry_run=True)
        assert any(
            ch.slug == "old" and ch.action == "removed" for ch in result.changes
        )

    def test_dry_run_no_write(self, tmp_path):
        base = [{"slug": "home", "route": "/", "title": "Home", "role": "public"}]
        work = [
            {"slug": "home", "route": "/", "title": "Home v2", "role": "public"}
        ]
        b, c, w = self._seed_three(tmp_path, base, base, work)
        dest = tmp_path / "merged"
        result = ia.merge_3way(b, c, w, dry_run=True, dest=dest)
        assert result.applied is False
        # dest must not be created
        assert not dest.exists()

    def test_apply_writes_to_dest(self, tmp_path):
        base = [{"slug": "home", "route": "/", "title": "Home", "role": "public"}]
        work = [
            {"slug": "home", "route": "/", "title": "Home v2", "role": "public"}
        ]
        b, c, w = self._seed_three(tmp_path, base, base, work)
        dest = tmp_path / "merged"
        result = ia.merge_3way(b, c, w, dry_run=False, dest=dest)
        assert result.applied is True
        assert dest.is_dir()
        assert (dest / "manifest.json").is_file()
        merged_manifest = json.loads((dest / "manifest.json").read_text())
        # work won — title is v2
        home_entry = next(
            e for e in merged_manifest["pages"] if e["slug"] == "home"
        )
        assert home_entry["title"] == "Home v2"


# ─────────────────────────────────────────────────────────────────────
# TestListPagesInScope
# ─────────────────────────────────────────────────────────────────────


class TestListPagesInScope:
    def test_no_filter_returns_all(self, tmp_path):
        ia_dir = _build_ia(
            tmp_path,
            "ia",
            [
                {"slug": "home", "route": "/", "title": "Home", "role": "public"},
                {
                    "slug": "dashboard",
                    "route": "/dashboard",
                    "title": "Dashboard",
                    "role": "auth",
                },
            ],
        )
        pages = ia.list_pages_in_scope(ia_dir)
        slugs = sorted(p.slug for p in pages)
        assert slugs == ["dashboard", "home"]
        # PageInfo fields
        home = next(p for p in pages if p.slug == "home")
        assert home.route == "/"
        assert home.title == "Home"
        assert home.role == "public"
        assert home.detail_path.is_file()

    def test_slugs_filter(self, tmp_path):
        ia_dir = _build_ia(
            tmp_path,
            "ia",
            [
                {"slug": "home", "route": "/", "title": "Home", "role": "public"},
                {
                    "slug": "dashboard",
                    "route": "/dashboard",
                    "title": "Dashboard",
                    "role": "auth",
                },
            ],
        )
        pages = ia.list_pages_in_scope(ia_dir, slugs=["home"])
        assert len(pages) == 1
        assert pages[0].slug == "home"

    def test_invalid_slug_filter_skipped(self, tmp_path):
        ia_dir = _build_ia(
            tmp_path,
            "ia",
            [{"slug": "home", "route": "/", "title": "Home", "role": "public"}],
        )
        pages = ia.list_pages_in_scope(ia_dir, slugs=["home", "ghost"])
        # Invalid slug skipped; valid one returned
        assert len(pages) == 1
        assert pages[0].slug == "home"


# ─────────────────────────────────────────────────────────────────────
# TestDispatcher — CLI entry
# ─────────────────────────────────────────────────────────────────────


class TestDispatcher:
    def test_dispatch_snapshot(self, tmp_path, capsys):
        src = _build_ia(
            tmp_path,
            "src",
            [{"slug": "home", "route": "/", "title": "Home", "role": "public"}],
        )
        dest = tmp_path / "baseline"
        ia.main(["snapshot", "--src", str(src), "--dest", str(dest)])
        out = json.loads(capsys.readouterr().out)
        assert out["created_empty"] is False
        assert out["pages_count"] == 1
        assert dest.is_dir()

    def test_dispatch_snapshot_cold_start(self, tmp_path, capsys):
        """--create-empty-if-missing path."""
        src = tmp_path / "nonexistent"
        dest = tmp_path / "baseline"
        ia.main(
            [
                "snapshot",
                "--src",
                str(src),
                "--dest",
                str(dest),
                "--create-empty-if-missing",
            ]
        )
        out = json.loads(capsys.readouterr().out)
        assert out["created_empty"] is True

    def test_dispatch_validate(self, tmp_path, capsys):
        ia_dir = _build_ia(
            tmp_path,
            "ia",
            [{"slug": "home", "route": "/", "title": "Home", "role": "public"}],
        )
        ia.main(["validate", str(ia_dir)])
        out = json.loads(capsys.readouterr().out)
        assert out["valid"] is True
        assert "R1" in out["rules_checked"]

    def test_dispatch_validate_invalid_exits_nonzero(self, tmp_path, capsys):
        ia_dir = tmp_path / "empty"
        ia_dir.mkdir()
        with pytest.raises(SystemExit) as excinfo:
            ia.main(["validate", str(ia_dir)])
        assert excinfo.value.code != 0

    def test_dispatch_merge_dry_run(self, tmp_path, capsys):
        base = _build_ia(
            tmp_path,
            "baseline",
            [{"slug": "home", "route": "/", "title": "Home", "role": "public"}],
        )
        current = _build_ia(
            tmp_path,
            "current",
            [{"slug": "home", "route": "/", "title": "Home", "role": "public"}],
        )
        work = _build_ia(
            tmp_path,
            "work",
            [{"slug": "home", "route": "/", "title": "Home v2", "role": "public"}],
        )
        ia.main(
            [
                "merge",
                "--baseline",
                str(base),
                "--current",
                str(current),
                "--work",
                str(work),
                "--dry-run",
            ]
        )
        out = json.loads(capsys.readouterr().out)
        assert out["applied"] is False
        assert any(
            ch["slug"] == "home" and ch["action"] == "modified"
            for ch in out["changes"]
        )

    def test_dispatch_list_pages(self, tmp_path, capsys):
        ia_dir = _build_ia(
            tmp_path,
            "work",
            [
                {"slug": "home", "route": "/", "title": "Home", "role": "public"},
                {"slug": "about", "route": "/about", "title": "About", "role": "public"},
            ],
        )
        ia.main(["list-pages", "--work", str(ia_dir)])
        out = json.loads(capsys.readouterr().out)
        assert out["count"] == 2
        slugs = sorted(p["slug"] for p in out["pages"])
        assert slugs == ["about", "home"]
