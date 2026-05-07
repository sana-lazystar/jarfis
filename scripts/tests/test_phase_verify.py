"""Tests for jarfis.verify M3 additions — phase-verify + pattern-detect.

Covers:
    * Phase 7개 × PASS/FAIL fixtures (14+ 시나리오)
    * pattern-detect 4 시나리오 (stagnation/regression/oscillation/clean)
    * dispatch error paths
"""

import json
import os
import subprocess

import pytest

from jarfis import verify, verify_helpers as vh
from jarfis.verify import (
    PHASE_VERIFIERS,
    _parse_review_md,
    _detect_stagnation,
    _detect_regression,
    _detect_oscillation,
    _phase_1b_verify,
    _phase_2_verify,
    _phase_3_verify,
    _phase_4_verify,
    _phase_4_5_verify,
    _phase_5_verify,
    _phase_6_verify,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _write(path, text=""):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _state(tmp_path, **overrides):
    """Build a minimal state dict with docsDir=tmp_path/docs."""
    docs = tmp_path / "docs"
    docs.mkdir(exist_ok=True)
    state = {
        "work": {"docsDir": str(docs)},
        "workspace": {"scope": []},
        "design": {"mode": None},
        "api": {"mode": None},
        "devops": False,
        "responsive": "pc-only",
        "org": None,
    }
    state.update(overrides)
    return state, str(docs)


def _prd_full():
    return (
        "# PRD\n\n"
        "## Required Roles\n- admin\n\n"
        "## Functional Requirements\n- login\n\n"
        "## Success Metrics\n- DAU\n\n"
        "## Scope\n- admin-fe\n"
    )


# ===========================================================================
# Phase 1b
# ===========================================================================
class TestPhase1b:
    def test_pass_with_design(self, tmp_path):
        state, docs = _state(tmp_path, design={"mode": "figma"})
        docs_p = tmp_path / "docs"
        _write(docs_p / "discovery" / "prd.md", _prd_full())
        _write(docs_p / "discovery" / "working-backwards.md", "content")
        _write(
            docs_p / "discovery" / "ux-direction.md",
            "# UX Direction\n\n### order-list\n\nbody\n\n### user-profile\n\nbody\n",
        )
        assert _phase_1b_verify(state, docs) == []

    def test_pass_without_design(self, tmp_path):
        state, docs = _state(tmp_path)
        _write(tmp_path / "docs" / "discovery" / "prd.md", _prd_full())
        _write(tmp_path / "docs" / "discovery" / "working-backwards.md", "x")
        assert _phase_1b_verify(state, docs) == []

    def test_fail_prd_missing(self, tmp_path):
        state, docs = _state(tmp_path)
        _write(tmp_path / "docs" / "discovery" / "working-backwards.md", "x")
        missing = _phase_1b_verify(state, docs)
        assert "discovery/prd.md 누락" in missing

    def test_fail_required_roles_section_missing(self, tmp_path):
        state, docs = _state(tmp_path)
        partial = "# PRD\n\n## Functional Requirements\n- x\n\n## Success Metrics\n- y\n\n## Scope\n- z\n"
        _write(tmp_path / "docs" / "discovery" / "prd.md", partial)
        _write(tmp_path / "docs" / "discovery" / "working-backwards.md", "x")
        missing = _phase_1b_verify(state, docs)
        assert any("Required Roles" in m for m in missing)

    def test_fail_ux_direction_kebab_violation(self, tmp_path):
        state, docs = _state(tmp_path, design={"mode": "figma"})
        _write(tmp_path / "docs" / "discovery" / "prd.md", _prd_full())
        _write(tmp_path / "docs" / "discovery" / "working-backwards.md", "x")
        _write(
            tmp_path / "docs" / "discovery" / "ux-direction.md",
            "### Order_List\n### user-profile\n",
        )
        missing = _phase_1b_verify(state, docs)
        assert any("Order_List" in m for m in missing)


# ===========================================================================
# Phase 2
# ===========================================================================
class TestPhase2:
    def _base_planning(self, tmp_path):
        p = tmp_path / "docs" / "planning"
        _write(p / "architecture.md", "x")
        _write(p / "test-strategy.md", "x")
        return p

    def test_pass_fe_only(self, tmp_path):
        state, docs = _state(
            tmp_path,
            workspace={"scope": [{"name": "admin-fe", "type": "frontend"}]},
        )
        p = self._base_planning(tmp_path)
        _write(p / "tasks.md", "## Frontend Tasks — admin-fe\n- [ ] FE-1 login\n")
        assert _phase_2_verify(state, docs) == []

    def test_pass_fe_and_be(self, tmp_path):
        state, docs = _state(
            tmp_path,
            workspace={
                "scope": [
                    {"name": "admin-fe", "type": "frontend"},
                    {"name": "api", "type": "backend"},
                ]
            },
        )
        p = self._base_planning(tmp_path)
        _write(
            p / "tasks.md",
            "## Frontend Tasks — admin-fe\n- [ ] FE-1\n\n## Backend Tasks — api\n- [ ] BE-1\n",
        )
        _write(p / "api-spec.md", "openapi")
        assert _phase_2_verify(state, docs) == []

    def test_fail_be_scope_missing_section(self, tmp_path):
        state, docs = _state(
            tmp_path,
            workspace={"scope": [{"name": "api", "type": "backend"}]},
        )
        p = self._base_planning(tmp_path)
        _write(p / "tasks.md", "## Frontend Tasks — api\n- [ ] x\n")
        _write(p / "api-spec.md", "openapi")
        missing = _phase_2_verify(state, docs)
        assert any("Backend Tasks — api" in m for m in missing)

    def test_fail_backend_scope_missing_api_spec(self, tmp_path):
        state, docs = _state(
            tmp_path,
            workspace={"scope": [{"name": "api", "type": "backend"}]},
        )
        p = self._base_planning(tmp_path)
        _write(p / "tasks.md", "## Backend Tasks — api\n- [ ] BE-1\n")
        missing = _phase_2_verify(state, docs)
        assert any("api-spec.md" in m for m in missing)


# ===========================================================================
# Phase 3
# ===========================================================================
class TestPhase3:
    def _setup_ux(self, tmp_path, ids):
        _write(
            tmp_path / "docs" / "discovery" / "ux-direction.md",
            "".join(f"### {uid}\n\n" for uid in ids),
        )

    def _make_design(self, tmp_path, uid, *, mobile=False, tablet=False, empty=False):
        d = tmp_path / "docs" / "design" / uid
        if empty:
            _write(d / "index.html", "")
        else:
            _write(d / "index.html", "<html></html>")
        _write(d / "reference.png", "png")
        if mobile:
            _write(d / "reference-mobile.png", "png")
        if tablet:
            _write(d / "reference-tablet.png", "png")

    def test_pass_pc_only(self, tmp_path):
        state, docs = _state(
            tmp_path, design={"mode": "figma"}, responsive="pc-only",
        )
        self._setup_ux(tmp_path, ["order-list"])
        self._make_design(tmp_path, "order-list")
        _write(tmp_path / "docs" / "design" / "token-map.json", "{}")
        assert _phase_3_verify(state, docs) == []

    def test_fail_index_missing(self, tmp_path):
        state, docs = _state(tmp_path, design={"mode": "figma"})
        self._setup_ux(tmp_path, ["order-list"])
        # no index.html
        (tmp_path / "docs" / "design" / "order-list").mkdir(parents=True)
        _write(tmp_path / "docs" / "design" / "token-map.json", "{}")
        missing = _phase_3_verify(state, docs)
        assert any("order-list/index.html" in m for m in missing)

    def test_fail_mobile_required(self, tmp_path):
        state, docs = _state(
            tmp_path, design={"mode": "figma"}, responsive="pc-mobile",
        )
        self._setup_ux(tmp_path, ["order-list"])
        self._make_design(tmp_path, "order-list", mobile=False)
        _write(tmp_path / "docs" / "design" / "token-map.json", "{}")
        missing = _phase_3_verify(state, docs)
        assert any("reference-mobile.png" in m for m in missing)

    def test_fail_empty_index_html(self, tmp_path):
        state, docs = _state(tmp_path, design={"mode": "figma"})
        self._setup_ux(tmp_path, ["order-list"])
        self._make_design(tmp_path, "order-list", empty=True)
        _write(tmp_path / "docs" / "design" / "token-map.json", "{}")
        missing = _phase_3_verify(state, docs)
        assert any("order-list/index.html 누락 또는 빈 파일" in m for m in missing)

    # -----------------------------------------------------------------------
    # design-supplied-mode-v1 — Step 2 additions
    #
    # In supplied mode the design tree is copied verbatim from
    # ``state.design.suppliedPath`` to ``$DOCS_DIR/design/`` BEFORE this
    # verifier runs. The expected layout is ``design/pages/{slug}/index.html``
    # + ``reference.png``. token-map.json and ux-direction.md are not
    # required (SSOT: only the supplied tree counts).
    # -----------------------------------------------------------------------
    def _make_supplied_page(self, tmp_path, slug, *, with_ref=True, with_idx=True):
        page_dir = tmp_path / "docs" / "design" / "pages" / slug
        if with_idx:
            _write(page_dir / "index.html", "<html></html>")
        else:
            page_dir.mkdir(parents=True, exist_ok=True)
        if with_ref:
            _write(page_dir / "reference.png", "png")

    def test_supplied_pages_valid(self, tmp_path):
        state, docs = _state(
            tmp_path,
            design={
                "mode": "supplied",
                "figmaPages": [],
                "suppliedPath": "/abs/mockup",
                "brandAssetsDir": None,
            },
        )
        self._make_supplied_page(tmp_path, "home")
        self._make_supplied_page(tmp_path, "pricing")
        assert _phase_3_verify(state, docs) == []

    def test_supplied_design_dir_missing(self, tmp_path):
        state, docs = _state(
            tmp_path,
            design={
                "mode": "supplied",
                "figmaPages": [],
                "suppliedPath": "/abs/mockup",
                "brandAssetsDir": None,
            },
        )
        # No design/ at all
        missing = _phase_3_verify(state, docs)
        assert any("design/ 디렉토리 누락" in m for m in missing)

    def test_supplied_pages_dir_missing(self, tmp_path):
        state, docs = _state(
            tmp_path,
            design={
                "mode": "supplied",
                "figmaPages": [],
                "suppliedPath": "/abs/mockup",
                "brandAssetsDir": None,
            },
        )
        # design/ exists but no pages/ subtree
        (tmp_path / "docs" / "design").mkdir(parents=True)
        missing = _phase_3_verify(state, docs)
        assert any("design/pages/ 누락" in m for m in missing)

    def test_supplied_no_valid_page(self, tmp_path):
        state, docs = _state(
            tmp_path,
            design={
                "mode": "supplied",
                "figmaPages": [],
                "suppliedPath": "/abs/mockup",
                "brandAssetsDir": None,
            },
        )
        # page directory exists but reference.png missing
        self._make_supplied_page(tmp_path, "home", with_ref=False)
        missing = _phase_3_verify(state, docs)
        assert any(
            "design/pages/home/reference.png" in m for m in missing
        ), missing

    def test_supplied_no_index_html(self, tmp_path):
        state, docs = _state(
            tmp_path,
            design={
                "mode": "supplied",
                "figmaPages": [],
                "suppliedPath": "/abs/mockup",
                "brandAssetsDir": None,
            },
        )
        self._make_supplied_page(tmp_path, "home", with_idx=False)
        missing = _phase_3_verify(state, docs)
        assert any(
            "design/pages/home/index.html" in m for m in missing
        ), missing

    def test_supplied_figma_pages_violation(self, tmp_path):
        """Mutual exclusion: mode == "supplied" but figmaPages is not [].
        Should be flagged by the verifier so a Gate-2 read trips even if
        ``set_design_mode`` was bypassed somehow."""
        state, docs = _state(
            tmp_path,
            design={
                "mode": "supplied",
                "figmaPages": [{"title": "Stale", "url": "https://figma.com/x"}],
                "suppliedPath": "/abs/mockup",
                "brandAssetsDir": None,
            },
        )
        self._make_supplied_page(tmp_path, "home")
        missing = _phase_3_verify(state, docs)
        assert any(
            "figmaPages mutual exclusion" in m or "figmaPages 가 비어있지 않음" in m
            for m in missing
        ), missing


# ===========================================================================
# Phase 4 (git subprocess) — use a real temp repo
# ===========================================================================
def _init_repo(path):
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "t"], check=True)
    subprocess.run(["git", "-C", str(path), "config", "commit.gpgsign", "false"], check=True)


