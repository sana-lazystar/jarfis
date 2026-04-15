"""JARFIS Gate Check -- Programmatic prerequisite validation for Gate 1/2/3.

Blocks gate presentation if required artifacts or state conditions are not met.
This is a SAFETY mechanism to prevent the LLM orchestrator from skipping steps.

Subcommands (via state.py routing):
    gate-check <state_file> <gate_number>
    phase-check <state_file> <phase_number>

Exit code 0 = PASS, 1 = FAIL.
"""

import json
import os
import re
import sys

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
    for f in ("press-release.md", "prd.md"):
        if _check_file(docs_dir, f):
            results.append(CheckResult(f"{f} exists", CheckResult.PASS))
        else:
            results.append(CheckResult(f"{f} missing", CheckResult.FAIL))

    # -- Ratchet state --
    ratchet = _get_nested(state, "phases.1.ratchet")
    if ratchet and "prd_score" in ratchet:
        score = ratchet["prd_score"]
        results.append(
            CheckResult(
                "phases.1.ratchet.prd_score exists",
                CheckResult.PASS,
                f"score={score}",
            )
        )
    else:
        results.append(
            CheckResult(
                "phases.1.ratchet.prd_score missing",
                CheckResult.FAIL,
                "PRD Completeness Check (Step 1-2.5) not executed",
            )
        )

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

    # -- Always-required Phase 2 artifacts --
    always_required = [
        "impact-analysis.md",
        "architecture.md",
        "tasks.md",
        "test-strategy.md",
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
        if _check_file(docs_dir, "api-spec.md"):
            results.append(
                CheckResult(
                    "api-spec.md exists",
                    CheckResult.PASS,
                    "api_spec_required=true",
                )
            )
        else:
            results.append(
                CheckResult(
                    "api-spec.md missing",
                    CheckResult.FAIL,
                    "api_spec_required=true",
                )
            )
    else:
        results.append(
            CheckResult(
                "api-spec.md",
                CheckResult.SKIP,
                "api_spec_required=false",
            )
        )

    # -- Conditional: ux-direction.md --
    ux_needed = _get_nested(state, "required_roles.ux_designer", False)
    if ux_needed:
        if _check_file(docs_dir, "ux-direction.md"):
            results.append(
                CheckResult(
                    "ux-direction.md exists",
                    CheckResult.PASS,
                    "required_roles.ux_designer=true",
                )
            )
        else:
            results.append(
                CheckResult(
                    "ux-direction.md missing",
                    CheckResult.FAIL,
                    "required_roles.ux_designer=true",
                )
            )
    else:
        results.append(
            CheckResult(
                "ux-direction.md",
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

        # Required Phase 2 artifacts
        for f in ("impact-analysis.md", "architecture.md", "tasks.md", "test-strategy.md"):
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
