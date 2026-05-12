"""JARFIS Verify -- Programmatic verification entry point (v4).

Unified verify module combining Gate/Phase pre-checks with v4 phase-verify
and pattern-detect. Former name: gate_check.py (renamed at M1).

Subcommands:
    gate-check     <state_file> <gate_number>     -- Gate 1/2/3 prerequisite check
    phase-check    <state_file> <phase_number>    -- Phase-start prerequisite check
    phase-verify   <state_file> <phase_id>        -- Per-phase output verification
    pattern-detect <review_md_path>               -- Review pattern detection

Routing:
    * v4: `jarfis_cli.py {gate-check|phase-check|phase-verify|pattern-detect}`
    * v3 alias (M7까지 유지): `jarfis_cli.py state {gate-check|phase-check}`

Exit code 0 = PASS, 1 = FAIL.

Phase-별 체크리스트 명세: implement-plan.md §A.7.
"""

import datetime
import json
import os
import re
import sys
import time
from pathlib import Path

from . import trace, verify_helpers as _h
from .utils import json_error, json_output


# ---------------------------------------------------------------------------
# Helper: resolve nested value from state dict by dot-path
# ---------------------------------------------------------------------------
def _get_nested(data, path, default=None):
    """Traverse a dict by dot-separated path. Returns *default* if missing."""
    keys = path.split(".")
    val = data
    for k in keys:
        if isinstance(val, dict) and k in val:
            val = val[k]
        else:
            return default
    return val


def _to_kebab(text):
    """Convert a title string to kebab-case for directory naming.

    Examples:
        "Benefits Signup" -> "benefits-signup"
        "구매내역" -> "구매내역"  (Korean stays as-is, only spaces/special chars)
    """
    s = text.strip().lower()
    s = re.sub(r"[^a-z0-9가-힣ぁ-ゔァ-ヴー\s-]", "", s)
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"-+", "-", s)
    return s.strip("-")


# ---------------------------------------------------------------------------
# Check result data class
# ---------------------------------------------------------------------------
class CheckResult:
    """Single prerequisite check outcome."""

    __slots__ = ("label", "status", "detail")

    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"

    def __init__(self, label, status, detail=""):
        self.label = label
        self.status = status
        self.detail = detail

    def to_dict(self):
        d = {"label": self.label, "status": self.status}
        if self.detail:
            d["detail"] = self.detail
        return d

    def line(self):
        tag = f"[{self.status}]"
        parts = [tag, self.label]
        if self.detail:
            parts.append(f"({self.detail})")
        return " ".join(parts)


# ---------------------------------------------------------------------------
# File existence checker (handles both file and directory)
# ---------------------------------------------------------------------------
def _check_file(docs_dir, rel_path, is_dir=False):
    """Return True if the artifact exists at docs_dir/rel_path."""
    full = os.path.join(docs_dir, rel_path)
    if is_dir:
        return os.path.isdir(full)
    return os.path.isfile(full)


# ---------------------------------------------------------------------------
# Gate 1 prerequisites
# ---------------------------------------------------------------------------
def _gate1_checks(state, docs_dir):
    """Prerequisites for Gate 1 (end of Phase 1 Discovery)."""
    results = []

    # -- Required files --
    for f in ("discovery/working-backwards.md", "discovery/prd.md"):
        if _check_file(docs_dir, f):
            results.append(CheckResult(f"{f} exists", CheckResult.PASS))
        else:
            results.append(CheckResult(f"{f} missing", CheckResult.FAIL))

    # -- Phase status --
    p1_status = _get_nested(state, "phases.1.status", "pending")
    if p1_status == "completed":
        results.append(
            CheckResult(
                "phases.1.status",
                CheckResult.PASS,
                f"status={p1_status}",
            )
        )
    else:
        # Not a hard fail -- ratchet + artifacts are the real signal.
        # But if status is still pending, it is a problem.
        if p1_status == "pending":
            results.append(
                CheckResult(
                    "phases.1.status",
                    CheckResult.FAIL,
                    f"status={p1_status} (Phase 1 not started)",
                )
            )
        else:
            # in_progress is OK -- gate can be presented after artifacts exist.
            results.append(
                CheckResult(
                    "phases.1.status",
                    CheckResult.PASS,
                    f"status={p1_status}",
                )
            )

    return results