def _commit(path, msg, files):
    for rel, content in files.items():
        full = path / rel
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(content, encoding="utf-8")
    subprocess.run(["git", "-C", str(path), "add", "-A"], check=True)
    subprocess.run(
        ["git", "-C", str(path), "commit", "-q", "--no-gpg-sign", "-m", msg], check=True
    )
    out = subprocess.check_output(
        ["git", "-C", str(path), "rev-parse", "HEAD"], text=True
    )
    return out.strip()


class TestPhase4:
    def test_pass_fe_task_and_css_var(self, tmp_path):
        repo = tmp_path / "fe"
        repo.mkdir()
        _init_repo(repo)
        base = _commit(repo, "init", {"README.md": "x"})
        _commit(
            repo,
            "jarfis(FE-1): implement login",
            {"src/login.ts": "const x = 'var(--color-primary)';\n"},
        )

        state, docs = _state(
            tmp_path,
            workspace={
                "scope": [
                    {
                        "name": "admin-fe",
                        "type": "frontend",
                        "path": str(repo),
                        "baseCommit": base,
                    }
                ]
            },
        )
        _write(
            tmp_path / "docs" / "planning" / "tasks.md",
            "## Frontend Tasks — admin-fe\n- [ ] FE-1 login\n",
        )
        _write(tmp_path / "docs" / "design" / "token-map.json", "{}")
        assert _phase_4_verify(state, docs) == []

    def test_fail_commit_missing(self, tmp_path):
        repo = tmp_path / "fe"
        repo.mkdir()
        _init_repo(repo)
        base = _commit(repo, "init", {"README.md": "x"})
        _commit(repo, "chore: unrelated", {"docs.md": "y"})
        state, docs = _state(
            tmp_path,
            workspace={
                "scope": [
                    {"name": "admin-fe", "type": "frontend", "path": str(repo), "baseCommit": base}
                ]
            },
        )
        _write(
            tmp_path / "docs" / "planning" / "tasks.md",
            "## Frontend Tasks — admin-fe\n- [ ] FE-1 login\n",
        )
        missing = _phase_4_verify(state, docs)
        assert any("task FE-1" in m for m in missing)

    def test_fail_no_css_var_usage(self, tmp_path):
        repo = tmp_path / "fe"
        repo.mkdir()
        _init_repo(repo)
        base = _commit(repo, "init", {"README.md": "x"})
        _commit(
            repo,
            "jarfis(FE-1): implement",
            {"src/login.ts": "const x = 'hardcoded';\n"},
        )
        state, docs = _state(
            tmp_path,
            workspace={
                "scope": [
                    {"name": "admin-fe", "type": "frontend", "path": str(repo), "baseCommit": base}
                ]
            },
        )
        _write(
            tmp_path / "docs" / "planning" / "tasks.md",
            "## Frontend Tasks — admin-fe\n- [ ] FE-1\n",
        )
        _write(tmp_path / "docs" / "design" / "token-map.json", "{}")
        missing = _phase_4_verify(state, docs)
        assert any("CSS var(-- 사용 없음" in m for m in missing)


