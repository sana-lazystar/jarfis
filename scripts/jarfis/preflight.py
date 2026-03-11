"""JARFIS Pre-flight — work/continue/meeting pre-validation.

Usage: jarfis preflight [options] [project_dir]

Options:
    --workspace-dir path   Workspace directory override
    --check-meetings       Check meetings directory
    --verbose              Verbose output to stderr
"""

import os
import subprocess
import sys

from .utils import get_claude_dir, get_source_path, get_workspace_dir, json_output


def main(args):
    project_dir = ""
    workspace_dir = ""
    check_meetings = False
    verbose = False

    i = 0
    while i < len(args):
        if args[i] == "--workspace-dir" and i + 1 < len(args):
            workspace_dir = args[i + 1]
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

    if not workspace_dir:
        workspace_dir = get_workspace_dir()

    warnings = []

    # Profile check
    profile_path = os.path.join(project_dir, ".jarfis", "project-profile.md")
    has_profile = os.path.isfile(profile_path)
    if has_profile:
        log(f"Profile found: {profile_path}")
    else:
        warnings.append("프로젝트 프로필이 없습니다. /jarfis:project-init으로 생성하세요.")
        profile_path = None
        log("Profile not found")

    # Learnings check
    source_path = get_source_path()
    learnings_path = os.path.join(source_path, ".local", "jarfis-learnings.md")
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
                warnings.append(f"커밋되지 않은 변경 {uncommitted}개가 있습니다.")
            log(f"Git: branch={branch}, uncommitted={uncommitted}")
    except FileNotFoundError:
        warnings.append("Git 저장소가 아닙니다.")
        log("Git not available")

    if not git_available and "Git 저장소가 아닙니다." not in warnings:
        warnings.append("Git 저장소가 아닙니다.")

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
        "workspace_dir": workspace_dir,
        "has_meetings": has_meetings,
        "warnings": warnings,
    })
