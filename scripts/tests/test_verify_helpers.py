"""Tests for jarfis.verify_helpers — Stage 3 IA helpers + jarfis.ia.probe.

Covers the 5 new helpers added in Stage 3 of ia-as-po-ssot-v2-spine:
  * check_ia_pages_match_tasks   (L2 mapping)
  * check_ia_pages_match_design  (L3 mapping, figma mode)
  * check_ia_pages_match_review  (Phase 5 coverage)
  * check_ia_merge_artifacts     (Phase 6 Org IA evidence)
  * check_fe_routes_match_ia     (R-8 best-effort warning)

Plus ia.probe (Resume Dispatch IA-missing detector — F3 dialectic absorption).
"""

import json
import os
import subprocess
from pathlib import Path

import pytest

from jarfis import ia, verify_helpers as vh


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _write(path: Path, text: str = "") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _make_ia(ia_dir: Path, slugs, routes=None) -> Path:
    """Build a minimal IA dir with manifest.json + pages/{slug}.md.

    routes: optional mapping {slug: route}. Default: /{slug}.
    """
    ia_dir.mkdir(parents=True, exist_ok=True)
    (ia_dir / "pages").mkdir(exist_ok=True)
    pages = []
    for slug in slugs:
        route = (routes or {}).get(slug, f"/{slug}")
        pages.append(
            {
                "slug": slug,
                "route": route,
                "title": slug.replace("-", " ").title(),
                "role": "public",
                "parent": None,
                "depth": 1,
                "detail": f"pages/{slug}.md",
            }
        )
        (ia_dir / "pages" / f"{slug}.md").write_text(
            f"---\nslug: {slug}\nroute: {route}\ntitle: {slug}\nrole: public\ndepth: 1\n---\n\n## Notes\n",
            encoding="utf-8",
        )
    manifest = {"version": "2.0", "project": "test", "pages": pages}
    (ia_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return ia_dir


# ===========================================================================
# check_ia_pages_match_tasks (L2 mapping)
# ===========================================================================
class TestCheckIAPagesMatchTasks:
    def test_pass_when_all_referenced_slugs_have_pages(self, tmp_path):
        ia_dir = _make_ia(tmp_path / "ia", ["home", "about"])
        tasks_md = tmp_path / "tasks.md"
        tasks_md.write_text(
            "## Frontend Tasks — admin-fe\n"
            "- [ ] FE-1 implement `home`\n"
            "- [ ] FE-2 implement `about`\n",
            encoding="utf-8",
        )
        assert vh.check_ia_pages_match_tasks(ia_dir, tasks_md) == []

    def test_fail_when_referenced_slug_has_no_ia_page(self, tmp_path):
        ia_dir = _make_ia(tmp_path / "ia", ["home", "about"])
        tasks_md = tmp_path / "tasks.md"
        tasks_md.write_text(
            "- [ ] FE-1 work on `home`\n"
            "- [ ] FE-2 work on `contact`\n",
            encoding="utf-8",
        )
        missing = vh.check_ia_pages_match_tasks(ia_dir, tasks_md)
        assert any("contact" in m for m in missing), missing

    def test_extra_pages_in_ia_are_ok(self, tmp_path):
        # IA has pages [home, about, contact]; tasks only reference home.
        ia_dir = _make_ia(tmp_path / "ia", ["home", "about", "contact"])
        tasks_md = tmp_path / "tasks.md"
        tasks_md.write_text("- [ ] FE-1 implement `home`\n", encoding="utf-8")
        assert vh.check_ia_pages_match_tasks(ia_dir, tasks_md) == []

    def test_missing_tasks_file_returns_empty(self, tmp_path):
        ia_dir = _make_ia(tmp_path / "ia", ["home"])
        assert vh.check_ia_pages_match_tasks(ia_dir, tmp_path / "nope.md") == []

    def test_missing_manifest_returns_empty(self, tmp_path):
        ia_dir = tmp_path / "ia"
        ia_dir.mkdir()
        tasks_md = tmp_path / "tasks.md"
        tasks_md.write_text("- [ ] FE-1 work on `home`\n", encoding="utf-8")
        assert vh.check_ia_pages_match_tasks(ia_dir, tasks_md) == []


# ===========================================================================
# check_ia_pages_match_design (L3 mapping, figma mode)
# ===========================================================================
class TestCheckIAPagesMatchDesign:
    def test_pass_figma_1to1_mapping(self, tmp_path):
        ia_dir = _make_ia(tmp_path / "ia", ["home", "about"])
        design_dir = tmp_path / "design"
        for slug in ("home", "about"):
            d = design_dir / slug
            d.mkdir(parents=True)
            (d / "index.html").write_text("<html></html>")
        assert vh.check_ia_pages_match_design(ia_dir, design_dir, mode="figma") == []

    def test_fail_design_missing_ia_slug(self, tmp_path):
        ia_dir = _make_ia(tmp_path / "ia", ["home", "about"])
        design_dir = tmp_path / "design"
        d = design_dir / "home"
        d.mkdir(parents=True)
        (d / "index.html").write_text("<html></html>")
        # No design/about
        missing = vh.check_ia_pages_match_design(ia_dir, design_dir, mode="figma")
        assert any("about" in m for m in missing), missing

    def test_fail_design_extra_dir_not_in_ia(self, tmp_path):
        ia_dir = _make_ia(tmp_path / "ia", ["home"])
        design_dir = tmp_path / "design"
        for slug in ("home", "rogue"):
            d = design_dir / slug
            d.mkdir(parents=True)
            (d / "index.html").write_text("<html></html>")
        missing = vh.check_ia_pages_match_design(ia_dir, design_dir, mode="figma")
        assert any("rogue" in m for m in missing), missing

    def test_supplied_mode_returns_empty(self, tmp_path):
        # Even if mismatch exists, supplied mode short-circuits (defense in depth).
        ia_dir = _make_ia(tmp_path / "ia", ["home"])
        design_dir = tmp_path / "design"
        design_dir.mkdir()  # empty
        assert vh.check_ia_pages_match_design(ia_dir, design_dir, mode="supplied") == []


# ===========================================================================
# check_ia_pages_match_review (Phase 5 coverage)
# ===========================================================================
class TestCheckIAPagesMatchReview:
    def test_pass_all_slugs_mentioned(self, tmp_path):
        ia_dir = _make_ia(tmp_path / "ia", ["home", "about"])
        review_md = tmp_path / "review.md"
        review_md.write_text(
            "# Review\n\n### admin-fe\n\nReviewed pages: home, about.\n",
            encoding="utf-8",
        )
        assert vh.check_ia_pages_match_review(ia_dir, review_md) == []

    def test_pass_case_insensitive(self, tmp_path):
        ia_dir = _make_ia(tmp_path / "ia", ["home"])
        review_md = tmp_path / "review.md"
        review_md.write_text("# Review of HOME page\n", encoding="utf-8")
        assert vh.check_ia_pages_match_review(ia_dir, review_md) == []

    def test_fail_slug_missing_in_review(self, tmp_path):
        ia_dir = _make_ia(tmp_path / "ia", ["home", "about"])
        review_md = tmp_path / "review.md"
        review_md.write_text("Reviewed pages: home only.\n", encoding="utf-8")
        missing = vh.check_ia_pages_match_review(ia_dir, review_md)
        assert any("about" in m for m in missing), missing

    def test_missing_review_file_returns_empty(self, tmp_path):
        ia_dir = _make_ia(tmp_path / "ia", ["home"])
        assert vh.check_ia_pages_match_review(ia_dir, tmp_path / "nope.md") == []


# ===========================================================================
# check_ia_merge_artifacts (Phase 6 Org IA evidence)
# ===========================================================================
class TestCheckIAMergeArtifacts:
    def test_no_org_returns_empty(self, tmp_path):
        state = {"org": None, "work": {"name": "w1"}}
        docs = tmp_path / "docs"
        docs.mkdir()
        assert vh.check_ia_merge_artifacts(state, str(docs)) == []

    def test_org_wiki_absent_returns_empty(self, tmp_path):
        # Org registered but Stage 6 not done — wiki/PO/projects/<name>/ia missing.
        org_root = tmp_path / "org"
        (org_root / ".jarfis-org").mkdir(parents=True)
        state = {"org": {"name": "Org", "root": str(org_root)}, "work": {"name": "w1"}}
        docs = tmp_path / "docs"
        docs.mkdir()
        assert vh.check_ia_merge_artifacts(state, str(docs)) == []

    def test_merge_log_missing_returns_error(self, tmp_path):
        org_root = tmp_path / "org"
        org_ia = org_root / ".jarfis-org" / "wiki" / "PO" / "projects" / "w1" / "ia"
        _make_ia(org_ia, ["home"])
        # No merge.log
        state = {"org": {"name": "Org", "root": str(org_root)}, "work": {"name": "w1"}}
        docs = tmp_path / "docs"
        _make_ia(docs / "discovery" / "ia", ["home"])
        missing = vh.check_ia_merge_artifacts(state, str(docs))
        assert any("merge.log" in m for m in missing), missing

    def test_extra_slug_in_work_not_in_org_ia(self, tmp_path):
        org_root = tmp_path / "org"
        org_ia = org_root / ".jarfis-org" / "wiki" / "PO" / "projects" / "w1" / "ia"
        _make_ia(org_ia, ["home"])
        (org_ia / "merge.log").write_text("merged at 2026-05-11\n")
        state = {"org": {"name": "Org", "root": str(org_root)}, "work": {"name": "w1"}}
        docs = tmp_path / "docs"
        _make_ia(docs / "discovery" / "ia", ["home", "about"])
        missing = vh.check_ia_merge_artifacts(state, str(docs))
        # about exists in work IA but not in org IA → flagged
        assert any("about" in m for m in missing), missing


# ===========================================================================
# check_fe_routes_match_ia (R-8 best-effort warnings)
# ===========================================================================
class TestCheckFERoutesMatchIA:
    def test_pass_when_route_found_in_code(self, tmp_path):
        repo = tmp_path / "fe"
        repo.mkdir()
        # Create a faux React route file referencing /home
        (repo / "App.tsx").write_text(
            "<Route path=\"/home\" element={<Home />} />\n", encoding="utf-8"
        )
        ia_dir = _make_ia(tmp_path / "ia", ["home"], routes={"home": "/home"})
        warnings = vh.check_fe_routes_match_ia(str(repo), "", ia_dir)
        assert warnings == []

    def test_warning_when_route_missing_in_code(self, tmp_path):
        repo = tmp_path / "fe"
        repo.mkdir()
        (repo / "App.tsx").write_text(
            "<Route path=\"/home\" element={<Home />} />\n", encoding="utf-8"
        )
        ia_dir = _make_ia(
            tmp_path / "ia",
            ["home", "about"],
            routes={"home": "/home", "about": "/about"},
        )
        warnings = vh.check_fe_routes_match_ia(str(repo), "", ia_dir)
        assert any("/about" in w for w in warnings), warnings

    def test_empty_repo_returns_warnings_for_all_routes(self, tmp_path):
        repo = tmp_path / "fe"
        repo.mkdir()
        ia_dir = _make_ia(tmp_path / "ia", ["home"], routes={"home": "/home"})
        warnings = vh.check_fe_routes_match_ia(str(repo), "", ia_dir)
        # No code at all → /home warning
        assert any("/home" in w for w in warnings)

    def test_no_ia_returns_empty(self, tmp_path):
        repo = tmp_path / "fe"
        repo.mkdir()
        ia_dir = tmp_path / "ia"
        ia_dir.mkdir()
        assert vh.check_fe_routes_match_ia(str(repo), "", ia_dir) == []


# ===========================================================================
# ia.probe (Resume Dispatch detector — F3)
# ===========================================================================
class TestIAProbe:
    def test_probe_present_and_baseline_present(self, tmp_path):
        docs = tmp_path / "docs"
        ia_dir = docs / "discovery" / "ia"
        ia_dir.mkdir(parents=True)
        (ia_dir / "manifest.json").write_text('{"version": "2.0", "pages": []}\n')
        baseline_dir = ia_dir / ".baseline"
        baseline_dir.mkdir()
        (baseline_dir / "manifest.json").write_text('{"version": "2.0", "pages": []}\n')
        result = ia.probe(str(docs))
        assert result["present"] is True
        assert result["baseline_present"] is True
        assert result["manifest_path"].endswith("discovery/ia/manifest.json")

    def test_probe_present_no_baseline(self, tmp_path):
        docs = tmp_path / "docs"
        ia_dir = docs / "discovery" / "ia"
        ia_dir.mkdir(parents=True)
        (ia_dir / "manifest.json").write_text('{"version": "2.0", "pages": []}\n')
        result = ia.probe(str(docs))
        assert result["present"] is True
        assert result["baseline_present"] is False

    def test_probe_absent(self, tmp_path):
        docs = tmp_path / "docs"
        docs.mkdir()
        result = ia.probe(str(docs))
        assert result["present"] is False
        assert result["baseline_present"] is False

    def test_probe_empty_manifest_treated_as_absent(self, tmp_path):
        docs = tmp_path / "docs"
        ia_dir = docs / "discovery" / "ia"
        ia_dir.mkdir(parents=True)
        (ia_dir / "manifest.json").write_text("")  # zero bytes
        result = ia.probe(str(docs))
        assert result["present"] is False


# ===========================================================================
# ia probe CLI
# ===========================================================================
class TestIAProbeCLI:
    def test_cli_probe_present_exit_0(self, tmp_path, capsys):
        docs = tmp_path / "docs"
        ia_dir = docs / "discovery" / "ia"
        ia_dir.mkdir(parents=True)
        (ia_dir / "manifest.json").write_text('{"version": "2.0"}\n')
        with pytest.raises(SystemExit) as exc_info:
            ia.main(["probe", str(docs)])
        assert exc_info.value.code == 0
        out = capsys.readouterr().out
        data = json.loads(out.strip().splitlines()[-1])
        assert data["present"] is True

    def test_cli_probe_absent_exit_1(self, tmp_path, capsys):
        docs = tmp_path / "docs"
        docs.mkdir()
        with pytest.raises(SystemExit) as exc_info:
            ia.main(["probe", str(docs)])
        assert exc_info.value.code == 1
        out = capsys.readouterr().out
        data = json.loads(out.strip().splitlines()[-1])
        assert data["present"] is False