# ---------------------------------------------------------------------------
# Gate 2 prerequisites
# ---------------------------------------------------------------------------
def _gate2_checks(state, docs_dir):
    """Prerequisites for Gate 2 (end of Phase 2 Architecture + Phase 3 UX)."""
    results = []

    # -- Always-required Phase 2 artifacts (produced under planning/ by phase2.md) --
    always_required = [
        "planning/architecture.md",
        "planning/tasks.md",
        "planning/test-strategy.md",
    ]
    for f in always_required:
        if _check_file(docs_dir, f):
            results.append(CheckResult(f"{f} exists", CheckResult.PASS))
        else:
            results.append(CheckResult(f"{f} missing", CheckResult.FAIL))

    # -- Conditional: api-spec.md --
    api_spec_required = state.get("api_spec_required")
    if api_spec_required is None:
        be = _get_nested(state, "required_roles.backend", False)
        fe = _get_nested(state, "required_roles.frontend", False)
        api_spec_required = bool(be and fe)
    if api_spec_required:
        if _check_file(docs_dir, "planning/api-spec.md"):
            results.append(
                CheckResult(
                    "planning/api-spec.md exists",
                    CheckResult.PASS,
                    "api_spec_required=true",
                )
            )
        else:
            results.append(
                CheckResult(
                    "planning/api-spec.md missing",
                    CheckResult.FAIL,
                    "api_spec_required=true",
                )
            )
    else:
        results.append(
            CheckResult(
                "planning/api-spec.md",
                CheckResult.SKIP,
                "api_spec_required=false",
            )
        )

    # -- Conditional: ux-direction.md (produced under discovery/ by phase1b.md) --
    ux_needed = _get_nested(state, "required_roles.ux_designer", False)
    if ux_needed:
        if _check_file(docs_dir, "discovery/ux-direction.md"):
            results.append(
                CheckResult(
                    "discovery/ux-direction.md exists",
                    CheckResult.PASS,
                    "required_roles.ux_designer=true",
                )
            )
        else:
            results.append(
                CheckResult(
                    "discovery/ux-direction.md missing",
                    CheckResult.FAIL,
                    "required_roles.ux_designer=true",
                )
            )
    else:
        results.append(
            CheckResult(
                "discovery/ux-direction.md",
                CheckResult.SKIP,
                "required_roles.ux_designer=false",
            )
        )

    # -- Conditional: design/ artifacts --
    fe_needed = _get_nested(state, "required_roles.frontend", False)
    phase3_status = _get_nested(state, "phases.3.status", "pending")
    phase3_mode = _get_nested(state, "phases.3.mode")
    has_designer = _get_nested(state, "phases.3.has_designer")

    # Phase 3 is only required when BOTH FE + UX Designer are needed
    phase3_should_run = fe_needed and ux_needed

    if not phase3_should_run:
        # Phase 3 skipped -- no design files needed
        results.append(
            CheckResult(
                "design/ artifacts",
                CheckResult.SKIP,
                f"Phase 3 not needed (frontend={fe_needed}, ux_designer={ux_needed})",
            )
        )
    elif phase3_status == "skipped":
        # Explicitly skipped -- acceptable
        reason = _get_nested(state, "phases.3.reason", "")
        results.append(
            CheckResult(
                "design/ artifacts",
                CheckResult.SKIP,
                f"Phase 3 explicitly skipped: {reason}" if reason else "Phase 3 explicitly skipped",
            )
        )
    elif phase3_mode == "figma":
        # Figma mode -- expect design/{kebab-title}/reference.png per page
        figma_pages = _get_nested(state, "phases.3.figma_pages", [])
        if not figma_pages:
            results.append(
                CheckResult(
                    "design/ figma pages",
                    CheckResult.FAIL,
                    "phases.3.mode=figma but figma_pages is empty",
                )
            )
        else:
            for page in figma_pages:
                title = page.get("title", "")
                kebab = _to_kebab(title) if title else ""
                if not kebab:
                    results.append(
                        CheckResult(
                            f"design/ page '{title}'",
                            CheckResult.FAIL,
                            "page title is empty or invalid",
                        )
                    )
                    continue

                # In figma mode: reference.png + index.html per page
                ref_path = f"design/{kebab}/reference.png"
                idx_path = f"design/{kebab}/index.html"

                if _check_file(docs_dir, ref_path):
                    results.append(
                        CheckResult(
                            f"{ref_path} exists",
                            CheckResult.PASS,
                        )
                    )
                else:
                    results.append(
                        CheckResult(
                            f"{ref_path} missing",
                            CheckResult.FAIL,
                            f"phases.3.mode=figma, page='{title}'",
                        )
                    )

                if _check_file(docs_dir, idx_path):
                    results.append(
                        CheckResult(
                            f"{idx_path} exists",
                            CheckResult.PASS,
                        )
                    )
                else:
                    results.append(
                        CheckResult(
                            f"{idx_path} missing",
                            CheckResult.FAIL,
                            f"phases.3.mode=figma, page='{title}'",
                        )
                    )

            # Also check _index.html (table of contents)
            if _check_file(docs_dir, "design/_index.html"):
                results.append(
                    CheckResult("design/_index.html exists", CheckResult.PASS)
                )
            else:
                results.append(
                    CheckResult(
                        "design/_index.html missing",
                        CheckResult.FAIL,
                        "phases.3.mode=figma",
                    )
                )

    elif phase3_mode == "text":
        # Text mode -- expect design/**/index.html + _index.html
        design_dir = os.path.join(docs_dir, "design")
        if not os.path.isdir(design_dir):
            results.append(
                CheckResult(
                    "design/ directory missing",
                    CheckResult.FAIL,
                    "phases.3.mode=text",
                )
            )
        else:
            # Must have at least one index.html in a subdirectory
            has_any_html = False
            for root, _dirs, files in os.walk(design_dir):
                for fname in files:
                    if fname == "index.html" and root != design_dir:
                        has_any_html = True
                        break
                if has_any_html:
                    break

            if has_any_html:
                results.append(
                    CheckResult(
                        "design/ has HTML mockups",
                        CheckResult.PASS,
                        "phases.3.mode=text",
                    )
                )
            else:
                results.append(
                    CheckResult(
                        "design/ has no HTML mockups",
                        CheckResult.FAIL,
                        "phases.3.mode=text, expected design/{path}/index.html",
                    )
                )

            # _index.html (table of contents)
            if _check_file(docs_dir, "design/_index.html"):
                results.append(
                    CheckResult("design/_index.html exists", CheckResult.PASS)
                )
            else:
                results.append(
                    CheckResult(
                        "design/_index.html missing",
                        CheckResult.FAIL,
                        "phases.3.mode=text",
                    )
                )

            # reference.png -- in text mode, generated by Step 3-2
            # Check for at least one reference.png in design subdirectories
            has_ref = False
            for root, _dirs, files in os.walk(design_dir):
                if "reference.png" in files and root != design_dir:
                    has_ref = True
                    break
            if has_ref:
                results.append(
                    CheckResult(
                        "design/ has reference.png",
                        CheckResult.PASS,
                        "phases.3.mode=text, Step 3-2 completed",
                    )
                )
            else:
                results.append(
                    CheckResult(
                        "design/ reference.png missing",
                        CheckResult.FAIL,
                        "phases.3.mode=text, Step 3-2 not completed",
                    )
                )
    elif phase3_mode == "supplied":
        # Supplied mode (design-supplied-mode-v1, Step 2) -- the design tree
        # was copied verbatim from state.design.suppliedPath into
        # $DOCS_DIR/design/. Layout: design/pages/{slug}/index.html +
        # reference.png (responsive PNGs are filled in by the foreman, not
        # required at Gate 2). SSOT: ia.json / sitemap.md are NOT auto-
        # generated; their absence is acceptable here.
        design_dir = os.path.join(docs_dir, "design")
        if not os.path.isdir(design_dir):
            results.append(
                CheckResult(
                    "design/ directory missing",
                    CheckResult.FAIL,
                    "phases.3.mode=supplied",
                )
            )
        else:
            pages_dir = os.path.join(design_dir, "pages")
            if not os.path.isdir(pages_dir):
                results.append(
                    CheckResult(
                        "design/pages/ missing",
                        CheckResult.FAIL,
                        "phases.3.mode=supplied — supplied 시안은 pages/{slug}/ 구조 의무",
                    )
                )
            else:
                has_valid_page = False
                for slug in sorted(os.listdir(pages_dir)):
                    page_dir = os.path.join(pages_dir, slug)
                    if not os.path.isdir(page_dir):
                        continue
                    idx = os.path.join(page_dir, "index.html")
                    ref = os.path.join(page_dir, "reference.png")
                    if os.path.isfile(idx) and os.path.isfile(ref):
                        has_valid_page = True
                        results.append(
                            CheckResult(
                                f"design/pages/{slug}/ valid",
                                CheckResult.PASS,
                            )
                        )
                    else:
                        results.append(
                            CheckResult(
                                f"design/pages/{slug}/ incomplete",
                                CheckResult.FAIL,
                                "missing index.html or reference.png",
                            )
                        )
                if not has_valid_page:
                    results.append(
                        CheckResult(
                            "design/pages/ has no valid page",
                            CheckResult.FAIL,
                            "최소 1개 page 가 index.html + reference.png 동봉 필요",
                        )
                    )

        # Mutual exclusion (Critic blocker #4): when mode=="supplied",
        # figmaPages must be empty. Reading both phases.3.figma_pages
        # (legacy) and design.figmaPages (v4 nested) so any leftover from a
        # mode switch trips the check.
        figma_pages = (
            _get_nested(state, "phases.3.figma_pages", [])
            or _get_nested(state, "design.figmaPages", [])
        )
        if figma_pages:
            results.append(
                CheckResult(
                    "figmaPages mutual exclusion violated",
                    CheckResult.FAIL,
                    "phases.3.mode=supplied 인데 figmaPages 가 비어있지 않음 — mode 전환 시 reset 누락",
                )
            )

    else:
        # mode is not set but Phase 3 should run -- something is wrong
        if phase3_status in ("pending", "in_progress"):
            results.append(
                CheckResult(
                    "design/ artifacts",
                    CheckResult.FAIL,
                    f"Phase 3 status={phase3_status}, mode not set",
                )
            )
        else:
            results.append(
                CheckResult(
                    "design/ artifacts",
                    CheckResult.FAIL,
                    f"Phase 3 status={phase3_status}, mode={phase3_mode}",
                )
            )

    # -- Phase statuses --
    p2_status = _get_nested(state, "phases.2.status", "pending")
    if p2_status == "completed":
        results.append(
            CheckResult("phases.2.status", CheckResult.PASS, f"status={p2_status}")
        )
    else:
        results.append(
            CheckResult("phases.2.status", CheckResult.FAIL, f"status={p2_status}")
        )

    if phase3_should_run:
        if phase3_status in ("completed", "skipped"):
            results.append(
                CheckResult(
                    "phases.3.status",
                    CheckResult.PASS,
                    f"status={phase3_status}",
                )
            )
        else:
            results.append(
                CheckResult(
                    "phases.3.status",
                    CheckResult.FAIL,
                    f"status={phase3_status}",
                )
            )
    else:
        results.append(
            CheckResult(
                "phases.3.status",
                CheckResult.SKIP,
                "Phase 3 not needed",
            )
        )

    return results


