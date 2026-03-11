"""JARFIS shared utilities — path resolution, JSON output helpers."""

import json
import os
import sys


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


def get_workspace_dir():
    """Resolve workspace directory.

    Priority:
    1. ~/.claude/.jarfis-works-dir content
    2. {source_path}/.local/workspace
    3. ~/repos/jarfis/.local/workspace
    """
    claude_dir = get_claude_dir()
    works_dir_file = os.path.join(claude_dir, ".jarfis-works-dir")
    if os.path.isfile(works_dir_file):
        with open(works_dir_file) as f:
            val = f.read().strip()
            if val:
                return val

    source_file = os.path.join(claude_dir, ".jarfis-source")
    if os.path.isfile(source_file):
        with open(source_file) as f:
            return os.path.join(f.read().strip(), ".local", "workspace")

    return os.path.join(os.path.expanduser("~"), "repos", "jarfis", ".local", "workspace")


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
    """Try to parse a string as JSON (number, bool, object), fallback to string."""
    try:
        return json.loads(value_str)
    except (json.JSONDecodeError, ValueError):
        return value_str


def read_file_stripped(path):
    """Read a file and return stripped content."""
    with open(path) as f:
        return f.read().strip()
