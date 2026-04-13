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
from .utils import _resolve_org_name, find_org_root, get_claude_dir, get_learnings_path, get_source_path, get_org_dir, json_output, STANDALONE_ORG


def main(args):
    project_dir = ""
    org_dir = ""
    check_meetings = False
    verbose = False

    i = 0
    while i < len(args):
        if args[i] == "--org-dir" and i + 1 < len(args):
            org_dir = args[i + 1]
            i += 2
        elif args[i] == "--check-meetings":
            check_meetings = True
            i += 1
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
    profile_path = os.path.join(project_dir, ".jarfis", "project-profile.md")
    has_profile = os.path.isfile(profile_path)
    if has_profile:
        log(f"Profile found: {profile_path}")
    else:
        warnings.append("No project profile found. Create one with /jarfis:project-init.")
        profile_path = None
        log("Profile not found")

    # Learnings check
    learnings_path = get_learnings_path(project_dir)
    has_learnings = os.path.isfile(learnings_path)
    if has_learnings:
        log(f"Learnings found: {learnings_path}")
    else:
        learnings_path = None
        log("Learnings not found")

    # Project context check
    context_path = os.path.join(project_dir, ".jarfis", "project-context.md")
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
        org_profile = os.path.join(org_root, ".jarfis", "org-profile.md")
        if not os.path.isfile(org_profile):
            org_profile = None
        wiki_index_path = os.path.join(org_root, ".jarfis", "wiki", "INDEX.md")
        if os.path.isfile(wiki_index_path):
            has_wiki = True
            wiki_index = wiki_index_path
        else:
            warnings.append("Organization is registered but wiki/INDEX.md is missing.")

        # Resolve org name and auto-register if needed
        org_name = _resolve_org_name(project_dir)
        if org_name and org_name != STANDALONE_ORG:
            org_auto_registered = register_org(org_name, org_root)
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
        meetings_dir = os.path.join(project_dir, ".jarfis", "meetings")
        if os.path.isdir(meetings_dir):
            for root, dirs, files in os.walk(meetings_dir):
                if "summary.md" in files:
                    has_meetings = True
                    break
        log(f"Meetings: {has_meetings}")

    json_output({
        "project_dir": project_dir,
        "profile_path": profile_path,
        "has_profile": has_profile,
        "has_learnings": has_learnings,
        "learnings_path": learnings_path,
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
        "warnings": warnings,
    })