# ---------------------------------------------------------------------------
# Gate 3 prerequisites
# ---------------------------------------------------------------------------
def _gate3_checks(state, docs_dir):
    """Prerequisites for Gate 3 (end of Phase 5 Review & QA)."""
    results = []

    # -- review.md (always required) --
    if _check_file(docs_dir, "review.md"):
        results.append(CheckResult("review.md exists", CheckResult.PASS))
    else:
        results.append(CheckResult("review.md missing", CheckResult.FAIL))

    # -- api-contract-check.md (conditional: when api-spec.md exists) --
    api_spec_exists = _check_file(docs_dir, "api-spec.md")
    if api_spec_exists:
        if _check_file(docs_dir, "api-contract-check.md"):
            results.append(
                CheckResult(
                    "api-contract-check.md exists",
                    CheckResult.PASS,
                    "api-spec.md exists",
                )
            )
        else:
            results.append(
                CheckResult(
                    "api-contract-check.md missing",
                    CheckResult.FAIL,
                    "api-spec.md exists, Step 5-0 not executed",
                )
            )
    else:
        results.append(
            CheckResult(
                "api-contract-check.md",
                CheckResult.SKIP,
                "api-spec.md does not exist",
            )
        )

    # -- deployment-plan.md (Phase 4.5 artifact, should exist before Gate 3) --
    if _check_file(docs_dir, "deployment-plan.md"):
        results.append(CheckResult("deployment-plan.md exists", CheckResult.PASS))
    else:
        results.append(
            CheckResult(
                "deployment-plan.md missing",
                CheckResult.FAIL,
                "Phase 4.5 artifact",
            )
        )

    # -- Phase statuses --
    # Phase 4 must be completed
    p4_status = _get_nested(state, "phases.4.status", "pending")
    if p4_status == "completed":
        results.append(
            CheckResult("phases.4.status", CheckResult.PASS, f"status={p4_status}")
        )
    else:
        results.append(
            CheckResult("phases.4.status", CheckResult.FAIL, f"status={p4_status}")
        )

    # Phase 4.5 must be completed
    # Handle both "4.5" and "4_5" key variants (orchestrator may use either)
    # If EITHER variant is "completed", treat as completed
    phases = state.get("phases", {})
    p45_a = phases.get("4.5", {})
    p45_b = phases.get("4_5", {})
    p45_status_a = p45_a.get("status", "pending") if isinstance(p45_a, dict) else "pending"
    p45_status_b = p45_b.get("status", "pending") if isinstance(p45_b, dict) else "pending"
    p45_status = "completed" if "completed" in (p45_status_a, p45_status_b) else p45_status_a
    if p45_status == "completed":
        results.append(
            CheckResult("phases.4.5.status", CheckResult.PASS, f"status={p45_status}")
        )
    else:
        results.append(
            CheckResult(
                "phases.4.5.status", CheckResult.FAIL, f"status={p45_status}"
            )
        )

    # Phase 5 should be in_progress or completed (review has been done)
    p5_status = _get_nested(state, "phases.5.status", "pending")
    if p5_status in ("in_progress", "completed"):
        results.append(
            CheckResult("phases.5.status", CheckResult.PASS, f"status={p5_status}")
        )
    else:
        results.append(
            CheckResult("phases.5.status", CheckResult.FAIL, f"status={p5_status}")
        )

    # -- Phase 5 agent execution records --
    # Validate that all required review agents were actually spawned
    phase5_agents = state.get("phase5_agents", {})
    required_review_agents = ["tech_lead", "qa", "security"]
    ux_needed = _get_nested(state, "required_roles.ux_designer", False)
    fe_needed = _get_nested(state, "required_roles.frontend", False)
    if ux_needed and fe_needed:
        required_review_agents.append("ux_designer")

    for agent_role in required_review_agents:
        agent_status = phase5_agents.get(agent_role)
        if agent_status == "completed":
            results.append(
                CheckResult(
                    f"phase5_agents.{agent_role}",
                    CheckResult.PASS,
                    f"status={agent_status}",
                )
            )
        else:
            results.append(
                CheckResult(
                    f"phase5_agents.{agent_role} missing",
                    CheckResult.FAIL,
                    f"required review agent not executed (status={agent_status})",
                )
            )

    # -- infra-runbook.md (conditional: when DevOps executes) --
    devops_needed = _get_nested(state, "required_roles.devops", False)
    devops_agent_status = _get_nested(state, "phase4_agents.devops")
    if devops_needed and devops_agent_status not in (None, "skipped"):
        if _check_file(docs_dir, "infra-runbook.md"):
            results.append(
                CheckResult(
                    "infra-runbook.md exists",
                    CheckResult.PASS,
                    "devops executed",
                )
            )
        else:
            results.append(
                CheckResult(
                    "infra-runbook.md missing",
                    CheckResult.FAIL,
                    "devops executed but infra-runbook.md not found",
                )
            )
    else:
        results.append(
            CheckResult(
                "infra-runbook.md",
                CheckResult.SKIP,
                f"devops={devops_needed}, agent_status={devops_agent_status}",
            )
        )

    return results


