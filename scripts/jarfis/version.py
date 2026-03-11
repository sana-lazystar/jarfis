"""JARFIS Version Bump — semver version bump automation.

Usage: jarfis version <patch|minor|major> "changelog entry"

Updates: VERSION, .jarfis-version, jarfis-index.md, CHANGELOG.md
"""

import os
import re
import sys
from datetime import date

from .utils import get_claude_dir, get_source_path, json_error, json_output


def main(args):
    bump_type = args[0] if args else ""
    changelog_entry = args[1] if len(args) > 1 else ""

    if not bump_type:
        json_error('Usage: jarfis version <patch|minor|major> "changelog entry"')

    if bump_type not in ("patch", "minor", "major"):
        json_error(f"Invalid bump type: {bump_type}. Must be patch, minor, or major.")

    # Resolve paths
    repo_path = get_source_path()
    claude_dir = get_claude_dir()

    version_file = os.path.join(repo_path, "VERSION")
    jarfis_version_file = os.path.join(claude_dir, ".jarfis-version")
    index_file = os.path.join(claude_dir, "commands", "jarfis", "jarfis-index.md")
    changelog_file = os.path.join(repo_path, "CHANGELOG.md")

    if not os.path.isfile(version_file):
        json_error(f"VERSION file not found: {version_file}")

    # Read current version
    with open(version_file) as f:
        current = f.read().strip()

    parts = current.split(".")
    if len(parts) != 3:
        json_error(f"Invalid version format: {current}")

    try:
        major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
    except ValueError:
        json_error(f"Invalid version format: {current}")

    # Bump
    if bump_type == "patch":
        patch += 1
    elif bump_type == "minor":
        minor += 1
        patch = 0
    elif bump_type == "major":
        major += 1
        minor = 0
        patch = 0

    new_version = f"{major}.{minor}.{patch}"
    today = date.today().isoformat()

    # Update VERSION
    with open(version_file, "w") as f:
        f.write(new_version + "\n")

    # Update .jarfis-version
    with open(jarfis_version_file, "w") as f:
        f.write(new_version + "\n")

    # Update jarfis-index.md
    if os.path.isfile(index_file):
        with open(index_file) as f:
            content = f.read()
        content = re.sub(
            r"Last updated: \d{4}-\d{2}-\d{2} \| Version: \d+\.\d+\.\d+",
            f"Last updated: {today} | Version: {new_version}",
            content,
        )
        with open(index_file, "w") as f:
            f.write(content)

    # Update CHANGELOG.md
    if os.path.isfile(changelog_file) and changelog_entry:
        with open(changelog_file) as f:
            lines = f.readlines()

        new_lines = []
        for line in lines:
            new_lines.append(line)
            if "[Unreleased]" in line:
                # Check if next line is blank
                # Insert entry after [Unreleased] header
                new_lines.append(f"\n- {changelog_entry} ({today})\n")

        with open(changelog_file, "w") as f:
            f.writelines(new_lines)

    files_updated = [version_file, jarfis_version_file, index_file, changelog_file]
    json_output({
        "previous": current,
        "new": new_version,
        "bump_type": bump_type,
        "date": today,
        "files_updated": files_updated,
    })
