"""JARFIS Sync — ~/.claude/ → repo unidirectional sync + README update.

Usage:
    jarfis sync [repo_path]           Full sync + README update
    jarfis sync --readme-only [repo]  README update only
    jarfis sync --version-check [repo] Drift check only (exit 1 on drift)
"""

import os
import re
import shutil
import subprocess
import sys

from .utils import get_claude_dir, get_source_path


def _read_version_from(path):
    """Extract version string from VERSION, .jarfis-version, or __init__.py."""
    if not os.path.isfile(path):
        return None
    try:
        content = open(path).read()
    except OSError:
        return None
    if path.endswith("__init__.py"):
        m = re.search(r'__version__\s*=\s*"([^"]+)"', content)
        return m.group(1) if m else None
    s = content.strip()
    return s or None


def check_version_drift(repo_path, claude_dir):
    """Return (versions_dict, drift_bool).

    Inspects 4 sources:
      - {claude_dir}/.jarfis-version
      - {claude_dir}/scripts/jarfis/__init__.py
      - {repo_path}/VERSION
      - {repo_path}/scripts/jarfis/__init__.py

    drift=True when ≥2 distinct non-null values are present.
    """
    sources = [
        ("claude/.jarfis-version", os.path.join(claude_dir, ".jarfis-version")),
        ("claude/scripts/jarfis/__init__.py", os.path.join(claude_dir, "scripts", "jarfis", "__init__.py")),
        ("repo/VERSION", os.path.join(repo_path, "VERSION")),
        ("repo/scripts/jarfis/__init__.py", os.path.join(repo_path, "scripts", "jarfis", "__init__.py")),
    ]
    versions = {}
    for label, path in sources:
        v = _read_version_from(path)
        if v is not None:
            versions[label] = v
    distinct = {v for v in versions.values()}
    return versions, len(distinct) > 1


def _diff_files(src, dst):
    """Return True if files differ or dst doesn't exist."""
    if not os.path.isfile(dst):
        return True
    try:
        with open(src, "rb") as f1, open(dst, "rb") as f2:
            return f1.read() != f2.read()
    except Exception:
        return True


def _sync_file(src, dst, claude_dir, changes):
    """Sync a single file. Returns 1 if synced, 0 otherwise."""
    if not os.path.isfile(src):
        return 0
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if _diff_files(src, dst):
        shutil.copy2(src, dst)
        rel_src = src[len(claude_dir) + 1:] if src.startswith(claude_dir + "/") else src
        changes.append(f"  ✅ {rel_src}")
        return 1
    return 0


def _find_files(directory, pattern=None, name_filter=None):
    """Walk directory and yield matching files."""
    if not os.path.isdir(directory):
        return
    for root, dirs, files in os.walk(directory):
        if ".distill-backup" in root:
            continue
        for fn in sorted(files):
            if pattern and not fn.endswith(pattern):
                continue
            if name_filter and not name_filter(fn):
                continue
            yield os.path.join(root, fn)