# ---------------------------------------------------------------------------
# Phase-check: validate preconditions before starting a phase
# ---------------------------------------------------------------------------
def _phase_check(state, docs_dir, phase_number):
    """Validate preconditions before starting a specific phase."""
    results = []

    if phase_number == 2:
        # Phase 2 start: Gate 1 must be approved
        g1 = _get_nested(state, "gate_results.gate1.decision")
        if g1 == "approved":
            results.append(
                CheckResult("gate_results.gate1.decision", CheckResult.PASS, "approved")
            )
        else:
            results.append(
                CheckResult(
                    "gate_results.gate1.decision",
                    CheckResult.FAIL,
                    f"decision={g1} (Gate 1 not approved)",
                )
            )

        # Phase 1 must be completed
        p1_status = _get_nested(state, "phases.1.status", "pending")
        if p1_status == "completed":
            results.append(
                CheckResult("phases.1.status", CheckResult.PASS, f"status={p1_status}")
            )
        else:
            results.append(
                CheckResult(
                    "phases.1.status",
                    CheckResult.FAIL,
                    f"status={p1_status}",
                )
            )

        # Swagger/API parameter extraction validation (when FE + external APIs)
        fe_needed = _get_nested(state, "required_roles.frontend", False)
        api_spec_required = state.get("api_spec_required", False)
        if fe_needed and api_spec_required:
            # Swagger URL might be stored in state -- validate the field exists
            # This is a soft check: warn if api_spec_required but no workspace FE
            results.append(
                CheckResult(
                    "API spec extraction readiness",
                    CheckResult.PASS,
                    f"api_spec_required={api_spec_required}, frontend={fe_needed}",
                )
            )

    elif phase_number == 4:
        # Phase 4 start: Gate 2 must be approved
        g2 = _get_nested(state, "gate_results.gate2.decision")
        if g2 == "approved":
            results.append(
                CheckResult("gate_results.gate2.decision", CheckResult.PASS, "approved")
            )
        else:
            results.append(
                CheckResult(
                    "gate_results.gate2.decision",
                    CheckResult.FAIL,
                    f"decision={g2} (Gate 2 not approved)",
                )
            )

        # Phase 2 must be completed
        p2_status = _get_nested(state, "phases.2.status", "pending")
        if p2_status == "completed":
            results.append(
                CheckResult("phases.2.status", CheckResult.PASS, f"status={p2_status}")
            )
        else:
            results.append(
                CheckResult(
                    "phases.2.status", CheckResult.FAIL, f"status={p2_status}"
                )
            )

        # Required Phase 2 artifacts (produced under planning/ by phase2.md)
        for f in ("planning/architecture.md", "planning/tasks.md", "planning/test-strategy.md"):
            if _check_file(docs_dir, f):
                results.append(CheckResult(f"{f} exists", CheckResult.PASS))
            else:
                results.append(CheckResult(f"{f} missing", CheckResult.FAIL))

    elif phase_number == 5:
        # Phase 5 start: Phase 4 + 4.5 must be completed
        p4_status = _get_nested(state, "phases.4.status", "pending")
        if p4_status == "completed":
            results.append(
                CheckResult("phases.4.status", CheckResult.PASS, f"status={p4_status}")
            )
        else:
            results.append(
                CheckResult(
                    "phases.4.status", CheckResult.FAIL, f"status={p4_status}"
                )
            )

        phases = state.get("phases", {})
        p45_a = phases.get("4.5", {})
        p45_b = phases.get("4_5", {})
        p45_sa = p45_a.get("status", "pending") if isinstance(p45_a, dict) else "pending"
        p45_sb = p45_b.get("status", "pending") if isinstance(p45_b, dict) else "pending"
        p45_status = "completed" if "completed" in (p45_sa, p45_sb) else p45_sa
        if p45_status == "completed":
            results.append(
                CheckResult(
                    "phases.4.5.status", CheckResult.PASS, f"status={p45_status}"
                )
            )
        else:
            results.append(
                CheckResult(
                    "phases.4.5.status", CheckResult.FAIL, f"status={p45_status}"
                )
            )

    elif phase_number == 6:
        # Phase 6 start: Gate 3 must be approved
        g3 = _get_nested(state, "gate_results.gate3.decision")
        if g3 == "approved":
            results.append(
                CheckResult("gate_results.gate3.decision", CheckResult.PASS, "approved")
            )
        else:
            results.append(
                CheckResult(
                    "gate_results.gate3.decision",
                    CheckResult.FAIL,
                    f"decision={g3} (Gate 3 not approved)",
                )
            )

        # Phase 5 must be completed
        p5_status = _get_nested(state, "phases.5.status", "pending")
        if p5_status == "completed":
            results.append(
                CheckResult("phases.5.status", CheckResult.PASS, f"status={p5_status}")
            )
        else:
            results.append(
                CheckResult(
                    "phases.5.status", CheckResult.FAIL, f"status={p5_status}"
                )
            )
    else:
        results.append(
            CheckResult(
                f"Phase {phase_number}",
                CheckResult.SKIP,
                "No pre-checks defined for this phase",
            )
        )

    return results


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------
def cmd_gate_check(args):
    """Main entry: gate-check <state_file> <gate_number>"""
    if len(args) < 2:
        json_error("Usage: jarfis state gate-check <state_file> <gate_number>")

    state_file = args[0]
    try:
        gate_number = int(args[1])
    except ValueError:
        json_error(f"gate_number must be integer, got: {args[1]}")

    if gate_number not in (1, 2, 3):
        json_error(f"gate_number must be 1, 2, or 3, got: {gate_number}")

    if not os.path.isfile(state_file):
        json_error("State file not found", path=state_file)

    with open(state_file) as f:
        state = json.load(f)

    docs_dir = state.get("docs_dir", "")
    if not docs_dir:
        json_error("docs_dir not set in state file")

    gate_funcs = {1: _gate1_checks, 2: _gate2_checks, 3: _gate3_checks}
    results = gate_funcs[gate_number](state, docs_dir)

    _print_results(f"Gate {gate_number}", results)


