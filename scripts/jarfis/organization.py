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

from .utils import json_error, json_output

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
    json_output({
        "action": "init",
        "org_root": os.path.abspath(org_root),
        "org_name": resolved_name,
        "projects": projects,
        "project_count": len(projects),
        "created_files": created,
        "created_count": len(created),
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