def sync_files(repo_path, claude_dir):
    """Sync files from ~/.claude → repo. Returns (synced_count, changes)."""
    synced = 0
    changes = []

    # 1. commands/jarfis.md
    synced += _sync_file(
        os.path.join(claude_dir, "commands", "jarfis.md"),
        os.path.join(repo_path, "commands", "jarfis.md"),
        claude_dir, changes
    )

    # 2. commands/jarfis/* (recursive, excluding .distill-backup)
    # Include .md (prompts/templates/skills) + .yaml/.yml (agent-composition, domain configs)
    for ext in (".md", ".yaml", ".yml"):
        for f in _find_files(os.path.join(claude_dir, "commands", "jarfis"), ext):
            rel = f[len(os.path.join(claude_dir, "commands", "jarfis")) + 1:]
            synced += _sync_file(f, os.path.join(repo_path, "commands", "jarfis", rel), claude_dir, changes)

    # 3. agents/jarfis/*
    for f in _find_files(os.path.join(claude_dir, "agents", "jarfis"), ".md"):
        rel = f[len(os.path.join(claude_dir, "agents", "jarfis")) + 1:]
        synced += _sync_file(f, os.path.join(repo_path, "agents", "jarfis", rel), claude_dir, changes)

    # 4. hooks/* (jarfis- prefix only)
    for f in _find_files(os.path.join(claude_dir, "hooks"), name_filter=lambda n: n.startswith("jarfis-")):
        rel = os.path.basename(f)
        synced += _sync_file(f, os.path.join(repo_path, "hooks", rel), claude_dir, changes)

    # 5. scripts/* (jarfis-* + claude-cleanup.sh + jarfis_cli.py + jarfis entrypoint)
    scripts_dir = os.path.join(claude_dir, "scripts")
    if os.path.isdir(scripts_dir):
        for fn in os.listdir(scripts_dir):
            full = os.path.join(scripts_dir, fn)
            if not os.path.isfile(full):
                continue
            if fn.startswith("jarfis-") or fn == "claude-cleanup.sh" or fn == "jarfis_cli.py" or fn == "jarfis":
                synced += _sync_file(full, os.path.join(repo_path, "scripts", fn), claude_dir, changes)

    # 5b. scripts/jarfis/ Python package
    src_pkg = os.path.join(claude_dir, "scripts", "jarfis")
    dst_pkg = os.path.join(repo_path, "scripts", "jarfis")
    if os.path.isdir(src_pkg):
        for f in _find_files(src_pkg, ".py"):
            rel = f[len(src_pkg) + 1:]
            synced += _sync_file(f, os.path.join(dst_pkg, rel), claude_dir, changes)

    # 5c. scripts/tests/ pytest tests
    src_tests = os.path.join(claude_dir, "scripts", "tests")
    dst_tests = os.path.join(repo_path, "scripts", "tests")
    if os.path.isdir(src_tests):
        for f in _find_files(src_tests, ".py"):
            rel = f[len(src_tests) + 1:]
            synced += _sync_file(f, os.path.join(dst_tests, rel), claude_dir, changes)

    # 6. statusline-command.sh
    synced += _sync_file(
        os.path.join(claude_dir, "statusline-command.sh"),
        os.path.join(repo_path, "statusline-command.sh"),
        claude_dir, changes
    )

    return synced, changes


def _replace_section(content, start_marker, end_marker, new_content):
    """Replace content between HTML comment markers."""
    pattern = re.compile(
        re.escape(start_marker) + r"\n.*?" + re.escape(end_marker),
        re.DOTALL
    )
    replacement = start_marker + "\n" + new_content + "\n" + end_marker
    new = pattern.sub(replacement, content)
    return new