def cmd_phase_check(args):
    """Main entry: phase-check <state_file> <phase_number>"""
    if len(args) < 2:
        json_error("Usage: jarfis state phase-check <state_file> <phase_number>")

    state_file = args[0]
    try:
        phase_number = int(args[1])
    except ValueError:
        json_error(f"phase_number must be integer, got: {args[1]}")

    if not os.path.isfile(state_file):
        json_error("State file not found", path=state_file)

    with open(state_file) as f:
        state = json.load(f)

    docs_dir = state.get("docs_dir", "")
    if not docs_dir:
        json_error("docs_dir not set in state file")

    results = _phase_check(state, docs_dir, phase_number)
    _print_results(f"Phase {phase_number} Pre-Check", results)


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------
def _print_results(title, results):
    """Print human-readable check results and JSON, set exit code."""
    passed = sum(1 for r in results if r.status == CheckResult.PASS)
    failed = sum(1 for r in results if r.status == CheckResult.FAIL)
    skipped = sum(1 for r in results if r.status == CheckResult.SKIP)

    lines = [f"{title} Prerequisites Check", "=" * 40]
    for r in results:
        lines.append(r.line())

    lines.append("")
    if failed == 0:
        lines.append(f"Result: PASS ({passed} passed, {skipped} skipped)")
    else:
        lines.append(f"Result: FAIL ({failed} missing, {passed} passed, {skipped} skipped)")
        missing = [r.label for r in results if r.status == CheckResult.FAIL]
        lines.append(f"Missing: {', '.join(missing)}")

    # Print human-readable to stderr
    print("\n".join(lines), file=sys.stderr)

    # Print JSON to stdout for programmatic consumption
    json_data = {
        "gate": title,
        "result": "PASS" if failed == 0 else "FAIL",
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "checks": [r.to_dict() for r in results],
    }
    if failed > 0:
        json_data["missing"] = [r.label for r in results if r.status == CheckResult.FAIL]

    print(json.dumps(json_data, ensure_ascii=False))

    if failed > 0:
        sys.exit(1)


# ---------------------------------------------------------------------------
# v4 phase-verify — Phase별 기계적 출력 검증 (M3)
#
# Contract: (state, docs_dir) -> list[str]  (빈 리스트 = PASS, 각 엔트리 = FAIL 사유 한글)
# 체크리스트 완전 명세: implement-plan.md §A.7.
# ---------------------------------------------------------------------------
def _parse_tasks_md_ids(tasks_md_path):
    """tasks.md 에서 `- [ ] {task_id}` 패턴의 task id 목록 추출."""
    p = Path(tasks_md_path)
    if not p.is_file():
        return []
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    pattern = re.compile(r"^\s*-\s*\[[ xX]\]\s*([A-Za-z0-9._-]+)\b", re.MULTILINE)
    return [m.group(1) for m in pattern.finditer(text)]


def _phase_1b_verify(state, docs_dir):
    """Phase 1b: discovery/ 산출물 3종 + prd 섹션 4개 + IA validation.

    Stage 3 (ia-as-po-ssot-v2-spine F1 — forward-only auto-detect):
        IA validation gated on `discovery/ia/` directory existence. When
        present, run validate_ia (PO Phase 1b scope = L0-L1 only, so
        strict=False); baseline-missing is a **warning** (stderr), NOT a
        FAIL — D10 forward-only contract means pre-Stage-4 works that
        never ran snapshot_org_ia must still pass.

    Stage 8: ux-direction.md kebab-case ID check 제거 — IA R3 slug regex
        (ia.py:66) 가 대체. ux-direction.md 의 Pages 디테일은 IA pages/
        {slug}.md Notes body 로 흡수됨. ux-direction 파일 존재 자체는 여전히
        design.mode != null 일 때 강제 (Tone & Voice + supplied External
        Mockup Reference 보존).
    """
    missing = []
    discovery = Path(docs_dir) / "discovery"

    prd_path = discovery / "prd.md"
    if not _h.check_file_exists(prd_path):
        missing.append("discovery/prd.md 누락")
    else:
        for section in ("Required Roles", "Functional Requirements", "Success Metrics", "Scope"):
            if not _h.check_section_exists(prd_path, section):
                missing.append(f"discovery/prd.md '## {section}' 섹션 누락")

    if not _h.check_file_exists(discovery / "working-backwards.md"):
        missing.append("discovery/working-backwards.md 누락")

    if _h.design_required(state):
        ux_path = discovery / "ux-direction.md"
        mode = (state.get("design") or {}).get("mode")
        if not _h.check_file_exists(ux_path):
            missing.append(f"discovery/ux-direction.md 누락 (design.mode={mode})")

    # NEW: IA validation (Stage 3 F1 — conditional on dir existence).
    # PO Phase 1b owns SSOT but only L0-L1 are mandatory at this stage,
    # so we use strict=False to skip R10/R11 frontmatter completeness
    # rules until Phase 2 absorption.
    ia_dir = discovery / "ia"
    if ia_dir.is_dir():
        from .ia import validate_ia  # local import — keeps verify.py decoupled at module load
        result = validate_ia(str(ia_dir), strict=False)
        if not result.valid:
            missing.extend(f"discovery/ia: {e}" for e in result.errors)
        # baseline-missing = separate warning channel (D10 forward-only — F1).
        baseline = ia_dir / ".baseline" / "manifest.json"
        if not baseline.is_file():
            sys.stderr.write(
                "[phase-verify warning] phase=1b discovery/ia/.baseline/manifest.json missing "
                "(snapshot_org_ia 미실행; D10 forward-only — verify 는 통과)\n"
            )

    return missing


_TYPE_TITLE = {"frontend": "Frontend", "backend": "Backend", "devops": "DevOps"}