# ===========================================================================
# Phase 4.5
# ===========================================================================
class TestPhase4_5:
    def test_pass_no_devops(self, tmp_path):
        state, docs = _state(tmp_path)
        _write(tmp_path / "docs" / "ops" / "deployment-plan.md", "plan")
        assert _phase_4_5_verify(state, docs) == []

    def test_fail_missing_plan(self, tmp_path):
        state, docs = _state(tmp_path)
        missing = _phase_4_5_verify(state, docs)
        assert any("deployment-plan.md" in m for m in missing)

    def test_fail_devops_no_rollback(self, tmp_path):
        state, docs = _state(tmp_path, devops=True)
        _write(tmp_path / "docs" / "ops" / "deployment-plan.md", "# Plan\n\n## Deploy\n- x\n")
        missing = _phase_4_5_verify(state, docs)
        assert any("Rollback" in m for m in missing)


# ===========================================================================
# Phase 5
# ===========================================================================
class TestPhase5:
    def _base_review(self, projects, extra=""):
        body = []
        for name in projects:
            body.append(f"### {name}\n")
            for role in ("Tech Lead", "QA", "Security"):
                body.append(f"#### {role}\n- ok\n")
        return "\n".join(body) + "\n" + extra

    def test_pass_with_design_and_api(self, tmp_path):
        state, docs = _state(
            tmp_path,
            workspace={"scope": [{"name": "admin-fe", "type": "frontend"}]},
            design={"mode": "figma"},
        )
        _write(
            tmp_path / "docs" / "review" / "review.md",
            self._base_review(["admin-fe"], "## UX Design Review\n- ok\n"),
        )
        _write(tmp_path / "docs" / "review" / "api-contract-check.md", "x")
        _write(tmp_path / "docs" / "planning" / "api-spec.md", "openapi")
        assert _phase_5_verify(state, docs) == []

    def test_fail_project_section_missing(self, tmp_path):
        state, docs = _state(
            tmp_path,
            workspace={"scope": [{"name": "admin-fe", "type": "frontend"}]},
        )
        _write(tmp_path / "docs" / "review" / "review.md", "## Overall\n")
        missing = _phase_5_verify(state, docs)
        assert any("'### admin-fe' 섹션" in m for m in missing)

    def test_fail_security_subsection_missing(self, tmp_path):
        state, docs = _state(
            tmp_path,
            workspace={"scope": [{"name": "admin-fe", "type": "frontend"}]},
        )
        _write(
            tmp_path / "docs" / "review" / "review.md",
            "### admin-fe\n\n#### Tech Lead\n\n#### QA\n",
        )
        missing = _phase_5_verify(state, docs)
        assert any("Security" in m for m in missing)

    def test_fail_ux_review_missing_when_design(self, tmp_path):
        state, docs = _state(
            tmp_path,
            workspace={"scope": [{"name": "admin-fe", "type": "frontend"}]},
            design={"mode": "figma"},
        )
        _write(tmp_path / "docs" / "review" / "review.md", self._base_review(["admin-fe"]))
        missing = _phase_5_verify(state, docs)
        assert any("UX Design Review" in m for m in missing)


