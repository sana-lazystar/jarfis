"""JARFIS Organization — Org-level project management.

Subcommands:
    init <org_root> [--confirm]   Initialize Organization (scan + optional file creation)
    scan <org_root>               Re-scan for new projects
    info <org_root>               Output Org info as JSON
"""

import json
import os
import re
import sys
from datetime import datetime

from .utils import get_personal_dir, json_error, json_output

# Directories to exclude during project scanning
EXCLUDE_DIRS = {
    "node_modules", ".git", "dist", "build", ".next", "__pycache__",
    "venv", ".venv", ".tox", "coverage", ".nyc_output", ".turbo",
}


def _scan_projects(org_root):
    """Recursively scan for projects with .jarfis/project-profile.md."""
    projects = []
    org_root = os.path.abspath(org_root)

    for root, dirs, files in os.walk(org_root):
        # Prune excluded directories
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

        jarfis_dir = os.path.join(root, ".jarfis")
        profile_path = os.path.join(jarfis_dir, "project-profile.md")

        if os.path.isfile(profile_path):
            rel_path = os.path.relpath(root, org_root)
            if rel_path == ".":
                rel_path = "."

            # Extract metadata from profile frontmatter
            name = os.path.basename(root)
            proj_type = "unknown"
            try:
                with open(profile_path) as f:
                    content = f.read()
                # Parse frontmatter-style metadata
                for line in content.split("\n"):
                    line = line.strip()
                    if line.startswith("> Type:"):
                        proj_type = line.replace("> Type:", "").strip()
                    elif line.startswith("# Project Profile:"):
                        name = line.replace("# Project Profile:", "").strip()
            except Exception:
                pass

            projects.append({
                "name": name,
                "path": rel_path,
                "absolute_path": root,
                "type": proj_type,
                "profile": os.path.join(rel_path, ".jarfis", "project-profile.md"),
            })

            # Don't descend into project subdirectories
            dirs.clear()

    return projects


def _create_org_files(org_root, projects, org_name=None):
    """Create Organization files: org-profile.md, wiki structure."""
    org_root = os.path.abspath(org_root)
    jarfis_dir = os.path.join(org_root, ".jarfis")
    wiki_dir = os.path.join(jarfis_dir, "wiki")
    if not org_name:
        org_name = os.path.basename(org_root)
    today = datetime.now().strftime("%Y-%m-%d")

    created_files = []

    # 1. org-profile.md
    os.makedirs(jarfis_dir, exist_ok=True)
    profile_path = os.path.join(jarfis_dir, "org-profile.md")
    project_rows = ""
    for p in projects:
        project_rows += f"| {p['name']} | {p['path']} | {p['type']} | {p['path']}/.jarfis/project-profile.md |\n"
    if not project_rows:
        project_rows = "| (없음) | | | |\n"

    with open(profile_path, "w") as f:
        f.write(f"""---
org: {org_name}
root: {org_root}
created: {today}
---

# Organization Profile

## Projects

| Name | Path | Type | Profile |
|------|------|------|---------|
{project_rows}""")
    created_files.append(profile_path)

    # 2. wiki/INDEX.md
    os.makedirs(wiki_dir, exist_ok=True)
    index_path = os.path.join(wiki_dir, "INDEX.md")
    with open(index_path, "w") as f:
        f.write(f"""# Wiki Index

## Quick Reference
- 총 파일: 0개 (PO: 0, DESIGN: 0, TA: 0, QA: 0)
- 최근 갱신: {today} (Organization 초기화)
- 주요 변경: 초기 구조 생성

## 사용 가이드
- 정보 우선순위: $DOCS_DIR > project/.jarfis > wiki/ > INDEX.md
- 이번 태스크가 다루는 주제: $DOCS_DIR 우선. 안 다루는 주제: wiki 유효.

## Directory Map

### PO/ (0 files)
핵심: (없음)
상세: PO/_index.md

### DESIGN/ (0 files)
핵심: (없음)
상세: DESIGN/_index.md

### TA/ (0 files)
핵심: (없음)
상세: TA/_index.md

### QA/ (0 files)
핵심: (없음)
상세: QA/_index.md
""")
    created_files.append(index_path)

    # 3. Section _index.md files
    for section in ("PO", "DESIGN", "TA", "QA"):
        section_dir = os.path.join(wiki_dir, section)
        os.makedirs(section_dir, exist_ok=True)
        section_index = os.path.join(section_dir, "_index.md")
        with open(section_index, "w") as f:
            f.write(f"""# {section} Wiki Index

| File | Summary | Projects | Updated |
|------|---------|----------|---------|
| (없음) | | | |
""")
        created_files.append(section_index)

    # 4. Update project profiles with org: field
    for p in projects:
        profile_path = os.path.join(p["absolute_path"], ".jarfis", "project-profile.md")
        if os.path.isfile(profile_path):
            with open(profile_path) as f:
                content = f.read()
            if "org:" not in content:
                # Add org: field after Last-Commit line or at end of frontmatter-like header
                content = content.replace(
                    "> Last-Commit:",
                    f"> org: {org_root}\n> Last-Commit:",
                )
                # Fallback: if no Last-Commit, add after Type line
                if f"org: {org_root}" not in content:
                    content = content.replace(
                        "> Type:",
                        f"> org: {org_root}\n> Type:",
                    )
                with open(profile_path, "w") as f:
                    f.write(content)

    return created_files


