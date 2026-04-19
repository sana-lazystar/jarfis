"""Tests for jarfis.verify — prerequisite validation for Gate 1/2/3.

Module renamed from jarfis.gate_check at M1 (imports updated accordingly).
"""

import json
import os

import pytest

from jarfis.verify import (
    CheckResult,
    _gate1_checks,
    _gate2_checks,
    _gate3_checks,
    _phase_check,
    _get_nested,
    _to_kebab,
    cmd_gate_check,
    cmd_phase_check,
)

# Public aliases the task spec refers to
run_gate_check = cmd_gate_check
run_phase_check = cmd_phase_check


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _statuses(results):
    """Return list of (label, status) tuples for assertion readability."""
    return [(r.label, r.status) for r in results]


def _find(results, keyword):
    """Return first CheckResult whose label contains *keyword*."""
    for r in results:
        if keyword in r.label:
            return r
    return None


def _make_docs(tmp_path, files=(), dirs=()):
    """Create a docs directory with the given relative file/dir paths."""
    docs = tmp_path / "docs"
    docs.mkdir(exist_ok=True)
    for rel in files:
        p = docs / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("")
    for rel in dirs:
        (docs / rel).mkdir(parents=True, exist_ok=True)
    return str(docs)


def _write_state(tmp_path, state):
    sf = tmp_path / ".jarfis-state.json"
    sf.write_text(json.dumps(state))
    return str(sf)


def _base_state(tmp_path, docs_dir=None):
    """Minimal valid state dict."""
    if docs_dir is None:
        docs_dir = str(tmp_path / "docs")
    return {
        "docs_dir": docs_dir,
        "phases": {
            "1": {"status": "pending"},
            "2": {"status": "pending"},
            "3": {"status": "pending"},
            "4": {"status": "pending"},
            "4.5": {"status": "pending"},
            "5": {"status": "pending"},
        },
        "required_roles": {},
        "gate_results": {},
    }


# ---------------------------------------------------------------------------
# Unit: _get_nested
# ---------------------------------------------------------------------------

class TestGetNested:
    def test_top_level(self):
        assert _get_nested({"a": 1}, "a") == 1

    def test_nested(self):
        assert _get_nested({"a": {"b": {"c": 42}}}, "a.b.c") == 42

    def test_missing_returns_default(self):
        assert _get_nested({}, "a.b", "fallback") == "fallback"

    def test_missing_returns_none_by_default(self):
        assert _get_nested({"a": 1}, "a.b") is None

    def test_non_dict_mid_path(self):
        assert _get_nested({"a": "string"}, "a.b", "x") == "x"


# ---------------------------------------------------------------------------
# Unit: _to_kebab
# ---------------------------------------------------------------------------

class TestToKebab:
    def test_basic_ascii(self):
        assert _to_kebab("Benefits Signup") == "benefits-signup"

    def test_extra_spaces(self):
        assert _to_kebab("  hello   world  ") == "hello-world"

    def test_special_chars_stripped(self):
        assert _to_kebab("Hello, World!") == "hello-world"

    def test_korean_preserved(self):
        assert _to_kebab("구매내역") == "구매내역"

    def test_already_kebab(self):
        assert _to_kebab("my-feature") == "my-feature"

    def test_multiple_hyphens_collapsed(self):
        assert _to_kebab("a--b---c") == "a-b-c"


# ---------------------------------------------------------------------------
# Gate 1 tests
# ---------------------------------------------------------------------------

class TestGate1:
    def _state(self, tmp_path, docs_dir, p1_status="completed", prd_score=85):
        s = _base_state(tmp_path, docs_dir)
        s["phases"]["1"] = {"status": p1_status}
        if prd_score is not None:
            s["phases"]["1"]["ratchet"] = {"prd_score": prd_score}
        return s

    def test_pass_all_conditions(self, tmp_path):
        docs = _make_docs(tmp_path, files=["press-release.md", "prd.md"])
        state = self._state(tmp_path, docs)
        results = _gate1_checks(state, docs)
        assert all(r.status in (CheckResult.PASS, CheckResult.SKIP) for r in results)

    def test_fail_press_release_missing(self, tmp_path):
        docs = _make_docs(tmp_path, files=["prd.md"])  # no press-release.md
        state = self._state(tmp_path, docs)
        results = _gate1_checks(state, docs)
        r = _find(results, "press-release.md")
        assert r is not None and r.status == CheckResult.FAIL

    def test_fail_prd_missing(self, tmp_path):
        docs = _make_docs(tmp_path, files=["press-release.md"])  # no prd.md
        state = self._state(tmp_path, docs)
        results = _gate1_checks(state, docs)
        r = _find(results, "prd.md")
        assert r is not None and r.status == CheckResult.FAIL

    def test_fail_ratchet_score_missing(self, tmp_path):
        docs = _make_docs(tmp_path, files=["press-release.md", "prd.md"])
        state = self._state(tmp_path, docs, prd_score=None)
        # Remove ratchet entirely
        state["phases"]["1"] = {"status": "completed"}
        results = _gate1_checks(state, docs)
        r = _find(results, "prd_score")
        assert r is not None and r.status == CheckResult.FAIL

    def test_fail_ratchet_key_absent(self, tmp_path):
        docs = _make_docs(tmp_path, files=["press-release.md", "prd.md"])
        state = self._state(tmp_path, docs, prd_score=None)
        # phases.1.ratchet exists but has no prd_score key
        state["phases"]["1"]["ratchet"] = {"other_key": 10}
        results = _gate1_checks(state, docs)
        r = _find(results, "prd_score")
        assert r is not None and r.status == CheckResult.FAIL

    def test_phase1_pending_is_fail(self, tmp_path):
        docs = _make_docs(tmp_path, files=["press-release.md", "prd.md"])
        state = self._state(tmp_path, docs, p1_status="pending")
        results = _gate1_checks(state, docs)
        r = _find(results, "phases.1.status")
        assert r is not None and r.status == CheckResult.FAIL

    def test_phase1_in_progress_is_pass(self, tmp_path):
        docs = _make_docs(tmp_path, files=["press-release.md", "prd.md"])
        state = self._state(tmp_path, docs, p1_status="in_progress")
        results = _gate1_checks(state, docs)
        r = _find(results, "phases.1.status")
        assert r is not None and r.status == CheckResult.PASS

    def test_score_is_reported_in_detail(self, tmp_path):
        docs = _make_docs(tmp_path, files=["press-release.md", "prd.md"])
        state = self._state(tmp_path, docs, prd_score=92)
        results = _gate1_checks(state, docs)
        r = _find(results, "prd_score")
        assert r is not None and r.status == CheckResult.PASS
        assert "92" in r.detail