# ===========================================================================
# Phase 6
# ===========================================================================
class TestPhase6:
    def test_pass_standalone(self, tmp_path):
        state, docs = _state(tmp_path)
        _write(tmp_path / "docs" / "retrospective.md", "x")
        assert _phase_6_verify(state, docs) == []

    def test_fail_retro_missing(self, tmp_path):
        state, docs = _state(tmp_path)
        missing = _phase_6_verify(state, docs)
        assert any("retrospective.md" in m for m in missing)

    def test_org_wiki_missing(self, tmp_path):
        org_root = tmp_path / "org"
        org_root.mkdir()
        _init_repo(org_root)
        _commit(org_root, "init", {"README.md": "x"})
        _commit(org_root, "unrelated change", {"other.md": "y"})
        state, docs = _state(
            tmp_path, org={"name": "Medi", "root": str(org_root)}
        )
        _write(tmp_path / "docs" / "retrospective.md", "x")
        missing = _phase_6_verify(state, docs)
        assert any("wiki 변경 commit 없음" in m for m in missing)

    def test_org_wiki_index_updated(self, tmp_path):
        org_root = tmp_path / "org"
        org_root.mkdir()
        _init_repo(org_root)
        _commit(org_root, "init", {"README.md": "x"})
        _commit(
            org_root,
            "docs(wiki): add INDEX",
            {".jarfis-org/wiki/INDEX.md": "# Index"},
        )
        state, docs = _state(
            tmp_path, org={"name": "Medi", "root": str(org_root)}
        )
        _write(tmp_path / "docs" / "retrospective.md", "x")
        assert _phase_6_verify(state, docs) == []


