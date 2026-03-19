"""JARFIS Validate — Workflow state and artifact validation.

Usage: jarfis validate [--state-file path]

Validates:
  1. .jarfis-state.json structure (reuses state validate)
  2. Artifact file existence (based on current_phase)
  3. Git status (uncommitted changes warning)

Manual tool only — not used as automatic gate.
"""

import json
import os
import subprocess
import sys

from .state import cmd_validate as state_validate
from .utils import get_workspace_dir, json_output


# Artifacts expected after each phase
PHASE_ARTIFACTS = {
    "1": ["press-release.md", "prd.md"],
    "2": ["impact-analysis.md", "architecture.md", "tasks.md", "test-strategy.md"],
    "4": [],  # code changes, not artifact files
    "4.5": ["deployment-plan.md"],
    "5": ["review.md"],
    "6": ["retrospective.md"],
}


def _check_state(state_file):
    """Validate state file structure. Returns (valid, errors)."""
    if not os.path.isfile(state_file):
        return False, [f"State file not found: {state_file}"]

    # Capture state validate output
    import io
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        state_validate([state_file])
        output = sys.stdout.getvalue()
    finally:
        sys.stdout = old_stdout

    try:
        result = json.loads(output)
        return result.get("valid", False), result.get("errors", [])
    except json.JSONDecodeError:
        return False, ["Failed to parse state validate output"]


def _check_artifacts(state_file):
    """Check if expected artifacts exist for completed phases."""
    errors = []
    warnings = []

    with open(state_file) as f:
        data = json.load(f)

    docs_dir = data.get("docs_dir", "")
    if not docs_dir or not os.path.isdir(docs_dir):
        errors.append(f"docs_dir not found: {docs_dir}")
        return errors, warnings

    phases = data.get("phases", {})
    for phase_key, artifacts in PHASE_ARTIFACTS.items():
        phase_status = phases.get(phase_key, {}).get("status", "pending")
        if phase_status == "completed":
            for artifact in artifacts:
                artifact_path = os.path.join(docs_dir, artifact)
                if not os.path.isfile(artifact_path):
                    warnings.append(f"Phase {phase_key} completed but missing: {artifact}")

    return errors, warnings


def _check_git(state_file):
    """Check git status for uncommitted changes."""
    warnings = []

    with open(state_file) as f:
        data = json.load(f)

    # Determine project directory from workspace
    workspace = data.get("workspace", {})
    projects = workspace.get("projects", {})

    dirs_to_check = set()
    for proj in projects.values():
        path = proj.get("path", "")
        if path and path != "N/A":
            dirs_to_check.add(os.path.abspath(path))

    if not dirs_to_check:
        dirs_to_check.add(os.getcwd())

    for d in dirs_to_check:
        if not os.path.isdir(os.path.join(d, ".git")):
            continue
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True, text=True, cwd=d, timeout=5,
            )
            lines = [l for l in result.stdout.strip().split("\n") if l.strip()]
            if lines:
                warnings.append(f"Uncommitted changes in {d}: {len(lines)} file(s)")
        except Exception:
            pass

    return warnings


def main(args):
    # Find state file
    state_file = ""
    if "--state-file" in args:
        idx = args.index("--state-file")
        if idx + 1 < len(args):
            state_file = args[idx + 1]

    if not state_file:
        # Auto-find: look in workspace
        workspace_dir = get_workspace_dir()
        works_dir = os.path.join(workspace_dir, "works")
        if os.path.isdir(works_dir):
            for entry in sorted(os.listdir(works_dir), reverse=True):
                candidate = os.path.join(works_dir, entry, ".jarfis-state.json")
                if os.path.isfile(candidate):
                    state_file = candidate
                    break

    if not state_file:
        json_output({
            "valid": False,
            "errors": ["No .jarfis-state.json found. Use --state-file or run /jarfis:work first."],
            "warnings": [],
        })
        return

    all_errors = []
    all_warnings = []

    # 1. State structure validation
    valid, errors = _check_state(state_file)
    if not valid:
        all_errors.extend(errors)

    # 2. Artifact existence check
    if os.path.isfile(state_file):
        errors, warnings = _check_artifacts(state_file)
        all_errors.extend(errors)
        all_warnings.extend(warnings)

    # 3. Git status
    if os.path.isfile(state_file):
        git_warnings = _check_git(state_file)
        all_warnings.extend(git_warnings)

    json_output({
        "valid": len(all_errors) == 0,
        "state_file": state_file,
        "errors": all_errors,
        "error_count": len(all_errors),
        "warnings": all_warnings,
        "warning_count": len(all_warnings),
    })