# ---------------------------------------------------------------------------
# Gate 2 tests
# ---------------------------------------------------------------------------

GATE2_ALWAYS_REQUIRED = [
    "impact-analysis.md",
    "architecture.md",
    "tasks.md",
    "test-strategy.md",
]


class TestGate2AlwaysRequired:
    def _full_state(self, tmp_path, docs_dir):
        s = _base_state(tmp_path, docs_dir)
        s["phases"]["2"] = {"status": "completed"}
        s["phases"]["3"] = {"status": "skipped", "reason": "no UX"}
        s["required_roles"] = {"frontend": False, "ux_designer": False}
        s["api_spec_required"] = False
        return s

    def test_pass_all_files_present(self, tmp_path):
        files = GATE2_ALWAYS_REQUIRED[:]
        docs = _make_docs(tmp_path, files=files)
        state = self._full_state(tmp_path, docs)
        results = _gate2_checks(state, docs)
        for fname in GATE2_ALWAYS_REQUIRED:
            r = _find(results, fname)
            assert r is not None and r.status == CheckResult.PASS, f"{fname} should PASS"

    def test_fail_when_architecture_missing(self, tmp_path):
        files = [f for f in GATE2_ALWAYS_REQUIRED if f != "architecture.md"]
        docs = _make_docs(tmp_path, files=files)
        state = self._full_state(tmp_path, docs)
        results = _gate2_checks(state, docs)
        r = _find(results, "architecture.md")
        assert r is not None and r.status == CheckResult.FAIL

    def test_fail_when_tasks_missing(self, tmp_path):
        files = [f for f in GATE2_ALWAYS_REQUIRED if f != "tasks.md"]
        docs = _make_docs(tmp_path, files=files)
        state = self._full_state(tmp_path, docs)
        results = _gate2_checks(state, docs)
        r = _find(results, "tasks.md")
        assert r is not None and r.status == CheckResult.FAIL


class TestGate2ApiSpec:
    def _state(self, tmp_path, docs_dir, *, api_spec_required, be=False, fe=False):
        s = _base_state(tmp_path, docs_dir)
        s["phases"]["2"] = {"status": "completed"}
        s["phases"]["3"] = {"status": "skipped"}
        s["required_roles"] = {
            "backend": be,
            "frontend": fe,
            "ux_designer": False,
        }
        s["api_spec_required"] = api_spec_required
        return s

    def test_skip_when_api_spec_required_false(self, tmp_path):
        docs = _make_docs(tmp_path, files=GATE2_ALWAYS_REQUIRED)
        state = self._state(tmp_path, docs, api_spec_required=False)
        results = _gate2_checks(state, docs)
        r = _find(results, "api-spec.md")
        assert r is not None and r.status == CheckResult.SKIP

    def test_fail_when_api_spec_required_true_and_file_missing(self, tmp_path):
        docs = _make_docs(tmp_path, files=GATE2_ALWAYS_REQUIRED)
        # no api-spec.md created
        state = self._state(tmp_path, docs, api_spec_required=True)
        results = _gate2_checks(state, docs)
        r = _find(results, "api-spec.md")
        assert r is not None and r.status == CheckResult.FAIL

    def test_pass_when_api_spec_required_true_and_file_present(self, tmp_path):
        docs = _make_docs(tmp_path, files=GATE2_ALWAYS_REQUIRED + ["api-spec.md"])
        state = self._state(tmp_path, docs, api_spec_required=True)
        results = _gate2_checks(state, docs)
        r = _find(results, "api-spec.md")
        assert r is not None and r.status == CheckResult.PASS

    def test_fallback_derive_from_roles_both_true(self, tmp_path):
        """When api_spec_required absent, derive from required_roles (be+fe -> True)."""
        docs = _make_docs(tmp_path, files=GATE2_ALWAYS_REQUIRED)
        # Omit api_spec_required entirely
        s = _base_state(tmp_path, docs)
        s["phases"]["2"] = {"status": "completed"}
        s["phases"]["3"] = {"status": "skipped"}
        s["required_roles"] = {"backend": True, "frontend": True, "ux_designer": False}
        # Do NOT set api_spec_required key
        results = _gate2_checks(s, docs)
        r = _find(results, "api-spec.md")
        # File missing -> should FAIL (derived as required)
        assert r is not None and r.status == CheckResult.FAIL

    def test_fallback_derive_from_roles_fe_only(self, tmp_path):
        """be=False, fe=True -> api_spec_required derived as False -> SKIP."""
        docs = _make_docs(tmp_path, files=GATE2_ALWAYS_REQUIRED)
        s = _base_state(tmp_path, docs)
        s["phases"]["2"] = {"status": "completed"}
        s["phases"]["3"] = {"status": "skipped"}
        s["required_roles"] = {"backend": False, "frontend": True, "ux_designer": False}
        results = _gate2_checks(s, docs)
        r = _find(results, "api-spec.md")
        assert r is not None and r.status == CheckResult.SKIP

    def test_fallback_derive_from_roles_neither(self, tmp_path):
        """be=False, fe=False -> api_spec_required derived as False -> SKIP."""
        docs = _make_docs(tmp_path, files=GATE2_ALWAYS_REQUIRED)
        s = _base_state(tmp_path, docs)
        s["phases"]["2"] = {"status": "completed"}
        s["phases"]["3"] = {"status": "skipped"}
        s["required_roles"] = {"backend": False, "frontend": False, "ux_designer": False}
        results = _gate2_checks(s, docs)
        r = _find(results, "api-spec.md")
        assert r is not None and r.status == CheckResult.SKIP


