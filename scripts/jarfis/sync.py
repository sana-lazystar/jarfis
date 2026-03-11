"""JARFIS Sync — ~/.claude/ → repo unidirectional sync + README update.

Usage:
    jarfis sync [repo_path]           Full sync + README update
    jarfis sync --readme-only [repo]  README update only
"""

import os
import re
import shutil
import subprocess
import sys

from .utils import get_claude_dir, get_source_path


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
    for f in _find_files(os.path.join(claude_dir, "commands", "jarfis"), ".md"):
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
            if "명령어 매핑" in line:
                in_section = True
                continue
            if in_section:
                if line.startswith("|") and "명령어" not in line and "---" not in line:
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
            if "파일 구조" in line:
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
                    clean = re.sub(r"\s*\(\d+줄[^)]*\)", "", line)
                    clean = re.sub(r"\s*\[NEW\]", "", clean)
                    clean = clean.rstrip()
                    struct_lines.append(clean)

        if struct_lines:
            arch_lines = [
                "## Architecture\n",
                "```",
            ] + struct_lines + [
                "```\n",
                "**설계 원칙**:\n",
                "- **워크플로우 흐름**은 `work.md`에, **에이전트 프롬프트**는 `prompts/`에, **산출물 양식**은 `templates/`에 분리",
                "- 에이전트 역할 프롬프트(`agents/`)와 워크플로우 프롬프트(`prompts/`)는 별개 — 역할은 고정, 태스크는 Phase마다 다름",
                "- 학습 데이터는 로컬에만 존재 (Git repo에 포함되지 않음)",
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
                "> 전체 변경 이력은 [CHANGELOG.md](./CHANGELOG.md)를 참조하세요.\n",
                version_section,
            ]
            changes_content = "\n".join(changes_lines)
            readme = _replace_section(readme, "<!-- JARFIS-LATEST-CHANGES-START -->", "<!-- JARFIS-LATEST-CHANGES-END -->", changes_content)

    if readme != original:
        with open(readme_path, "w") as f:
            f.write(readme)
        updated = 1
        print(f"📝 README.md: 섹션 갱신")
    else:
        print(f"📝 README.md: 이미 최신 (변경 없음)")

    return updated


def main(args):
    readme_only = "--readme-only" in args
    remaining = [a for a in args if a != "--readme-only"]
    repo_path = remaining[0] if remaining else get_source_path()

    if not os.path.isdir(repo_path):
        print(f"ERROR: repo not found at {repo_path}", file=sys.stderr)
        sys.exit(1)

    if readme_only:
        update_readme(repo_path)
        return

    claude_dir = get_claude_dir()
    synced, changes = sync_files(repo_path, claude_dir)

    # README update
    update_readme(repo_path)

    if synced > 0:
        print(f"🔄 Repo 동기화: {synced}개 파일 → {repo_path}")
        for c in changes:
            print(c)
    else:
        print(f"✅ Repo 동기화: 이미 최신 (변경 없음)")
