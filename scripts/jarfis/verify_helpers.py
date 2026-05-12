"""JARFIS verify helpers — M3.

Pure helpers used by phase-verify. See implement-plan A.7 + m3-test-results §3.1.

Two groups:
    * Evaluators: state dict → branch condition (7)
    * Checks: filesystem / markdown / git inspections (7+)
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

TASK_COMMIT_RE_TPL = r"jarfis\({task_id}\)\s*:"
CSS_VAR_RE = re.compile(r"var\(--")

# Stage 3 — kebab-case slug enclosed in backticks (tasks.md / review.md convention).
_BACKTICK_SLUG_RE = re.compile(r"`([a-z][a-z0-9-]{1,40})`")

# Stage 3 — FE source extensions scanned by check_fe_routes_match_ia (R-8).
_FE_SOURCE_EXT = (".ts", ".tsx", ".js", ".jsx", ".vue", ".svelte", ".astro")
_FE_SKIP_DIRS = {
    "node_modules", ".git", "dist", "build", ".next", ".nuxt",
    "out", ".turbo", "coverage", ".svelte-kit",
}


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


# ---------------------------------------------------------------------------
# Stage 3 — IA SSOT checks (ia-as-po-ssot-v2-spine L4 Verification layer)
#
# These helpers cross-check the IA manifest against other Phase artifacts:
#   - tasks.md (Phase 2)   — slugs referenced in tasks must exist in IA
#   - design/  (Phase 3)   — 1:1 mapping figma mode only (supplied skipped)
#   - review.md (Phase 5)  — each IA slug mentioned at least once
#   - org wiki (Phase 6)   — work IA fully merged into Org IA
#   - FE source (Phase 4)  — IA routes appear in code (best-effort WARNING)
#
# All helpers are tolerant: missing manifest / missing input file → return
# []. They are gated by the caller (_phase_*_verify) which only calls them
# when `discovery/ia/` exists (F1 forward-only auto-detect).
# ---------------------------------------------------------------------------


def _load_manifest_pages(ia_dir: Path) -> list[dict]:
    """Read manifest.json → pages list, or [] on any error."""
    manifest_path = Path(ia_dir) / "manifest.json"
    if not manifest_path.is_file():
        return []
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    pages = data.get("pages") if isinstance(data, dict) else None
    return pages if isinstance(pages, list) else []


def check_ia_pages_match_tasks(ia_dir: Path, tasks_md: Path) -> list[str]:
    """L2 mapping check — every page-slug referenced in tasks.md has a corresponding IA page.

    Convention: tasks.md references a page using backtick-enclosed kebab
    slugs (e.g. `home`, `user-profile`). Any backtick-slug that is NOT a
    valid IA page is reported as missing. Extra IA pages (no task) are OK.

    Returns missing[] list (empty = OK). Soft if ia_dir or tasks_md absent.
    """
    tasks_md = Path(tasks_md)
    if not tasks_md.is_file():
        return []
    # Soft-skip when manifest absent — caller already gates on ia_dir.is_dir()
    # but the manifest itself is what we map against. validate_ia (R1) is the
    # right surface for "IA dir present but manifest missing".
    if not (Path(ia_dir) / "manifest.json").is_file():
        return []
    pages = _load_manifest_pages(ia_dir)
    valid_slugs = {p.get("slug") for p in pages if isinstance(p.get("slug"), str)}
    try:
        text = tasks_md.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    referenced = set(_BACKTICK_SLUG_RE.findall(text))
    missing: list[str] = []
    for slug in sorted(referenced):
        if slug not in valid_slugs:
            missing.append(
                f"discovery/ia: tasks.md 가 참조하는 `{slug}` 슬러그에 해당하는 "
                f"pages/{slug}.md 없음 (IA SSOT 위반)"
            )
    return missing


def check_ia_pages_match_design(ia_dir: Path, design_dir: Path, mode: str) -> list[str]:
    """L3 mapping — design slugs ↔ IA pages slugs 1:1 (figma/text modes only).

    supplied mode short-circuits to [] — defense-in-depth alongside the
    caller-side skip in _phase_3_verify (TODO Stage 4 — phase1b prompt
    rewrite will allow re-enabling once import-then-discard contract
    lands).

    A "design slug" is a subdirectory directly under design/ that contains
    a non-empty index.html. Mismatch in either direction (IA ∋ slug ∉
    design  or  design ∋ slug ∉ IA) is reported.
    """
    if mode == "supplied":
        return []
    design_dir = Path(design_dir)
    if not design_dir.is_dir():
        return []
    pages = _load_manifest_pages(ia_dir)
    ia_slugs = {p.get("slug") for p in pages if isinstance(p.get("slug"), str)}
    if not ia_slugs:
        return []
    design_slugs: set[str] = set()
    for child in design_dir.iterdir():
        if not child.is_dir():
            continue
        if child.name in (".git", "_index", "pages"):
            continue
        idx = child / "index.html"
        if idx.is_file():
            design_slugs.add(child.name)
    missing: list[str] = []
    for slug in sorted(ia_slugs - design_slugs):
        missing.append(
            f"discovery/ia page `{slug}` 에 해당하는 design/{slug}/index.html 없음 "
            "(IA↔design 1:1 위반)"
        )
    for slug in sorted(design_slugs - ia_slugs):
        missing.append(
            f"design/{slug}/ 에 해당하는 IA page `{slug}` 없음 "
            "(IA↔design 1:1 위반)"
        )
    return missing


def check_ia_pages_match_review(ia_dir: Path, review_md: Path) -> list[str]:
    """Phase 5 — review.md must mention each IA page slug at least once (case-insensitive).

    Soft if review.md absent (caller already flagged it).
    """
    review_md = Path(review_md)
    if not review_md.is_file():
        return []
    pages = _load_manifest_pages(ia_dir)
    slugs = [p.get("slug") for p in pages if isinstance(p.get("slug"), str)]
    if not slugs:
        return []
    try:
        text = review_md.read_text(encoding="utf-8", errors="replace").lower()
    except OSError:
        return []
    missing: list[str] = []
    for slug in slugs:
        if slug.lower() not in text:
            missing.append(
                f"review/review.md 에 IA page `{slug}` 언급 없음 (Phase 5 coverage 위반)"
            )
    return missing


def check_ia_merge_artifacts(state: dict, docs_dir: str) -> list[str]:
    """Phase 6 — Org IA merge evidence (D11 1:1 + D12 confirm).

    Best-effort: if state.org.root / wiki/PO/projects/{name}/ia/ does not
    exist yet (Stage 6 not done), return []. Otherwise verify:
      - merge.log present.
      - All work IA slugs appear in post-merge Org IA manifest.
    """
    org = (state or {}).get("org") or {}
    org_root = org.get("root")
    work_name = ((state or {}).get("work") or {}).get("name") or ""
    if not org_root or not work_name:
        return []
    work_ia_dir = Path(docs_dir) / "discovery" / "ia"
    org_ia_dir = (
        Path(org_root)
        / ".jarfis-org"
        / "wiki"
        / "PO"
        / "projects"
        / work_name
        / "ia"
    )
    if not org_ia_dir.is_dir():
        return []  # Stage 6 not done yet — silent skip.

    missing: list[str] = []
    merge_log = org_ia_dir / "merge.log"
    if not merge_log.is_file():
        missing.append(
            f"wiki/PO/projects/{work_name}/ia/merge.log 누락 "
            "(Phase 6 merge artifact 미생성)"
        )

    work_pages = {p.get("slug") for p in _load_manifest_pages(work_ia_dir)
                  if isinstance(p.get("slug"), str)}
    org_pages = {p.get("slug") for p in _load_manifest_pages(org_ia_dir)
                 if isinstance(p.get("slug"), str)}
    for slug in sorted(work_pages - org_pages):
        missing.append(
            f"wiki/PO/projects/{work_name}/ia 에 work IA slug `{slug}` 미반영 "
            "(merge 후 1:1 위반)"
        )
    return missing


def check_fe_routes_match_ia(repo_path: str, base_commit: str, ia_dir: Path) -> list[str]:
    """R-8 best-effort grep across React/Vue/Next.js patterns.

    Returns warnings[] list. Caller writes to stderr; NEVER adds to
    missing[]. Heuristic: parse manifest.json for `route` fields then grep
    each route literal (`'/foo'` | `"/foo"` | `` `/foo` ``) across FE
    source files. Any route absent from the aggregated source = warning.

    The base_commit arg is accepted for API symmetry with other helpers
    but is unused — this is a working-tree scan, not a diff scan.
    """
    del base_commit  # unused — working-tree scan
    if not repo_path or not os.path.isdir(repo_path):
        return []
    pages = _load_manifest_pages(ia_dir)
    routes = [p.get("route") for p in pages
              if isinstance(p.get("route"), str) and p.get("route")]
    if not routes:
        return []

    chunks: list[str] = []
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in _FE_SKIP_DIRS]
        for fname in files:
            if not fname.endswith(_FE_SOURCE_EXT):
                continue
            try:
                chunks.append(
                    (Path(root) / fname).read_text(encoding="utf-8", errors="replace")
                )
            except OSError:
                continue
    blob = "\n".join(chunks)

    warnings: list[str] = []
    for route in routes:
        needles = (f"'{route}'", f'"{route}"', f"`{route}`")
        if not any(n in blob for n in needles):
            warnings.append(
                f"IA route `{route}` 가 FE 코드에서 발견되지 않음 "
                f"({Path(repo_path).name} 스캔; R-8 best-effort, FAIL 아님)"
            )
    return warnings