class TestGate2DesignFiles:
    """Design artifact checks gated on frontend + ux_designer roles."""

    def _state_with_figma(self, tmp_path, docs_dir, figma_pages):
        s = _base_state(tmp_path, docs_dir)
        s["phases"]["2"] = {"status": "completed"}
        s["phases"]["3"] = {
            "status": "in_progress",
            "mode": "figma",
            "figma_pages": figma_pages,
        }
        s["required_roles"] = {"frontend": True, "ux_designer": True}
        s["api_spec_required"] = False
        return s

    def test_skip_design_when_ux_not_required(self, tmp_path):
        docs = _make_docs(tmp_path, files=GATE2_ALWAYS_REQUIRED)
        s = _base_state(tmp_path, docs)
        s["phases"]["2"] = {"status": "completed"}
        s["phases"]["3"] = {"status": "pending"}
        s["required_roles"] = {"frontend": True, "ux_designer": False}
        s["api_spec_required"] = False
        results = _gate2_checks(s, docs)
        r = _find(results, "design/")
        assert r is not None and r.status == CheckResult.SKIP

    def test_skip_design_when_frontend_not_required(self, tmp_path):
        docs = _make_docs(tmp_path, files=GATE2_ALWAYS_REQUIRED)
        s = _base_state(tmp_path, docs)
        s["phases"]["2"] = {"status": "completed"}
        s["phases"]["3"] = {"status": "pending"}
        s["required_roles"] = {"frontend": False, "ux_designer": True}
        s["api_spec_required"] = False
        results = _gate2_checks(s, docs)
        r = _find(results, "design/")
        assert r is not None and r.status == CheckResult.SKIP

    def test_fail_figma_missing_html(self, tmp_path):
        """Figma mode: reference.png present but index.html missing -> FAIL."""
        figma_pages = [{"title": "Benefits Signup"}]
        docs = _make_docs(
            tmp_path,
            files=GATE2_ALWAYS_REQUIRED + [
                "design/benefits-signup/reference.png",
                "design/_index.html",
            ],
        )
        state = self._state_with_figma(tmp_path, docs, figma_pages)
        results = _gate2_checks(state, docs)
        idx_check = _find(results, "design/benefits-signup/index.html")
        assert idx_check is not None and idx_check.status == CheckResult.FAIL

    def test_pass_figma_all_files_present(self, tmp_path):
        """Figma mode: reference.png + index.html + _index.html + ux-direction.md all present -> PASS."""
        figma_pages = [{"title": "Benefits Signup"}]
        docs = _make_docs(
            tmp_path,
            files=GATE2_ALWAYS_REQUIRED + [
                "ux-direction.md",
                "design/benefits-signup/reference.png",
                "design/benefits-signup/index.html",
                "design/_index.html",
            ],
        )
        state = self._state_with_figma(tmp_path, docs, figma_pages)
        # Also need phase 3 status check to pass
        state["phases"]["3"]["status"] = "completed"
        results = _gate2_checks(state, docs)
        fails = [r for r in results if r.status == CheckResult.FAIL]
        assert fails == [], f"Unexpected failures: {[(r.label, r.detail) for r in fails]}"

    def test_fail_figma_empty_pages(self, tmp_path):
        """Figma mode with figma_pages=[] -> FAIL."""
        docs = _make_docs(tmp_path, files=GATE2_ALWAYS_REQUIRED)
        state = self._state_with_figma(tmp_path, docs, figma_pages=[])
        results = _gate2_checks(state, docs)
        r = _find(results, "figma pages")
        assert r is not None and r.status == CheckResult.FAIL

    def test_phase3_explicitly_skipped_is_skip(self, tmp_path):
        """phase3 status=skipped with reason -> design/ check is SKIP."""
        docs = _make_docs(tmp_path, files=GATE2_ALWAYS_REQUIRED)
        s = _base_state(tmp_path, docs)
        s["phases"]["2"] = {"status": "completed"}
        s["phases"]["3"] = {"status": "skipped", "reason": "Approved by PM"}
        s["required_roles"] = {"frontend": True, "ux_designer": True}
        s["api_spec_required"] = False
        results = _gate2_checks(s, docs)
        r = _find(results, "design/")
        assert r is not None and r.status == CheckResult.SKIP
        assert "skipped" in r.detail.lower()

    def test_ux_direction_required_when_ux_designer(self, tmp_path):
        """ux_designer=True -> ux-direction.md should be required."""
        docs = _make_docs(tmp_path, files=GATE2_ALWAYS_REQUIRED)
        s = _base_state(tmp_path, docs)
        s["phases"]["2"] = {"status": "completed"}
        s["phases"]["3"] = {"status": "skipped"}
        s["required_roles"] = {"frontend": False, "ux_designer": True}
        s["api_spec_required"] = False
        results = _gate2_checks(s, docs)
        r = _find(results, "ux-direction.md")
        # File not created -> should FAIL
        assert r is not None and r.status == CheckResult.FAIL

    def test_ux_direction_skipped_when_no_ux_designer(self, tmp_path):
        """ux_designer=False -> ux-direction.md SKIP."""
        docs = _make_docs(tmp_path, files=GATE2_ALWAYS_REQUIRED)
        s = _base_state(tmp_path, docs)
        s["phases"]["2"] = {"status": "completed"}
        s["phases"]["3"] = {"status": "skipped"}
        s["required_roles"] = {"frontend": False, "ux_designer": False}
        s["api_spec_required"] = False
        results = _gate2_checks(s, docs)
        r = _find(results, "ux-direction.md")
        assert r is not None and r.status == CheckResult.SKIP


