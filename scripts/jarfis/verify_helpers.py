"""JARFIS verify helpers — M3.

Pure helpers used by phase-verify. See implement-plan A.7 + m3-test-results §3.1.

Two groups:
    * Evaluators: state dict → branch condition (7)
    * Checks: filesystem / markdown / git inspections (7+)
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

KEBAB_RE = re.compile(r"^[a-z][a-z0-9-]*$")
TASK_COMMIT_RE_TPL = r"jarfis\({task_id}\)\s*:"
CSS_VAR_RE = re.compile(r"var\(--")


# ---------------------------------------------------------------------------
# Evaluators (state → branch decision)
# ---------------------------------------------------------------------------
def _scope_list(state: dict) -> list[dict]:
    return (state.get("workspace") or {}).get("scope") or []


def has_frontend(state: dict) -> bool:
    return any(p.get("type") == "frontend" for p in _scope_list(state))


def has_backend(state: dict) -> bool:
    return any(p.get("type") == "backend" for p in _scope_list(state))


def has_devops(state: dict) -> bool:
    return bool(state.get("devops"))


def design_required(state: dict) -> bool:
    return (state.get("design") or {}).get("mode") is not None


def api_spec_required(state: dict) -> bool:
    if has_backend(state):
        return True
    return (state.get("api") or {}).get("mode") == "swagger"


def responsive_level(state: dict) -> str:
    return state.get("responsive") or "pc-only"


def org_registered(state: dict) -> bool:
    org = state.get("org")
    return bool(org)


# ---------------------------------------------------------------------------
# Filesystem / markdown checks
# ---------------------------------------------------------------------------
def check_file_exists(path) -> bool:
    return Path(path).exists()


def check_file_nonempty(path) -> bool:
    p = Path(path)
    try:
        return p.is_file() and p.stat().st_size > 0
    except OSError:
        return False


_SECTION_RE_CACHE: dict[tuple[int, str], re.Pattern] = {}


def check_section_exists(md_path, section_title: str, level: int = 2) -> bool:
    """Return True if a `#{level} {section_title}` heading exists (case-sensitive).

    Allows leading whitespace on the line (common in lightly formatted docs)
    and trims trailing whitespace in the heading text before comparison.
    """
    p = Path(md_path)
    if not p.is_file():
        return False
    key = (level, section_title)
    pattern = _SECTION_RE_CACHE.get(key)
    if pattern is None:
        prefix = "#" * level
        pattern = re.compile(
            rf"^\s*{re.escape(prefix)}\s+{re.escape(section_title)}\s*$",
            re.MULTILINE,
        )
        _SECTION_RE_CACHE[key] = pattern
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return bool(pattern.search(text))


_ID_HEADING_RE = re.compile(r"^\s*###\s+([^\n]+?)\s*$", re.MULTILINE)


def ux_direction_ids(ux_direction_md) -> list[str]:
    """Extract all level-3 heading texts from ux-direction.md."""
    p = Path(ux_direction_md)
    if not p.is_file():
        return []
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    return [m.group(1).strip() for m in _ID_HEADING_RE.finditer(text)]


def check_kebab_case_ids(ux_direction_md) -> tuple[bool, list[str]]:
    """Return (all_valid, invalid_ids) for `###` headings."""
    ids = ux_direction_ids(ux_direction_md)
    invalid = [i for i in ids if not KEBAB_RE.match(i)]
    return (not invalid, invalid)


# ---------------------------------------------------------------------------
# Git checks (subprocess-based)
# ---------------------------------------------------------------------------
def _run_git(repo_path: str, args: list[str], timeout: float = 10.0) -> str:
    """Run a git command, return stdout. Empty string on failure."""
    if not os.path.isdir(repo_path):
        return ""
    try:
        res = subprocess.run(
            ["git", "-C", repo_path, *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError):
        return ""
    if res.returncode != 0:
        return ""
    return res.stdout


def git_commit_messages(repo_path: str, base_commit: str, head: str = "HEAD") -> list[str]:
    """git log {base}..{head} --format=%s. Empty list on error."""
    out = _run_git(repo_path, ["log", f"{base_commit}..{head}", "--format=%s"])
    return [line for line in out.splitlines() if line]


def git_changed_files(repo_path: str, base_commit: str, head: str = "HEAD") -> list[str]:
    """git diff --name-only {base}..{head}."""
    out = _run_git(repo_path, ["diff", "--name-only", f"{base_commit}..{head}"])
    return [line for line in out.splitlines() if line]


def git_diff_text(repo_path: str, base_commit: str, head: str = "HEAD") -> str:
    """git diff {base}..{head} — raw unified diff."""
    return _run_git(repo_path, ["diff", f"{base_commit}..{head}"])


def check_git_commit_for_task(repo_path: str, base_commit: str, task_id: str) -> bool:
    """True if any commit subject matches `jarfis({task_id}):`."""
    pattern = re.compile(TASK_COMMIT_RE_TPL.format(task_id=re.escape(task_id)))
    return any(pattern.search(msg) for msg in git_commit_messages(repo_path, base_commit))


def check_code_changes(repo_path: str, base_commit: str, globs: list[str] | None = None) -> bool:
    """True if any file changed under {base}..HEAD matches one of globs.
    globs=None → any change."""
    files = git_changed_files(repo_path, base_commit)
    if not files:
        return False
    if not globs:
        return True
    from fnmatch import fnmatch

    return any(fnmatch(f, g) for f in files for g in globs)


def check_css_var_usage(repo_path: str, base_commit: str) -> bool:
    """True if diff contains `var(--` on an added line."""
    diff = git_diff_text(repo_path, base_commit)
    for line in diff.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            if CSS_VAR_RE.search(line):
                return True
    return False
