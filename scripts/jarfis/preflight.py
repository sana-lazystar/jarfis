"""JARFIS Pre-flight — work/continue/meeting pre-validation.

Usage: jarfis preflight [options] [project_dir]

Options:
    --org-dir path   Org directory override
    --check-meetings       Check meetings directory
    --verbose              Verbose output to stderr
"""

import os
import subprocess
import sys

from .organization import ensure_project_in_org_profile, read_orgs, register_org
from .utils import _resolve_org_name, find_org_root, get_claude_dir, get_source_path, get_org_dir, json_output, STANDALONE_ORG


def _validate_docsdir_position(docsdir, org_dir):
    """Defect D6: validate docsDir lies under {org_dir}/works/.

    Returns dict suitable for inclusion in preflight JSON output:
      - {"valid": True} when docsDir is under the expected prefix.
      - {"valid": False, "expected_prefix": ..., "actual": ...,
         "error": "..."} otherwise.
    """
    expected_prefix = os.path.join(os.path.abspath(org_dir), "works") + os.sep
    actual = os.path.abspath(docsdir)
    # Use string-prefix match anchored on path separator to avoid partial-name
    # collisions (e.g. /a/works-old/ vs /a/works/).
    if actual.startswith(expected_prefix) or actual == expected_prefix.rstrip(os.sep):
        return {"valid": True}
    return {
        "valid": False,
        "expected_prefix": expected_prefix.rstrip(os.sep),
        "actual": actual,
        "error": "docsDir is outside org workspace",
    }