def _get_orgs_json_path():
    """Return path to orgs.json."""
    return os.path.join(get_personal_dir(), "orgs", "orgs.json")


def read_orgs():
    """Read orgs.json. Returns {"orgs": [...]} or empty structure."""
    path = _get_orgs_json_path()
    if os.path.isfile(path):
        try:
            with open(path) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {"orgs": []}


def _write_orgs(data):
    """Write orgs.json."""
    path = _get_orgs_json_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def register_org(name, root):
    """Register org in orgs.json + create workspace dirs.

    Returns True if newly added, False if already exists.
    Rejects names starting with '_' (reserved prefix).
    """
    if name.startswith("_"):
        return False
    data = read_orgs()
    for org in data["orgs"]:
        if org["name"] == name:
            return False
    data["orgs"].append({"name": name, "root": os.path.abspath(root)})
    _write_orgs(data)

    # Create org workspace directories
    personal = get_personal_dir()
    org_ws = os.path.join(personal, "orgs", name)
    os.makedirs(os.path.join(org_ws, "works"), exist_ok=True)
    os.makedirs(os.path.join(org_ws, "meetings"), exist_ok=True)
    return True


def ensure_project_in_org_profile(org_root, project_dir):
    """Ensure a project is listed in org-profile.md's Projects table.

    If the project has a .jarfis/project-profile.md but is not in the
    org-profile.md table, adds a new row. Returns True if added, False if
    already present or not applicable.
    """
    org_root = os.path.abspath(org_root)
    project_dir = os.path.abspath(project_dir)
    profile_path = os.path.join(org_root, ".jarfis", "org-profile.md")

    if not os.path.isfile(profile_path):
        return False

    # Check project has its own profile
    proj_profile = os.path.join(project_dir, ".jarfis", "project-profile.md")
    if not os.path.isfile(proj_profile):
        return False

    rel_path = os.path.relpath(project_dir, org_root)

    # Read org-profile and check if project is already in table
    with open(profile_path) as f:
        content = f.read()

    if rel_path in content or os.path.basename(project_dir) in content:
        return False

    # Extract project metadata
    name = os.path.basename(project_dir)
    proj_type = "unknown"
    try:
        with open(proj_profile) as f:
            for line in f:
                line = line.strip()
                if line.startswith("# Project Profile:"):
                    name = line.replace("# Project Profile:", "").strip()
                elif line.startswith("> Type:"):
                    proj_type = line.replace("> Type:", "").strip()
    except Exception:
        pass

    # Add row to table
    new_row = f"| {name} | {rel_path} | {proj_type} | {rel_path}/.jarfis/project-profile.md |"
    # Remove empty placeholder row if present
    content = content.replace("| (없음) | | | |", "")
    # Insert before the last line or at end of table
    if content.rstrip().endswith("|"):
        content = content.rstrip() + "\n" + new_row + "\n"
    else:
        content = content + new_row + "\n"

    with open(profile_path, "w") as f:
        f.write(content)

    return True