# ===========================================================================
# pattern-detect
# ===========================================================================
class TestPatternDetect:
    def _rounds_md(self, rounds):
        """rounds: list[(n, [issue, ...])]. Build a review.md text."""
        out = ["# Review\n"]
        for n, issues in rounds:
            out.append(f"\n## Round {n}\n")
            for i in issues:
                out.append(f"- [REVISION] {i}\n")
        return "".join(out)

    def test_stagnation(self, tmp_path):
        md = tmp_path / "review.md"
        md.write_text(
            self._rounds_md([(1, ["API 500 error"]), (2, ["API 500 error", "new"])])
        )
        rounds = _parse_review_md(str(md))
        assert _detect_stagnation(rounds) == {"issue": "API 500 error", "rounds": [1, 2]}

    def test_regression(self, tmp_path):
        md = tmp_path / "review.md"
        md.write_text(
            self._rounds_md([(1, ["A"]), (2, ["A", "DB leak"])])
        )
        rounds = _parse_review_md(str(md))
        assert _detect_regression(rounds) == {"issue": "DB leak", "rounds": [2]}

    def test_oscillation(self, tmp_path):
        md = tmp_path / "review.md"
        md.write_text(
            self._rounds_md([(1, ["A"]), (2, ["B"]), (3, ["A"])])
        )
        rounds = _parse_review_md(str(md))
        assert _detect_oscillation(rounds) == {"rounds": [3, 1]}

    def test_clean(self, tmp_path):
        md = tmp_path / "review.md"
        md.write_text(
            self._rounds_md([(1, ["A", "B"]), (2, ["C"]), (3, [])])
        )
        rounds = _parse_review_md(str(md))
        assert _detect_stagnation(rounds) is None
        assert _detect_oscillation(rounds) is None

    def test_parse_empty(self, tmp_path):
        md = tmp_path / "review.md"
        md.write_text("# No rounds here")
        assert _parse_review_md(str(md)) == {}

    def test_detect_fewer_than_two_rounds(self):
        assert _detect_stagnation({1: ["A"]}) is None
        assert _detect_regression({1: ["A"]}) is None
        assert _detect_oscillation({1: ["A"], 2: ["A"]}) is None