class TestGate2PhaseStatuses:
    def test_phase2_not_completed_is_fail(self, tmp_path):
        docs = _make_docs(tmp_path, files=GATE2_ALWAYS_REQUIRED)
        s = _base_state(tmp_path, docs)
        s["phases"]["2"] = {"status": "in_progress"}
        s["phases"]["3"] = {"status": "skipped"}
        s["required_roles"] = {"frontend": False, "ux_designer": False}
        s["api_spec_required"] = False
        results = _gate2_checks(s, docs)
        r = _find(results, "phases.2.status")
        assert r is not None and r.status == CheckResult.FAIL

    def test_phase3_status_skipped_when_not_needed(self, tmp_path):
        docs = _make_docs(tmp_path, files=GATE2_ALWAYS_REQUIRED)
        s = _base_state(tmp_path, docs)
        s["phases"]["2"] = {"status": "completed"}
        s["phases"]["3"] = {"status": "pending"}
        s["required_roles"] = {"frontend": False, "ux_designer": False}
        s["api_spec_required"] = False
        results = _gate2_checks(s, docs)
        r = _find(results, "phases.3.status")
        assert r is not None and r.status == CheckResult.SKIP


# ---------------------------------------------------------------------------
# Gate 3 tests
# ---------------------------------------------------------------------------