def main(args):
    project_dir = ""
    org_dir = ""
    check_meetings = False
    verbose = False
    check_docsdir = ""

    i = 0
    while i < len(args):
        if args[i] == "--org-dir" and i + 1 < len(args):
            org_dir = args[i + 1]
            i += 2
        elif args[i] == "--check-meetings":
            check_meetings = True
            i += 1
        elif args[i] == "--check-docsdir" and i + 1 < len(args):
            check_docsdir = args[i + 1]
            i += 2
        elif args[i] == "--verbose":
            verbose = True
            i += 1
        else:
            project_dir = args[i]
            i += 1

    def log(msg):
        if verbose:
            print(f"[preflight] {msg}", file=sys.stderr)

    if not project_dir:
        project_dir = os.getcwd()

    if not org_dir:
        org_dir = get_org_dir(project_dir)

    warnings = []

    # Profile check
    profile_path = os.path.join(project_dir, ".jarfis-project", "project-profile.md")
    has_profile = os.path.isfile(profile_path)
    if has_profile:
        log(f"Profile found: {profile_path}")
    else:
        warnings.append("No project profile found. Create one with /jarfis:project-init.")
        profile_path = None
        log("Profile not found")

    # Greenfield detection (ADR-0003 §2.4) — directory has no project
    # profile AND no recognizable manifest (package.json, Cargo.toml,
    # pyproject.toml, etc.). Signals work.md Phase 0 to AskUserQuestion
    # before invoking domain detect.
    greenfield = False
    if not has_profile:
        manifest_candidates = (
            "package.json",
            "Cargo.toml",
            "pyproject.toml",
            "requirements.txt",
            "go.mod",
            "pom.xml",
            "build.gradle",
            "build.gradle.kts",
            "Gemfile",
            "pubspec.yaml",
            "Pipfile",
        )
        has_any_manifest = any(
            os.path.isfile(os.path.join(project_dir, name))
            for name in manifest_candidates
        )
        if not has_any_manifest:
            greenfield = True
            warnings.append(
                "Greenfield directory (no project profile, no codebase). "
                "Phase 0 will ask which domain to scaffold."
            )
            log("Greenfield directory detected")

    # Project rule check (user-defined, highest priority)
    rule_path = os.path.join(project_dir, ".jarfis-project", "project-rule.md")
    has_rule = os.path.isfile(rule_path)
    if has_rule:
        log(f"Rule found: {rule_path}")
    else:
        rule_path = None
        log("Rule not found")

    # Project context check
    context_path = os.path.join(project_dir, ".jarfis-project", "project-context.md")
    has_context = os.path.isfile(context_path)
    if has_context:
        log(f"Context found: {context_path}")
    else:
        context_path = None
        log("Context not found")

    # Git check
    git_available = False
    branch = None
    uncommitted = 0
    has_uncommitted = False

    git_dir = os.path.join(project_dir, ".git")
    try:
        if os.path.isdir(git_dir) or subprocess.run(
            ["git", "-C", project_dir, "rev-parse", "--git-dir"],
            capture_output=True, text=True
        ).returncode == 0:
            git_available = True
            result = subprocess.run(
                ["git", "-C", project_dir, "branch", "--show-current"],
                capture_output=True, text=True
            )
            branch_raw = result.stdout.strip()
            branch = branch_raw if branch_raw else None

            result = subprocess.run(
                ["git", "-C", project_dir, "status", "--porcelain"],
                capture_output=True, text=True
            )
            uncommitted = len([l for l in result.stdout.strip().split("\n") if l.strip()])
            if uncommitted > 0:
                has_uncommitted = True
                warnings.append(f"{uncommitted} uncommitted changes detected.")
            log(f"Git: branch={branch}, uncommitted={uncommitted}")
    except FileNotFoundError:
        warnings.append("Not a Git repository.")
        log("Git not available")

    if not git_available and "Not a Git repository." not in warnings:
        warnings.append("Not a Git repository.")

    # Org detection
    org_root = find_org_root(project_dir)
    org_profile = None
    has_wiki = False
    wiki_index = None

    org_name = None
    org_auto_registered = False

    if org_root:
        org_profile = os.path.join(org_root, ".jarfis-org", "org-profile.md")
        if not os.path.isfile(org_profile):
            org_profile = None
        wiki_index_path = os.path.join(org_root, ".jarfis-org", "wiki", "INDEX.md")
        if os.path.isfile(wiki_index_path):
            has_wiki = True
            wiki_index = wiki_index_path
        else:
            warnings.append("Organization is registered but wiki/INDEX.md is missing.")

        # Resolve org name and auto-register if needed (v4.4: register_org
        # returns a dict; expose the newly-registered boolean for backward
        # compat with downstream consumers).
        org_name = _resolve_org_name(project_dir)
        if org_name and org_name != STANDALONE_ORG:
            reg_result = register_org(org_name, org_root)
            org_auto_registered = bool(reg_result.get("registered"))
            if org_auto_registered:
                log(f"Org auto-registered: {org_name}")

        # Auto-add project to org-profile.md table if missing
        org_project_added = ensure_project_in_org_profile(org_root, project_dir)
        if org_project_added:
            log(f"Project auto-added to org-profile.md: {project_dir}")

        log(f"Org: root={org_root}, name={org_name}, wiki={has_wiki}")
    else:
        org_project_added = False
        log("Org not found")

    # Meetings check
    has_meetings = False
    if check_meetings:
        meetings_dir = os.path.join(project_dir, ".jarfis-project", "meetings")
        if os.path.isdir(meetings_dir):
            for root, dirs, files in os.walk(meetings_dir):
                if "summary.md" in files:
                    has_meetings = True
                    break
        log(f"Meetings: {has_meetings}")

    # Defect D6: docsDir position validation (best-effort).
    docsdir_validated = None
    if check_docsdir:
        docsdir_validated = _validate_docsdir_position(check_docsdir, org_dir)

    json_output({
        "project_dir": project_dir,
        "profile_path": profile_path,
        "has_profile": has_profile,
        "greenfield": greenfield,
        "has_rule": has_rule,
        "rule_path": rule_path,
        "has_context": has_context,
        "context_path": context_path,
        "git_available": git_available,
        "branch": branch,
        "uncommitted": uncommitted,
        "has_uncommitted": has_uncommitted,
        "org_dir": org_dir,
        "has_meetings": has_meetings,
        "org_root": org_root,
        "org_name": org_name,
        "org_auto_registered": org_auto_registered,
        "org_project_added": org_project_added,
        "org_profile": org_profile,
        "has_wiki": has_wiki,
        "wiki_index": wiki_index,
        "docsDir_validated": docsdir_validated,
        "warnings": warnings,
    })