def _phase_2_verify(state, docs_dir):
    """Phase 2: planning/ 산출물 3종 + scope×type 섹션 + 조건부 api-spec.md."""
    missing = []
    planning = Path(docs_dir) / "planning"

    if not _h.check_file_exists(planning / "architecture.md"):
        missing.append("planning/architecture.md 누락")
    if not _h.check_file_exists(planning / "test-strategy.md"):
        missing.append("planning/test-strategy.md 누락")

    tasks_md = planning / "tasks.md"
    if not _h.check_file_exists(tasks_md):
        missing.append("planning/tasks.md 누락")
    else:
        for p in (state.get("workspace") or {}).get("scope", []):
            title = _TYPE_TITLE.get(p.get("type"), p.get("type", "?").capitalize())
            section = f"{title} Tasks — {p.get('name','?')}"
            if not _h.check_section_exists(tasks_md, section):
                missing.append(f"planning/tasks.md '## {section}' 섹션 누락")

    if _h.api_spec_required(state) and not _h.check_file_exists(planning / "api-spec.md"):
        reason = "backend scope" if _h.has_backend(state) else "api.mode=swagger"
        missing.append(f"planning/api-spec.md 누락 ({reason})")

    # NEW: IA L2 — tasks ↔ pages mapping (Stage 3).
    ia_dir = Path(docs_dir) / "discovery" / "ia"
    if ia_dir.is_dir():
        missing.extend(_h.check_ia_pages_match_tasks(ia_dir, tasks_md))

    return missing


def _phase_3_verify(state, docs_dir):
    """Phase 3: design/ 디렉토리 + id별 index.html/reference.png + responsive 변종 + token-map.json.

    For ``state.design.mode == "supplied"`` (design-supplied-mode-v1, Step
    2), the verifier expects the supplied tree at
    ``design/pages/{slug}/index.html`` + ``reference.png``. token-map.json
    and ux-direction.md are NOT required (SSOT — only the supplied tree
    counts; Critic blocker #3 absorption). Mutual exclusion against
    ``design.figmaPages`` is enforced as a final guard.
    """
    missing = []
    design_dir = Path(docs_dir) / "design"

    design = state.get("design") or {}
    mode = design.get("mode")

    # TODO(Stage 4 — phase1b prompt rewrite): re-enable IA pages match for supplied mode
    # once PO SSOT import-then-discard contract is wired in prompts/phase1b.md.
    # Until then, supplied designer slugs and PO IA slugs may diverge legitimately
    # (Stage 3 dialectic F2 absorption).
    if mode == "supplied":
        if not design_dir.is_dir():
            missing.append("design/ 디렉토리 누락")
            return missing

        pages_dir = design_dir / "pages"
        if not pages_dir.is_dir():
            missing.append("design/pages/ 누락 (supplied 모드는 pages/{slug}/ 구조 의무)")
        else:
            has_valid_page = False
            for slug_dir in sorted(pages_dir.iterdir()):
                if not slug_dir.is_dir():
                    continue
                slug = slug_dir.name
                idx_ok = _h.check_file_nonempty(slug_dir / "index.html")
                ref_ok = _h.check_file_exists(slug_dir / "reference.png")
                if not idx_ok:
                    missing.append(
                        f"design/pages/{slug}/index.html 누락 또는 빈 파일"
                    )
                if not ref_ok:
                    missing.append(f"design/pages/{slug}/reference.png 누락")
                if idx_ok and ref_ok:
                    has_valid_page = True
            if not has_valid_page and not missing:
                # No page subdirectories at all (or all are empty)
                missing.append(
                    "design/pages/ 에 유효한 page 없음 (최소 1개 index.html + reference.png 필요)"
                )

        # Mutual exclusion (Critic blocker #4): supplied mode must have
        # empty figmaPages. Even if state.py.set_design_mode was bypassed,
        # verify.py rejects the state here.
        figma_pages = design.get("figmaPages") or []
        if figma_pages:
            missing.append(
                "figmaPages mutual exclusion 위반 — design.mode=supplied 인데 "
                "figmaPages 가 비어있지 않음 (mode 전환 시 reset 누락)"
            )

        return missing

    # Existing figma / text path -- unchanged behavior.
    if not design_dir.is_dir():
        missing.append("design/ 디렉토리 누락")
        return missing

    ids = _h.ux_direction_ids(Path(docs_dir) / "discovery" / "ux-direction.md")
    level = _h.responsive_level(state)
    need_mobile = level in ("pc-mobile", "pc-mobile-tablet")
    need_tablet = level == "pc-mobile-tablet"

    for uid in ids:
        page_dir = design_dir / uid
        index_html = page_dir / "index.html"
        if not _h.check_file_nonempty(index_html):
            missing.append(f"design/{uid}/index.html 누락 또는 빈 파일")
        if not _h.check_file_exists(page_dir / "reference.png"):
            missing.append(f"design/{uid}/reference.png 누락")
        if need_mobile and not _h.check_file_exists(page_dir / "reference-mobile.png"):
            missing.append(f"design/{uid}/reference-mobile.png 누락 (responsive={level})")
        if need_tablet and not _h.check_file_exists(page_dir / "reference-tablet.png"):
            missing.append(f"design/{uid}/reference-tablet.png 누락 (responsive={level})")

    if not _h.check_file_exists(design_dir / "token-map.json"):
        missing.append("design/token-map.json 누락")

    # NEW: IA L3 — design slugs ↔ IA pages 1:1 mapping (Stage 3; figma/text only).
    ia_dir = Path(docs_dir) / "discovery" / "ia"
    if ia_dir.is_dir():
        missing.extend(_h.check_ia_pages_match_design(ia_dir, design_dir, mode=mode))

    return missing