def update_readme(repo_path):
    """Update README.md sections from jarfis-index.md and CHANGELOG.md."""
    claude_dir = get_claude_dir()
    readme_path = os.path.join(repo_path, "README.md")
    index_path = os.path.join(claude_dir, "commands", "jarfis", "jarfis-index.md")
    changelog_path = os.path.join(repo_path, "CHANGELOG.md")

    if not os.path.isfile(readme_path):
        print(f"ERROR: README.md not found at {readme_path}", file=sys.stderr)
        return

    with open(readme_path) as f:
        readme = f.read()

    updated = 0
    original = readme

    # 1. Commands section
    if os.path.isfile(index_path):
        with open(index_path) as f:
            index_content = f.read()

        # Parse command mapping table
        cmds = []
        in_section = False
        for line in index_content.split("\n"):
            if "Command Mapping" in line:
                in_section = True
                continue
            if in_section:
                if line.startswith("|") and "Command" not in line and "---" not in line:
                    cols = [c.strip() for c in line.split("|")]
                    if len(cols) >= 5 and cols[1] and cols[3]:
                        cmds.append((cols[1], cols[3]))
                elif line.startswith("##") or (not line.strip() and cmds):
                    in_section = False

        if cmds:
            max_cmd = max(len("Command"), max(len(c) for c, _ in cmds))
            max_desc = max(len("Description"), max(len(d) for _, d in cmds))
            lines = [
                "## Commands\n",
                f"| {'Command':<{max_cmd}} | {'Description':<{max_desc}} |",
                f"| {'-' * max_cmd} | {'-' * max_desc} |",
            ]
            for cmd, desc in cmds:
                lines.append(f"| {cmd:<{max_cmd}} | {desc:<{max_desc}} |")
            cmd_content = "\n".join(lines)
            readme = _replace_section(readme, "<!-- JARFIS-COMMANDS-START -->", "<!-- JARFIS-COMMANDS-END -->", cmd_content)

    # 2. Architecture section
    if os.path.isfile(index_path):
        with open(index_path) as f:
            index_content = f.read()

        # Parse file structure
        struct_lines = []
        in_section = False
        in_block = False
        for line in index_content.split("\n"):
            if "File Structure" in line:
                in_section = True
                continue
            if in_section:
                if line.strip() == "```" and not in_block:
                    in_block = True
                    continue
                if line.strip() == "```" and in_block:
                    break
                if in_block:
                    # Strip size annotations
                    clean = re.sub(r"\s*\(\d+\s*(줄|lines)[^)]*\)", "", line)
                    clean = re.sub(r"\s*\[NEW\]", "", clean)
                    clean = clean.rstrip()
                    struct_lines.append(clean)

        if struct_lines:
            arch_lines = [
                "## Architecture\n",
                "```",
            ] + struct_lines + [
                "```\n",
                "**Design Principles**:\n",
                "- **Workflow flow** in `work.md`, **agent prompts** in `prompts/`, **output templates** in `templates/` — separated",
                "- Agent role prompts (`agents/`) and workflow prompts (`prompts/`) are separate — roles are fixed, tasks vary per Phase",
                "- Learning data exists only locally (not included in Git repo)",
            ]
            arch_content = "\n".join(arch_lines)
            readme = _replace_section(readme, "<!-- JARFIS-ARCHITECTURE-START -->", "<!-- JARFIS-ARCHITECTURE-END -->", arch_content)

    # 3. Latest Changes section
    if os.path.isfile(changelog_path):
        with open(changelog_path) as f:
            cl_content = f.read()

        # Extract first version section
        version_match = re.search(r"^(## \[\d+\.\d+\.\d+\].*?)(?=\n## \[|\Z)", cl_content, re.MULTILINE | re.DOTALL)
        if version_match:
            version_section = version_match.group(1).rstrip()
            changes_lines = [
                "## Latest Changes\n",
                "> See [CHANGELOG.md](./CHANGELOG.md) for full change history.\n",
                version_section,
            ]
            changes_content = "\n".join(changes_lines)
            readme = _replace_section(readme, "<!-- JARFIS-LATEST-CHANGES-START -->", "<!-- JARFIS-LATEST-CHANGES-END -->", changes_content)

    if readme != original:
        with open(readme_path, "w") as f:
            f.write(readme)
        updated = 1
        print(f"📝 README.md: sections updated")
    else:
        print(f"📝 README.md: already up-to-date (no changes)")

    return updated


def main(args):
    readme_only = "--readme-only" in args
    version_check_only = "--version-check" in args
    remaining = [a for a in args if a not in ("--readme-only", "--version-check")]
    repo_path = remaining[0] if remaining else get_source_path()

    if not os.path.isdir(repo_path):
        print(f"ERROR: repo not found at {repo_path}", file=sys.stderr)
        sys.exit(1)

    claude_dir = get_claude_dir()

    # Version drift pre-check (informational; sync may resolve __init__.py drift)
    pre_versions, pre_drift = check_version_drift(repo_path, claude_dir)
    if pre_drift:
        print("⚠️  Version drift detected (pre-sync):", file=sys.stderr)
        for label, v in pre_versions.items():
            print(f"    {label}: {v}", file=sys.stderr)

    if version_check_only:
        # Exit 1 if drift present, 0 otherwise. For CI / pre-commit use.
        sys.exit(1 if pre_drift else 0)

    if readme_only:
        update_readme(repo_path)
        return

    synced, changes = sync_files(repo_path, claude_dir)

    # README update
    update_readme(repo_path)

    if synced > 0:
        print(f"🔄 Repo sync: {synced} files → {repo_path}")
        for c in changes:
            print(c)
    else:
        print(f"✅ Repo sync: already up-to-date (no changes)")

    # Post-sync drift check — after sync, only VERSION vs .jarfis-version drift remains possible
    # (sync copies __init__.py so both __init__.py values match). Warn if mismatch persists.
    post_versions, post_drift = check_version_drift(repo_path, claude_dir)
    if post_drift:
        print("⚠️  Version drift persists after sync — manual fix required:", file=sys.stderr)
        for label, v in post_versions.items():
            print(f"    {label}: {v}", file=sys.stderr)
        print("    Run: jarfis version patch \"fix drift\" (or align manually).", file=sys.stderr)