class TestGate3:
    def _full_state(self, tmp_path, docs_dir):
        s = _base_state(tmp_path, docs_dir)
        s["phases"]["4"] = {"status": "completed"}
        s["phases"]["4.5"] = {"status": "completed"}
        s["phases"]["5"] = {"status": "in_progress"}
        s["required_roles"] = {"devops": False, "frontend": True, "ux_designer": False}
        s["phase5_agents"] = {"tech_lead": "completed", "qa": "completed", "security": "completed"}
        return s

    def test_pass_all_required(self, tmp_path):
        docs = _make_docs(
            tmp_path,
            files=["review.md", "deployment-plan.md"],
        )
        state = self._full_state(tmp_path, docs)
        results = _gate3_checks(state, docs)
        fails = [r for r in results if r.status == CheckResult.FAIL]
        assert fails == [], f"Unexpected FAIL: {[(r.label, r.detail) for r in fails]}"

    def test_fail_review_md_missing(self, tmp_path):
        docs = _make_docs(tmp_path, files=["deployment-plan.md"])
        state = self._full_state(tmp_path, docs)
        results = _gate3_checks(state, docs)
        r = _find(results, "review.md")
        assert r is not None and r.status == CheckResult.FAIL

    def test_fail_deployment_plan_missing(self, tmp_path):
        docs = _make_docs(tmp_path, files=["review.md"])
        state = self._full_state(tmp_path, docs)
        results = _gate3_checks(state, docs)
        r = _find(results, "deployment-plan.md")
        assert r is not None and r.status == CheckResult.FAIL

    def test_skip_api_contract_check_when_no_api_spec(self, tmp_path):
        """No api-spec.md -> api-contract-check.md check should be SKIP."""
        docs = _make_docs(tmp_path, files=["review.md", "deployment-plan.md"])
        state = self._full_state(tmp_path, docs)
        results = _gate3_checks(state, docs)
        r = _find(results, "api-contract-check.md")
        assert r is not None and r.status == CheckResult.SKIP

    def test_fail_api_contract_check_when_api_spec_exists(self, tmp_path):
        """api-spec.md exists but api-contract-check.md missing -> FAIL."""
        docs = _make_docs(
            tmp_path,
            files=["review.md", "deployment-plan.md", "api-spec.md"],
        )
        state = self._full_state(tmp_path, docs)
        results = _gate3_checks(state, docs)
        r = _find(results, "api-contract-check.md")
        assert r is not None and r.status == CheckResult.FAIL

    def test_pass_api_contract_check_when_both_present(self, tmp_path):
        docs = _make_docs(
            tmp_path,
            files=["review.md", "deployment-plan.md", "api-spec.md", "api-contract-check.md"],
        )
        state = self._full_state(tmp_path, docs)
        results = _gate3_checks(state, docs)
        r = _find(results, "api-contract-check.md")
        assert r is not None and r.status == CheckResult.PASS

    def test_skip_infra_runbook_when_devops_not_required(self, tmp_path):
        docs = _make_docs(tmp_path, files=["review.md", "deployment-plan.md"])
        state = self._full_state(tmp_path, docs)
        state["required_roles"]["devops"] = False
        results = _gate3_checks(state, docs)
        r = _find(results, "infra-runbook.md")
        assert r is not None and r.status == CheckResult.SKIP

    def test_skip_infra_runbook_when_devops_agent_skipped(self, tmp_path):
        docs = _make_docs(tmp_path, files=["review.md", "deployment-plan.md"])
        state = self._full_state(tmp_path, docs)
        state["required_roles"]["devops"] = True
        state["phase4_agents"] = {"devops": "skipped"}
        results = _gate3_checks(state, docs)
        r = _find(results, "infra-runbook.md")
        assert r is not None and r.status == CheckResult.SKIP

    def test_fail_infra_runbook_when_devops_executed_but_file_missing(self, tmp_path):
        docs = _make_docs(tmp_path, files=["review.md", "deployment-plan.md"])
        state = self._full_state(tmp_path, docs)
        state["required_roles"]["devops"] = True
        state["phase4_agents"] = {"devops": "completed"}
        results = _gate3_checks(state, docs)
        r = _find(results, "infra-runbook.md")
        assert r is not None and r.status == CheckResult.FAIL

    def test_pass_infra_runbook_when_devops_executed_and_file_present(self, tmp_path):
        docs = _make_docs(
            tmp_path,
            files=["review.md", "deployment-plan.md", "infra-runbook.md"],
        )
        state = self._full_state(tmp_path, docs)
        state["required_roles"]["devops"] = True
        state["phase4_agents"] = {"devops": "completed"}
        results = _gate3_checks(state, docs)
        r = _find(results, "infra-runbook.md")
        assert r is not None and r.status == CheckResult.PASS

    def test_phase45_key_variant_dot(self, tmp_path):
        """phases['4.5'].status == 'completed' -> PASS."""
        docs = _make_docs(tmp_path, files=["review.md", "deployment-plan.md"])
        state = self._full_state(tmp_path, docs)
        state["phases"]["4.5"] = {"status": "completed"}
        state["phases"].pop("4_5", None)
        results = _gate3_checks(state, docs)
        r = _find(results, "phases.4.5.status")
        assert r is not None and r.status == CheckResult.PASS

    def test_phase45_key_variant_underscore(self, tmp_path):
        """phases['4_5'].status == 'completed' -> PASS (underscore variant)."""
        docs = _make_docs(tmp_path, files=["review.md", "deployment-plan.md"])
        state = self._full_state(tmp_path, docs)
        # Use 4_5 key only, drop 4.5
        state["phases"].pop("4.5", None)
        state["phases"]["4_5"] = {"status": "completed"}
        results = _gate3_checks(state, docs)
        r = _find(results, "phases.4.5.status")
        assert r is not None and r.status == CheckResult.PASS

    def test_phase45_both_variants_present_one_completed(self, tmp_path):
        """If either variant is 'completed', result is PASS."""
        docs = _make_docs(tmp_path, files=["review.md", "deployment-plan.md"])
        state = self._full_state(tmp_path, docs)
        state["phases"]["4.5"] = {"status": "pending"}
        state["phases"]["4_5"] = {"status": "completed"}
        results = _gate3_checks(state, docs)
        r = _find(results, "phases.4.5.status")
        assert r is not None and r.status == CheckResult.PASS

    def test_phase45_missing_is_fail(self, tmp_path):
        docs = _make_docs(tmp_path, files=["review.md", "deployment-plan.md"])
        state = self._full_state(tmp_path, docs)
        state["phases"]["4.5"] = {"status": "pending"}
        state["phases"].pop("4_5", None)
        results = _gate3_checks(state, docs)
        r = _find(results, "phases.4.5.status")
        assert r is not None and r.status == CheckResult.FAIL

    def test_phase4_not_completed_is_fail(self, tmp_path):
        docs = _make_docs(tmp_path, files=["review.md", "deployment-plan.md"])
        state = self._full_state(tmp_path, docs)
        state["phases"]["4"] = {"status": "in_progress"}
        results = _gate3_checks(state, docs)
        r = _find(results, "phases.4.status")
        assert r is not None and r.status == CheckResult.FAIL

    def test_phase5_pending_is_fail(self, tmp_path):
        docs = _make_docs(tmp_path, files=["review.md", "deployment-plan.md"])
        state = self._full_state(tmp_path, docs)
        state["phases"]["5"] = {"status": "pending"}
        results = _gate3_checks(state, docs)
        r = _find(results, "phases.5.status")
        assert r is not None and r.status == CheckResult.FAIL

    def test_phase5_completed_is_pass(self, tmp_path):
        docs = _make_docs(tmp_path, files=["review.md", "deployment-plan.md"])
        state = self._full_state(tmp_path, docs)
        state["phases"]["5"] = {"status": "completed"}
        results = _gate3_checks(state, docs)
        r = _find(results, "phases.5.status")
        assert r is not None and r.status == CheckResult.PASS

    def test_phase5_agents_all_present_pass(self, tmp_path):
        """All required phase5 agents recorded -> PASS."""
        docs = _make_docs(tmp_path, files=["review.md", "deployment-plan.md"])
        state = self._full_state(tmp_path, docs)
        results = _gate3_checks(state, docs)
        for role in ["tech_lead", "qa", "security"]:
            r = _find(results, f"phase5_agents.{role}")
            assert r is not None and r.status == CheckResult.PASS, f"{role} should PASS"

    def test_phase5_agents_missing_tl_fail(self, tmp_path):
        """tech_lead not recorded -> FAIL."""
        docs = _make_docs(tmp_path, files=["review.md", "deployment-plan.md"])
        state = self._full_state(tmp_path, docs)
        del state["phase5_agents"]["tech_lead"]
        results = _gate3_checks(state, docs)
        r = _find(results, "phase5_agents.tech_lead")
        assert r is not None and r.status == CheckResult.FAIL

    def test_phase5_agents_ux_required_but_missing_fail(self, tmp_path):
        """UX designer required + FE needed but not recorded -> FAIL."""
        docs = _make_docs(tmp_path, files=["review.md", "deployment-plan.md"])
        state = self._full_state(tmp_path, docs)
        state["required_roles"]["ux_designer"] = True
        state["required_roles"]["frontend"] = True
        # phase5_agents has tl/qa/security but NOT ux_designer
        results = _gate3_checks(state, docs)
        r = _find(results, "phase5_agents.ux_designer")
        assert r is not None and r.status == CheckResult.FAIL

    def test_phase5_agents_ux_not_required_skip(self, tmp_path):
        """UX designer not required -> no ux_designer check at all."""
        docs = _make_docs(tmp_path, files=["review.md", "deployment-plan.md"])
        state = self._full_state(tmp_path, docs)
        state["required_roles"]["ux_designer"] = False
        results = _gate3_checks(state, docs)
        r = _find(results, "phase5_agents.ux_designer")
        assert r is None  # Not even checked

    def test_phase5_agents_ux_required_and_present_pass(self, tmp_path):
        """UX designer required + recorded -> PASS."""
        docs = _make_docs(tmp_path, files=["review.md", "deployment-plan.md"])
        state = self._full_state(tmp_path, docs)
        state["required_roles"]["ux_designer"] = True
        state["required_roles"]["frontend"] = True
        state["phase5_agents"]["ux_designer"] = "completed"
        results = _gate3_checks(state, docs)
        r = _find(results, "phase5_agents.ux_designer")
        assert r is not None and r.status == CheckResult.PASS

    def test_phase5_agents_empty_all_fail(self, tmp_path):
        """No phase5_agents at all -> all 3 required agents FAIL."""
        docs = _make_docs(tmp_path, files=["review.md", "deployment-plan.md"])
        state = self._full_state(tmp_path, docs)
        state["phase5_agents"] = {}
        results = _gate3_checks(state, docs)
        fails = [r for r in results if "phase5_agents" in r.label and r.status == CheckResult.FAIL]
        assert len(fails) == 3  # tl, qa, security