def _phase_4_verify(state, docs_dir):
    """Phase 4: task별 commit 매칭 + scope별 코드 변경 + devops/CSS var 조건부."""
    missing = []
    planning = Path(docs_dir) / "planning"
    tasks_md = planning / "tasks.md"
    token_map = Path(docs_dir) / "design" / "token-map.json"

    task_ids = _parse_tasks_md_ids(tasks_md) if tasks_md.is_file() else []
    scopes = (state.get("workspace") or {}).get("scope", [])

    for p in scopes:
        repo = p.get("path")
        base = p.get("baseCommit")
        name = p.get("name", "?")
        if not repo or not base:
            missing.append(f"scope {name}: path/baseCommit 누락 (state 손상)")
            continue

        # (a) task commit 매칭
        for tid in task_ids:
            if not _h.check_git_commit_for_task(repo, base, tid):
                missing.append(f"Phase 4 commit 누락: task {tid} (scope {name})")

        # (b) scope type별 코드 변경
        if not _h.check_code_changes(repo, base):
            missing.append(f"{p.get('type','?').upper()} 코드 변경 없음: scope {name} (baseCommit..HEAD)")

    if _h.has_devops(state):
        devops_globs = [
            "**/Dockerfile*", "**/docker-compose*.y*ml",
            "**/.github/workflows/*.y*ml", "**/terraform/**", "**/helm/**",
            "**/k8s/**", "**/kubernetes/**",
        ]
        any_change = any(
            _h.check_code_changes(p.get("path",""), p.get("baseCommit",""), devops_globs)
            for p in scopes if p.get("path") and p.get("baseCommit")
        )
        if not any_change:
            missing.append("DevOps 파일 변경 없음 (devops=true인데 infra 파일 diff 0)")

    if token_map.is_file() and _h.has_frontend(state):
        for p in scopes:
            if p.get("type") != "frontend":
                continue
            if not p.get("path") or not p.get("baseCommit"):
                continue
            if not _h.check_css_var_usage(p["path"], p["baseCommit"]):
                missing.append(
                    f"FE scope {p.get('name','?')}에서 CSS var(-- 사용 없음 (token-map.json 존재)"
                )

    # NEW: FE route ↔ IA route best-effort warning (Stage 3, R-8).
    # Pure stderr warnings — never escalate into missing[] (framework drift
    # would cause false positives across React/Vue/Next variants).
    ia_dir = Path(docs_dir) / "discovery" / "ia"
    if ia_dir.is_dir():
        for p in scopes:
            if p.get("type") != "frontend":
                continue
            warnings = _h.check_fe_routes_match_ia(
                p.get("path", ""), p.get("baseCommit", ""), ia_dir
            )
            for w in warnings:
                sys.stderr.write(f"[phase-verify warning] phase=4 {w}\n")

    return missing


def _phase_4_5_verify(state, docs_dir):
    """Phase 4.5: deployment-plan.md + devops=true 시 Rollback 섹션."""
    missing = []
    plan = Path(docs_dir) / "ops" / "deployment-plan.md"
    if not _h.check_file_exists(plan):
        missing.append("ops/deployment-plan.md 누락")
        return missing
    if _h.has_devops(state) and not _h.check_section_exists(plan, "Rollback"):
        missing.append("ops/deployment-plan.md '## Rollback' 섹션 누락 (devops=true)")
    return missing


def _phase_5_verify(state, docs_dir):
    """Phase 5: review.md + 프로젝트×역할 소섹션 + UX/api-contract 조건부."""
    missing = []
    review_md = Path(docs_dir) / "review" / "review.md"
    if not _h.check_file_exists(review_md):
        missing.append("review/review.md 누락")
        return missing

    for p in (state.get("workspace") or {}).get("scope", []):
        name = p.get("name", "?")
        if not _h.check_section_exists(review_md, name, level=3):
            missing.append(f"review/review.md '### {name}' 섹션 누락")
            continue
        for role in ("Tech Lead", "QA", "Security"):
            if not _h.check_section_exists(review_md, role, level=4):
                missing.append(f"review/review.md '{name}' 내 '#### {role}' 소섹션 누락")

    if _h.design_required(state) and not _h.check_section_exists(review_md, "UX Design Review"):
        missing.append("review/review.md '## UX Design Review' 섹션 누락")

    if _h.check_file_exists(Path(docs_dir) / "planning" / "api-spec.md"):
        if not _h.check_file_exists(Path(docs_dir) / "review" / "api-contract-check.md"):
            missing.append("review/api-contract-check.md 누락 (api-spec.md 존재)")

    # NEW: review.md page coverage ↔ IA pages (Stage 3).
    ia_dir = Path(docs_dir) / "discovery" / "ia"
    if ia_dir.is_dir():
        missing.extend(_h.check_ia_pages_match_review(ia_dir, review_md))

    return missing


def _phase_6_verify(state, docs_dir):
    """Phase 6: retrospective.md + org 등록 시 wiki/INDEX.md 갱신 commit + docsDir 위치(D5)."""
    missing = []
    retro = Path(docs_dir) / "retrospective.md"
    if not _h.check_file_exists(retro):
        missing.append("retrospective.md 누락")

    if _h.org_registered(state):
        org = state["org"]
        org_root = org.get("root")
        org_name = org.get("name", "?")
        if not org_root:
            missing.append(f"wiki 변경 commit 없음 (org={org_name}, org.root 누락)")
            return missing

        wiki_dir = "./.jarfis-org/wiki"
        changed = _h.git_changed_files(org_root, "HEAD~1", "HEAD")
        if not any(f.startswith(".jarfis-org/wiki/") for f in changed):
            missing.append(f"wiki 변경 commit 없음 (org={org_name}, 예상 경로 {org_root}/.jarfis-org/wiki)")
        else:
            if not any(f.startswith(".jarfis-org/wiki/") and f.endswith("INDEX.md") for f in changed):
                missing.append(f"wiki/INDEX.md 갱신 commit 없음 (org={org_name})")

    # v4.4 (defect D5): docsDir position assertion. The state.work.docsDir
    # must lie under {org_dir}/works/ where org_dir = get_org_dir(project_path).
    # The orchestrator computes docs_dir = state.work.docsDir, so reuse it.
    try:
        from .utils import get_org_dir as _get_org_dir
        # Pick a representative project path: first scope path if available.
        workspace = state.get("workspace") or {}
        scopes = workspace.get("scope") or []
        project_path = None
        if scopes:
            project_path = scopes[0].get("path")
        # Resolve org_dir based on project_path; falls back to standalone (flat).
        org_dir = _get_org_dir(project_path) if project_path else None
        if org_dir and docs_dir:
            expected_prefix = os.path.join(os.path.abspath(org_dir), "works") + os.sep
            actual = os.path.abspath(docs_dir)
            if not (actual == expected_prefix.rstrip(os.sep) or actual.startswith(expected_prefix)):
                missing.append(
                    f"docsDir position invalid: {actual} not under {expected_prefix.rstrip(os.sep)}"
                )
    except Exception:
        # Best-effort — never flip phase outcome on a soft check failure.
        pass

    # NEW: Org IA merge artifact check (Stage 3; best-effort skip if Stage 6 not done).
    ia_dir = Path(docs_dir) / "discovery" / "ia"
    if ia_dir.is_dir() and _h.org_registered(state):
        missing.extend(_h.check_ia_merge_artifacts(state, docs_dir))

    return missing


PHASE_VERIFIERS = {
    "1": _phase_1b_verify,
    "1a": _phase_1b_verify,
    "1b": _phase_1b_verify,
    "2": _phase_2_verify,
    "3": _phase_3_verify,
    "4": _phase_4_verify,
    "4-5": _phase_4_5_verify,
    "4.5": _phase_4_5_verify,
    "5": _phase_5_verify,
    "6": _phase_6_verify,
}


