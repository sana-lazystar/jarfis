"""JARFIS shared utilities — path resolution, JSON output helpers."""

import json
import os
import sys

STANDALONE_ORG = "_standalone"


def get_claude_dir():
    """Return ~/.claude path."""
    return os.path.join(os.path.expanduser("~"), ".claude")


def get_source_path():
    """Read .jarfis-source to find repo path, fallback ~/repos/jarfis."""
    source_file = os.path.join(get_claude_dir(), ".jarfis-source")
    if os.path.isfile(source_file):
        with open(source_file) as f:
            return f.read().strip()
    return os.path.join(os.path.expanduser("~"), "repos", "jarfis")


def get_personal_dir():
    """Resolve .personal base directory.

    Priority:
    1. ~/.claude/.jarfis-personal-dir content
    2. {source_path}/.personal
    3. ~/repos/jarfis/.personal
    """
    claude_dir = get_claude_dir()
    personal_file = os.path.join(claude_dir, ".jarfis-personal-dir")
    if os.path.isfile(personal_file):
        with open(personal_file) as f:
            val = f.read().strip()
            if val:
                return val

    return os.path.join(get_source_path(), ".personal")


def _resolve_org_name(project_dir=None):
    """Determine org name from project context.

    Returns org name string or STANDALONE_ORG if no org found.
    """
    if project_dir:
        org_root = find_org_root(project_dir)
        if org_root:
            profile = os.path.join(org_root, ".jarfis-org", "org-profile.md")
            if os.path.isfile(profile):
                with open(profile) as f:
                    for line in f:
                        if line.strip().startswith("org:"):
                            name = line.split(":", 1)[1].strip()
                            if name:
                                return name
            return os.path.basename(org_root)
    return STANDALONE_ORG


def get_org_dir(project_dir=None):
    """Resolve org-aware workspace directory (v4.4 — physical org-root data source).

    Semantics:
        - If ``project_dir`` is supplied AND ``find_org_root(project_dir)`` finds
          an org-root with ``.jarfis-org/org-profile.md`` → return
          ``{org_root}/.jarfis-org/`` (the single org container holding
          wiki/, meetings/, works/, learnings.md).
        - Otherwise (standalone — no org context) → return ``{personal_dir}/``
          flat, with ``meetings/``, ``works/`` as direct subdirs of
          ``.personal/``. The ``orgs/_standalone/`` wrapper used in v4.3 has
          been abandoned (per ADR — v4.4 org-root data-source restructure).

    Args:
        project_dir: Project directory to determine org context.
                     If None or not under any org, returns flat personal_dir.
    """
    personal = get_personal_dir()
    if project_dir:
        org_root = find_org_root(project_dir)
        if org_root:
            jarfis_org = os.path.join(org_root, ".jarfis-org")
            org_profile = os.path.join(jarfis_org, "org-profile.md")
            if os.path.isfile(org_profile):
                return jarfis_org
    return personal


def get_all_workspaces():
    """List all org workspace directories for cross-org scanning (v4.4 rewrite).

    Behavior (per Critic Fix A — ADR org-root data-source restructure):
      1. Read ``{personal_dir}/orgs/orgs.json`` if present.
      2. For each registered org with a ``root`` field, yield
         ``{root}/.jarfis-org/`` if that directory exists.
      3. Append ``{personal_dir}/`` itself as the standalone bucket
         (flat — no ``_standalone`` wrapper).
      4. Filter to existing directories only.

    Returns list of absolute paths.
    """
    personal = get_personal_dir()
    result = []
    orgs_json = os.path.join(personal, "orgs", "orgs.json")
    if os.path.isfile(orgs_json):
        try:
            with open(orgs_json) as f:
                data = json.load(f)
            for entry in data.get("orgs", []):
                root = entry.get("root")
                if not root:
                    continue
                jarfis_org = os.path.join(root, ".jarfis-org")
                if os.path.isdir(jarfis_org):
                    result.append(jarfis_org)
        except (json.JSONDecodeError, OSError):
            pass

    # Standalone bucket: flat personal_dir.
    if os.path.isdir(personal):
        result.append(personal)
    return result


def get_learnings_path(project_dir=None):
    """Resolve org-aware learnings.md path (v4.4).

    Returns ``{org_root}/.jarfis-org/learnings.md`` for registered orgs, or
    ``{personal_dir}/learnings.md`` for standalone (flat). The path formula
    is unchanged ({org_dir}/learnings.md); the change is in get_org_dir's
    semantic.
    """
    ws = get_org_dir(project_dir)
    return os.path.join(ws, "learnings.md")


def json_output(data):
    """Print JSON to stdout."""
    print(json.dumps(data, ensure_ascii=False))


def json_error(msg, **extra):
    """Print JSON error to stderr and exit 1."""
    err = {"error": msg}
    err.update(extra)
    print(json.dumps(err, ensure_ascii=False), file=sys.stderr)
    sys.exit(1)


def parse_json_value(value_str):
    """Try to parse a string as JSON (number, bool, object, array), fallback to string.

    v4.0.2 OBS-2: Handle shell-quoting edge cases. When a value arrives as an
    over-quoted JSON literal (e.g. `'"[]"'`), ``json.loads`` returns the inner
    string ``"[]"`` instead of an empty list. If the parsed result is still a
    string that looks JSON-shaped (starts with ``[`` or ``{``), retry once with
    the intermediate value. This makes ``state set-nested k '[]'`` behave the
    same whether the shell preserves the outer quotes or not.
    """
    if not isinstance(value_str, str):
        return value_str
    try:
        result = json.loads(value_str)
    except (json.JSONDecodeError, ValueError):
        return value_str
    if isinstance(result, str) and result and result[0] in "[{":
        try:
            return json.loads(result)
        except (json.JSONDecodeError, ValueError):
            return result
    return result


def read_file_stripped(path):
    """Read a file and return stripped content."""
    with open(path) as f:
        return f.read().strip()


def find_org_root(project_dir):
    """Find Organization root by traversing up to 5 parent directories.

    Looks for .jarfis-org/org-profile.md to identify the org root.
    Returns the org root path or None if not found.
    """
    current = os.path.abspath(project_dir)
    for _ in range(5):
        org_profile = os.path.join(current, ".jarfis-org", "org-profile.md")
        if os.path.isfile(org_profile):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent
    return None