# ---------------------------------------------------------------------------
# Phase check tests
# ---------------------------------------------------------------------------

class TestPhaseCheck2:
    def test_pass_gate1_approved_and_phase1_completed(self, tmp_path):
        docs = _make_docs(tmp_path)
        s = _base_state(tmp_path, docs)
        s["gate_results"] = {"gate1": {"decision": "approved"}}
        s["phases"]["1"] = {"status": "completed"}
        results = _phase_check(s, docs, 2)
        fails = [r for r in results if r.status == CheckResult.FAIL]
        assert fails == [], f"Unexpected FAIL: {[(r.label, r.detail) for r in fails]}"

    def test_fail_gate1_not_approved(self, tmp_path):
        docs = _make_docs(tmp_path)
        s = _base_state(tmp_path, docs)
        s["gate_results"] = {"gate1": {"decision": "pending"}}
        s["phases"]["1"] = {"status": "completed"}
        results = _phase_check(s, docs, 2)
        r = _find(results, "gate_results.gate1.decision")
        assert r is not None and r.status == CheckResult.FAIL

    def test_fail_gate1_missing(self, tmp_path):
        docs = _make_docs(tmp_path)
        s = _base_state(tmp_path, docs)
        # gate_results.gate1 not set at all
        s["gate_results"] = {}
        s["phases"]["1"] = {"status": "completed"}
        results = _phase_check(s, docs, 2)
        r = _find(results, "gate_results.gate1.decision")
        assert r is not None and r.status == CheckResult.FAIL

    def test_fail_phase1_not_completed(self, tmp_path):
        docs = _make_docs(tmp_path)
        s = _base_state(tmp_path, docs)
        s["gate_results"] = {"gate1": {"decision": "approved"}}
        s["phases"]["1"] = {"status": "in_progress"}
        results = _phase_check(s, docs, 2)
        r = _find(results, "phases.1.status")
        assert r is not None and r.status == CheckResult.FAIL

    def test_api_spec_readiness_check_when_fe_and_api_spec_required(self, tmp_path):
        """When frontend=True and api_spec_required=True, readiness check PASS."""
        docs = _make_docs(tmp_path)
        s = _base_state(tmp_path, docs)
        s["gate_results"] = {"gate1": {"decision": "approved"}}
        s["phases"]["1"] = {"status": "completed"}
        s["required_roles"] = {"frontend": True}
        s["api_spec_required"] = True
        results = _phase_check(s, docs, 2)
        r = _find(results, "API spec extraction")
        assert r is not None and r.status == CheckResult.PASS

    def test_no_api_spec_readiness_when_not_required(self, tmp_path):
        """No extra check emitted when api_spec_required=False."""
        docs = _make_docs(tmp_path)
        s = _base_state(tmp_path, docs)
        s["gate_results"] = {"gate1": {"decision": "approved"}}
        s["phases"]["1"] = {"status": "completed"}
        s["required_roles"] = {"frontend": False}
        s["api_spec_required"] = False
        results = _phase_check(s, docs, 2)
        r = _find(results, "API spec extraction")
        assert r is None  # check not emitted