# ===========================================================================
# Dispatch / error paths
# ===========================================================================
class TestDispatch:
    def test_phase_verifiers_keys(self):
        # "1" / "1a" / "1b" all alias Phase 1b (Defect #2 fix — work.md uses int phase ids).
        # "4.5" / "4-5" both map to Phase 4.5 (A.3 canonical: hyphen; tolerate dot).
        assert set(PHASE_VERIFIERS) == {"1", "1a", "1b", "2", "3", "4", "4-5", "4.5", "5", "6"}

    def test_unknown_phase_id(self, tmp_path, capsys):
        state_file = tmp_path / "s.json"
        state_file.write_text("{}")
        with pytest.raises(SystemExit):
            verify.cmd_phase_verify([str(state_file), "9"])
        assert "Unknown phase_id" in capsys.readouterr().err

    def test_state_file_missing(self, capsys):
        with pytest.raises(SystemExit):
            verify.cmd_phase_verify(["/nonexistent.json", "1b"])
        assert "state file not found" in capsys.readouterr().err

    def test_pattern_detect_missing_file(self, capsys):
        with pytest.raises(SystemExit):
            verify.cmd_pattern_detect(["/nonexistent.md"])
        assert "review.md not found" in capsys.readouterr().err


# ===========================================================================
# Evaluator helpers
# ===========================================================================
class TestEvaluators:
    def test_design_required(self):
        assert vh.design_required({"design": {"mode": "figma"}})
        assert not vh.design_required({"design": {"mode": None}})
        assert not vh.design_required({})

    def test_api_spec_required(self):
        s = {"workspace": {"scope": [{"type": "backend"}]}, "api": {"mode": None}}
        assert vh.api_spec_required(s)
        s2 = {"workspace": {"scope": []}, "api": {"mode": "swagger"}}
        assert vh.api_spec_required(s2)
        s3 = {"workspace": {"scope": [{"type": "frontend"}]}, "api": {"mode": None}}
        assert not vh.api_spec_required(s3)

    def test_responsive_default(self):
        assert vh.responsive_level({}) == "pc-only"
        assert vh.responsive_level({"responsive": "pc-mobile-tablet"}) == "pc-mobile-tablet"

    def test_org_registered(self):
        assert not vh.org_registered({"org": None})
        assert not vh.org_registered({})
        assert vh.org_registered({"org": {"name": "x", "root": "/p"}})