def cmd_phase_verify(args):
    """Dispatch Phase N verifier. Returns JSON {verdict, missing[], checkedAt, phaseId}."""
    if len(args) < 2:
        json_error("Usage: jarfis phase-verify <state_file> <phase_id>")

    state_file, phase_id = args[0], args[1]

    start = time.monotonic()
    try:
        if trace.is_enabled():
            trace.log_event("phase_verify_start", {"phase_id": phase_id})
    except Exception:
        pass

    if phase_id not in PHASE_VERIFIERS:
        valid = ", ".join(PHASE_VERIFIERS.keys())
        json_error(f"Unknown phase_id: {phase_id}. Valid: {valid}")

    if not os.path.isfile(state_file):
        json_error(f"state file not found: {state_file}")

    try:
        with open(state_file, encoding="utf-8") as f:
            state = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        json_error(f"failed to read state: {e}")

    docs_dir = (state.get("work") or {}).get("docsDir")
    if not docs_dir:
        json_error("state.work.docsDir 누락")

    missing = PHASE_VERIFIERS[phase_id](state, docs_dir)

    result = {
        "verdict": "PASS" if not missing else "FAIL",
        "missing": missing,
        "checkedAt": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "phaseId": phase_id,
    }
    try:
        if trace.is_enabled():
            trace.log_event(
                "phase_verify_end",
                {"phase_id": phase_id, "verdict": result["verdict"],
                 "missing_count": len(missing),
                 "duration_ms": int((time.monotonic() - start) * 1000)},
            )
    except Exception:
        pass
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(0 if not missing else 1)


# ---------------------------------------------------------------------------
# v4 pattern-detect — review round 패턴 감지 (M3)
#
# 3개 패턴: stagnation / regression / oscillation. 항상 exit 0 (정보 제공).
# ---------------------------------------------------------------------------
_ROUND_HEADING_RE = re.compile(r"^\s*##\s+Round\s+(\d+)\s*$", re.IGNORECASE | re.MULTILINE)
_REVISION_LINE_RE = re.compile(r"\[REVISION\]\s*(.+?)\s*$", re.MULTILINE)


def _normalize_issue(text):
    """앞뒤 공백 제거 + 리스트 마커/REVISION 태그 제거 + 양끝 영숫자 외 trim."""
    s = text.strip()
    s = re.sub(r"^[-*+]\s+", "", s)
    s = re.sub(r"^\[REVISION\]\s*", "", s, flags=re.IGNORECASE)
    s = s.strip()
    return s


def _parse_review_md(md_path):
    """Return {round_number: [normalized_issue, ...]}."""
    p = Path(md_path)
    if not p.is_file():
        return {}
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}

    headings = list(_ROUND_HEADING_RE.finditer(text))
    if not headings:
        return {}

    rounds = {}
    for i, m in enumerate(headings):
        round_no = int(m.group(1))
        start = m.end()
        end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
        body = text[start:end]
        issues = []
        for line in body.splitlines():
            if "[REVISION]" not in line.upper():
                continue
            normalized = _normalize_issue(line)
            if normalized:
                issues.append(normalized)
        rounds[round_no] = issues
    return rounds


def _detect_stagnation(rounds):
    """같은 issue가 연속 2+ Round에 존재."""
    if len(rounds) < 2:
        return None
    ordered = sorted(rounds.keys())
    for i in range(len(ordered) - 1):
        a, b = ordered[i], ordered[i + 1]
        if b != a + 1:
            continue
        common = set(rounds[a]) & set(rounds[b])
        if common:
            issue = sorted(common)[0]
            run = [a, b]
            j = i + 2
            while j < len(ordered) and ordered[j] == ordered[j - 1] + 1 and issue in rounds[ordered[j]]:
                run.append(ordered[j])
                j += 1
            return {"issue": issue, "rounds": run}
    return None


def _detect_regression(rounds):
    """Round N issue 중 Round N-1 없었던 항목 (N>=2)."""
    ordered = sorted(rounds.keys())
    for idx, n in enumerate(ordered):
        if idx == 0:
            continue
        prev = ordered[idx - 1]
        if n != prev + 1:
            continue
        new_issues = sorted(set(rounds[n]) - set(rounds[prev]))
        if new_issues:
            return {"issue": new_issues[0], "rounds": [n]}
    return None


def _detect_oscillation(rounds):
    """Round N issue 집합 == Round N-2 집합 (N>=3, 비어있지 않을 때)."""
    ordered = sorted(rounds.keys())
    for idx, n in enumerate(ordered):
        if idx < 2:
            continue
        n2 = ordered[idx - 2]
        if n - n2 != 2:
            continue
        set_n = set(rounds[n])
        set_n2 = set(rounds[n2])
        if set_n and set_n == set_n2:
            return {"rounds": [n, n2]}
    return None


def cmd_pattern_detect(args):
    """Detect review-round patterns. Always exits 0 (informational)."""
    if len(args) < 1:
        json_error("Usage: jarfis pattern-detect <review_md_path>")

    review_path = args[0]

    if not os.path.isfile(review_path):
        json_error(f"review.md not found: {review_path}")

    rounds = _parse_review_md(review_path)
    stagnation = _detect_stagnation(rounds)
    regression = _detect_regression(rounds)
    oscillation = _detect_oscillation(rounds)

    patterns = []
    if stagnation:
        patterns.append("stagnation")
    if regression:
        patterns.append("regression")
    if oscillation:
        patterns.append("oscillation")

    result = {
        "patterns": patterns,
        "details": {
            "stagnation": stagnation,
            "regression": regression,
            "oscillation": oscillation,
        },
        "reviewPath": review_path,
    }
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(0)


# ---------------------------------------------------------------------------
# Module-level dispatch entry point (used by jarfis_cli.py routing)
# ---------------------------------------------------------------------------
def main(args):
    """Dispatch entry for jarfis_cli.py top-level subcommands.

    jarfis_cli.py prepends the subcommand to args (e.g. ["gate-check", ...]),
    so args[0] is the subcommand name and args[1:] are its positional args.
    """
    if not args:
        json_error("Usage: jarfis <gate-check|phase-check|phase-verify|pattern-detect> <args...>")

    sub = args[0]
    rest = args[1:]

    dispatch = {
        "gate-check": cmd_gate_check,
        "phase-check": cmd_phase_check,
        "phase-verify": cmd_phase_verify,
        "pattern-detect": cmd_pattern_detect,
    }

    if sub not in dispatch:
        json_error(
            f"Unknown verify subcommand: {sub}. "
            "Use gate-check|phase-check|phase-verify|pattern-detect."
        )

    dispatch[sub](rest)