class TestPhaseCheck4:
    def test_pass_gate2_approved_and_phase2_completed_with_artifacts(self, tmp_path):
        docs = _make_docs(tmp_path, files=GATE2_ALWAYS_REQUIRED)
        s = _base_state(tmp_path, docs)
        s["gate_results"] = {"gate2": {"decision": "approved"}}
        s["phases"]["2"] = {"status": "completed"}
        results = _phase_check(s, docs, 4)
        fails = [r for r in results if r.status == CheckResult.FAIL]
        assert fails == [], f"Unexpected FAIL: {[(r.label, r.detail) for r in fails]}"

    def test_fail_gate2_not_approved(self, tmp_path):
        docs = _make_docs(tmp_path, files=GATE2_ALWAYS_REQUIRED)
        s = _base_state(tmp_path, docs)
        s["gate_results"] = {"gate2": {"decision": "revision_requested"}}
        s["phases"]["2"] = {"status": "completed"}
        results = _phase_check(s, docs, 4)
        r = _find(results, "gate_results.gate2.decision")
        assert r is not None and r.status == CheckResult.FAIL

    def test_fail_phase2_not_completed(self, tmp_path):
        docs = _make_docs(tmp_path, files=GATE2_ALWAYS_REQUIRED)
        s = _base_state(tmp_path, docs)
        s["gate_results"] = {"gate2": {"decision": "approved"}}
        s["phases"]["2"] = {"status": "in_progress"}
        results = _phase_check(s, docs, 4)
        r = _find(results, "phases.2.status")
        assert r is not None and r.status == CheckResult.FAIL

    def test_fail_when_phase2_artifact_missing(self, tmp_path):
        files = [f for f in GATE2_ALWAYS_REQUIRED if f != "architecture.md"]
        docs = _make_docs(tmp_path, files=files)
        s = _base_state(tmp_path, docs)
        s["gate_results"] = {"gate2": {"decision": "approved"}}
        s["phases"]["2"] = {"status": "completed"}
        results = _phase_check(s, docs, 4)
        r = _find(results, "architecture.md")
        assert r is not None and r.status == CheckResult.FAIL


class TestPhaseCheckOther:
    def test_phase_with_no_checks_returns_skip(self, tmp_path):
        docs = _make_docs(tmp_path)
        s = _base_state(tmp_path, docs)
        results = _phase_check(s, docs, 99)
        assert len(results) == 1
        assert results[0].status == CheckResult.SKIP

    def test_phase6_requires_gate3_approved(self, tmp_path):
        docs = _make_docs(tmp_path)
        s = _base_state(tmp_path, docs)
        s["gate_results"] = {"gate3": {"decision": "approved"}}
        s["phases"]["5"] = {"status": "completed"}
        results = _phase_check(s, docs, 6)
        fails = [r for r in results if r.status == CheckResult.FAIL]
        assert fails == [], f"Unexpected FAIL: {[(r.label, r.detail) for r in fails]}"

    def test_phase6_fail_gate3_not_approved(self, tmp_path):
        docs = _make_docs(tmp_path)
        s = _base_state(tmp_path, docs)
        s["gate_results"] = {}
        s["phases"]["5"] = {"status": "completed"}
        results = _phase_check(s, docs, 6)
        r = _find(results, "gate_results.gate3.decision")
        assert r is not None and r.status == CheckResult.FAIL

    def test_phase5_checks_phase4_and_4_5(self, tmp_path):
        docs = _make_docs(tmp_path)
        s = _base_state(tmp_path, docs)
        s["phases"]["4"] = {"status": "completed"}
        s["phases"]["4.5"] = {"status": "completed"}
        results = _phase_check(s, docs, 5)
        fails = [r for r in results if r.status == CheckResult.FAIL]
        assert fails == [], f"Unexpected FAIL: {[(r.label, r.detail) for r in fails]}"

    def test_phase5_fail_when_phase4_not_completed(self, tmp_path):
        docs = _make_docs(tmp_path)
        s = _base_state(tmp_path, docs)
        s["phases"]["4"] = {"status": "in_progress"}
        s["phases"]["4.5"] = {"status": "completed"}
        results = _phase_check(s, docs, 5)
        r = _find(results, "phases.4.status")
        assert r is not None and r.status == CheckResult.FAIL

    def test_phase5_underscore_variant_4_5(self, tmp_path):
        """phase-check 5: 4_5 key variant accepted."""
        docs = _make_docs(tmp_path)
        s = _base_state(tmp_path, docs)
        s["phases"]["4"] = {"status": "completed"}
        s["phases"].pop("4.5", None)
        s["phases"]["4_5"] = {"status": "completed"}
        results = _phase_check(s, docs, 5)
        r = _find(results, "phases.4.5.status")
        assert r is not None and r.status == CheckResult.PASS


