"""JARFIS Quality Gate — run lint/typecheck on edited files.

Called by hooks/jarfis-quality-gate.sh (PostToolUse).
Also registered as `jarfis quality-gate <file_path>` in CLI.

Walks up from the file to find package.json/tsconfig.json,
then runs biome or prettier + tsc depending on project config.
"""

import json
import os
import subprocess
import sys

# Extensions and their check strategies
TS_EXTENSIONS = {".ts", ".tsx", ".mts"}
JS_EXTENSIONS = {".js", ".jsx", ".mjs"}
FORMAT_ONLY_EXTENSIONS = {".json", ".css", ".scss"}
ALL_CHECKABLE = TS_EXTENSIONS | JS_EXTENSIONS | FORMAT_ONLY_EXTENSIONS


def find_project_root(file_path):
    """Walk up from file_path to find nearest directory with package.json."""
    current = os.path.dirname(os.path.abspath(file_path))
    while current != os.path.dirname(current):  # stop at filesystem root
        if os.path.isfile(os.path.join(current, "package.json")):
            return current
        current = os.path.dirname(current)
    return None


def has_biome(project_root):
    """Check if project uses biome (biome.json or biome.jsonc exists)."""
    for name in ("biome.json", "biome.jsonc"):
        if os.path.isfile(os.path.join(project_root, name)):
            return True
    return False


def find_executable(project_root, name):
    """Find executable: project-local npx first, then global."""
    local_bin = os.path.join(project_root, "node_modules", ".bin", name)
    if os.path.isfile(local_bin):
        return local_bin
    # Try npx
    return None


def run_check(cmd, cwd, label, timeout=10):
    """Run a check command, return (success, output)."""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = (result.stdout + result.stderr).strip()
        if result.returncode != 0:
            return False, f"[{label}] FAIL:\n{output}"
        return True, f"[{label}] OK"
    except subprocess.TimeoutExpired:
        return False, f"[{label}] TIMEOUT (>{timeout}s)"
    except FileNotFoundError:
        return False, f"[{label}] SKIP (command not found: {cmd[0]})"


def check_file(file_path):
    """Run appropriate checks for the given file. Returns (results, skipped)."""
    ext = os.path.splitext(file_path)[1].lower()

    if ext not in ALL_CHECKABLE:
        return [], True

    project_root = find_project_root(file_path)
    if not project_root:
        return [("[quality-gate] No package.json found, skipping")], True

    results = []
    use_biome = has_biome(project_root)

    # Format check
    if use_biome:
        biome_bin = find_executable(project_root, "biome")
        if biome_bin:
            cmd = [biome_bin, "check", "--no-errors-on-unmatched", file_path]
        else:
            cmd = ["npx", "biome", "check", "--no-errors-on-unmatched", file_path]
        ok, msg = run_check(cmd, project_root, "biome")
        results.append(msg)
    else:
        prettier_bin = find_executable(project_root, "prettier")
        if prettier_bin:
            cmd = [prettier_bin, "--check", file_path]
        else:
            cmd = ["npx", "prettier", "--check", file_path]
        ok, msg = run_check(cmd, project_root, "prettier")
        results.append(msg)

    # TypeScript type check (only for .ts/.tsx/.mts)
    if ext in TS_EXTENSIONS:
        tsconfig = os.path.join(project_root, "tsconfig.json")
        if os.path.isfile(tsconfig):
            tsc_bin = find_executable(project_root, "tsc")
            if tsc_bin:
                cmd = [tsc_bin, "--noEmit", "--skipLibCheck"]
            else:
                cmd = ["npx", "tsc", "--noEmit", "--skipLibCheck"]
            ok, msg = run_check(cmd, project_root, "tsc", timeout=10)
            results.append(msg)

    return results, False


def main(args):
    """Entry point for CLI: jarfis quality-gate <file_path>"""
    if not args:
        print(
            json.dumps({"error": "Usage: jarfis quality-gate <file_path>"}),
            file=sys.stderr,
        )
        sys.exit(1)

    file_path = args[0]
    results, skipped = check_file(file_path)

    if skipped:
        print(json.dumps({"status": "skipped", "file": file_path}))
        return

    has_failure = any("FAIL" in r for r in results)
    output = {
        "status": "warn" if has_failure else "ok",
        "file": file_path,
        "checks": results,
    }
    print(json.dumps(output, ensure_ascii=False))

    # Also print human-readable to stderr for hook output
    if has_failure:
        for r in results:
            if "FAIL" in r:
                print(r, file=sys.stderr)