def cmd_init(args):
    """Initialize Organization."""
    org_root = args[0] if args else ""
    confirm = "--confirm" in args

    # Parse --name option
    org_name = None
    for i, a in enumerate(args):
        if a == "--name" and i + 1 < len(args):
            org_name = args[i + 1]
            break

    if not org_root:
        json_error("Usage: jarfis org init <org_root> [--confirm] [--name <name>]")

    if not os.path.isdir(org_root):
        json_error(f"Directory not found: {org_root}")

    projects = _scan_projects(org_root)

    if not confirm:
        # Scan only — output JSON for agent to display
        json_output({
            "action": "scan",
            "org_root": os.path.abspath(org_root),
            "org_name": os.path.basename(os.path.abspath(org_root)),
            "projects": projects,
            "project_count": len(projects),
            "message": "Use --confirm to create files",
        })
        return

    # Create files
    resolved_name = org_name or os.path.basename(os.path.abspath(org_root))
    created = _create_org_files(org_root, projects, org_name=resolved_name)

    # Auto-register in orgs.json
    registered = register_org(resolved_name, org_root)

    json_output({
        "action": "init",
        "org_root": os.path.abspath(org_root),
        "org_name": resolved_name,
        "projects": projects,
        "project_count": len(projects),
        "created_files": created,
        "created_count": len(created),
        "orgs_json_registered": registered,
    })


def cmd_scan(args):
    """Re-scan for new projects."""
    org_root = args[0] if args else ""
    if not org_root:
        json_error("Usage: jarfis org scan <org_root>")

    projects = _scan_projects(org_root)
    json_output({
        "action": "scan",
        "org_root": os.path.abspath(org_root),
        "projects": projects,
        "project_count": len(projects),
    })


def cmd_info(args):
    """Output Organization info."""
    org_root = args[0] if args else ""
    if not org_root:
        json_error("Usage: jarfis org info <org_root>")

    org_root = os.path.abspath(org_root)
    profile_path = os.path.join(org_root, ".jarfis", "org-profile.md")

    if not os.path.isfile(profile_path):
        json_output({
            "registered": False,
            "org_root": org_root,
            "message": "Organization이 등록되지 않았습니다.",
        })
        return

    # Read profile
    with open(profile_path) as f:
        content = f.read()

    # Extract org name from frontmatter
    org_name = os.path.basename(org_root)
    for line in content.split("\n"):
        if line.startswith("org:"):
            org_name = line.split(":", 1)[1].strip()
            break

    # Check wiki
    wiki_dir = os.path.join(org_root, ".jarfis", "wiki")
    has_wiki = os.path.isfile(os.path.join(wiki_dir, "INDEX.md"))

    # Scan current projects
    projects = _scan_projects(org_root)

    json_output({
        "registered": True,
        "org_root": org_root,
        "org_name": org_name,
        "profile_path": profile_path,
        "has_wiki": has_wiki,
        "wiki_dir": wiki_dir if has_wiki else None,
        "projects": projects,
        "project_count": len(projects),
    })


def main(args):
    if not args:
        json_error("Usage: jarfis org <init|scan|info> <org_root> [options]")

    action = args[0]
    rest = args[1:]

    commands = {
        "init": cmd_init,
        "scan": cmd_scan,
        "info": cmd_info,
    }

    if action not in commands:
        json_error(f"Unknown action: {action}. Use init|scan|info.")

    commands[action](rest)