# ---------------------------------------------------------------------------
# Integration: cmd_gate_check / cmd_phase_check (via state file on disk)
# ---------------------------------------------------------------------------

class TestCmdGateCheck:
    def _make_state_file(self, tmp_path, state):
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir(exist_ok=True)
        state.setdefault("docs_dir", str(docs_dir))
        sf = tmp_path / ".jarfis-state.json"
        sf.write_text(json.dumps(state))
        return str(sf)

    def test_gate1_pass(self, tmp_path, capsys):
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "press-release.md").write_text("")
        (docs_dir / "prd.md").write_text("")
        state = {
            "docs_dir": str(docs_dir),
            "phases": {"1": {"status": "completed", "ratchet": {"prd_score": 80}}},
        }
        sf = self._make_state_file(tmp_path, state)
        # Should not raise SystemExit
        cmd_gate_check([sf, "1"])
        out = json.loads(capsys.readouterr().out)
        assert out["result"] == "PASS"

    def test_gate1_fail_exits_1(self, tmp_path, capsys):
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        # Missing both files
        state = {
            "docs_dir": str(docs_dir),
            "phases": {"1": {"status": "pending"}},
        }
        sf = self._make_state_file(tmp_path, state)
        with pytest.raises(SystemExit) as exc:
            cmd_gate_check([sf, "1"])
        assert exc.value.code == 1
        out = json.loads(capsys.readouterr().out)
        assert out["result"] == "FAIL"
        assert "missing" in out

    def test_invalid_gate_number_exits(self, tmp_path):
        state = {"docs_dir": str(tmp_path / "docs"), "phases": {}}
        sf = self._make_state_file(tmp_path, state)
        with pytest.raises(SystemExit):
            cmd_gate_check([sf, "9"])

    def test_missing_state_file_exits(self, tmp_path):
        with pytest.raises(SystemExit):
            cmd_gate_check([str(tmp_path / "nonexistent.json"), "1"])

    def test_non_integer_gate_exits(self, tmp_path):
        state = {"docs_dir": str(tmp_path / "docs"), "phases": {}}
        sf = self._make_state_file(tmp_path, state)
        with pytest.raises(SystemExit):
            cmd_gate_check([sf, "abc"])

    def test_gate2_pass(self, tmp_path, capsys):
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        for f in GATE2_ALWAYS_REQUIRED:
            (docs_dir / f).write_text("")
        state = {
            "docs_dir": str(docs_dir),
            "phases": {
                "2": {"status": "completed"},
                "3": {"status": "skipped"},
            },
            "required_roles": {"frontend": False, "ux_designer": False},
            "api_spec_required": False,
        }
        sf = self._make_state_file(tmp_path, state)
        cmd_gate_check([sf, "2"])
        out = json.loads(capsys.readouterr().out)
        assert out["result"] == "PASS"

    def test_gate3_pass(self, tmp_path, capsys):
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "review.md").write_text("")
        (docs_dir / "deployment-plan.md").write_text("")
        state = {
            "docs_dir": str(docs_dir),
            "phases": {
                "4": {"status": "completed"},
                "4.5": {"status": "completed"},
                "5": {"status": "in_progress"},
            },
            "required_roles": {"devops": False, "frontend": True, "ux_designer": False},
            "phase5_agents": {"tech_lead": "completed", "qa": "completed", "security": "completed"},
        }
        sf = self._make_state_file(tmp_path, state)
        cmd_gate_check([sf, "3"])
        out = json.loads(capsys.readouterr().out)
        assert out["result"] == "PASS"


class TestCmdPhaseCheck:
    def _make_state_file(self, tmp_path, state):
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir(exist_ok=True)
        state.setdefault("docs_dir", str(docs_dir))
        sf = tmp_path / ".jarfis-state.json"
        sf.write_text(json.dumps(state))
        return str(sf)

    def test_phase2_pass(self, tmp_path, capsys):
        state = {
            "docs_dir": str(tmp_path / "docs"),
            "phases": {"1": {"status": "completed"}},
            "gate_results": {"gate1": {"decision": "approved"}},
            "required_roles": {"frontend": False},
            "api_spec_required": False,
        }
        sf = self._make_state_file(tmp_path, state)
        cmd_phase_check([sf, "2"])
        out = json.loads(capsys.readouterr().out)
        assert out["result"] == "PASS"

    def test_phase2_fail_exits_1(self, tmp_path, capsys):
        state = {
            "docs_dir": str(tmp_path / "docs"),
            "phases": {"1": {"status": "pending"}},
            "gate_results": {},
        }
        sf = self._make_state_file(tmp_path, state)
        with pytest.raises(SystemExit) as exc:
            cmd_phase_check([sf, "2"])
        assert exc.value.code == 1

    def test_phase4_pass(self, tmp_path, capsys):
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir(exist_ok=True)
        for f in GATE2_ALWAYS_REQUIRED:
            (docs_dir / f).write_text("")
        state = {
            "docs_dir": str(docs_dir),
            "phases": {"2": {"status": "completed"}},
            "gate_results": {"gate2": {"decision": "approved"}},
        }
        sf = self._make_state_file(tmp_path, state)
        cmd_phase_check([sf, "4"])
        out = json.loads(capsys.readouterr().out)
        assert out["result"] == "PASS"

    def test_missing_state_file_exits(self, tmp_path):
        with pytest.raises(SystemExit):
            cmd_phase_check([str(tmp_path / "ghost.json"), "2"])
