"""JARFIS Measure — prompt file token measurement + structure diagnostics.

Usage: jarfis measure [options] [dir1 dir2 ...]

Options:
    --exclude file1,file2   Exclude files (comma-separated)
    --index path            Index file for mismatch check
    --verbose               Verbose output to stderr
    --diagnostics           Include D-1 diagnostics (codeblocks, headers, prompts)
"""

import json
import os
import re
import sys

from .utils import get_claude_dir, json_output


def main(args):
    exclude = []
    index_path = ""
    verbose = False
    diagnostics = False
    dirs = []
    extra_files = []

    # Parse args
    i = 0
    while i < len(args):
        if args[i] == "--exclude" and i + 1 < len(args):
            exclude = [x.strip() for x in args[i + 1].split(",") if x.strip()]
            i += 2
        elif args[i] == "--index" and i + 1 < len(args):
            index_path = args[i + 1]
            i += 2
        elif args[i] == "--verbose":
            verbose = True
            i += 1
        elif args[i] == "--diagnostics":
            diagnostics = True
            i += 1
        else:
            dirs.append(args[i])
            i += 1

    claude_dir = get_claude_dir()

    if not dirs:
        dirs = [
            os.path.join(claude_dir, "commands", "jarfis"),
            os.path.join(claude_dir, "agents", "jarfis"),
        ]
        main_file = os.path.join(claude_dir, "commands", "jarfis.md")
        if os.path.isfile(main_file):
            extra_files.append(main_file)

    def log(msg):
        if verbose:
            print(f"[measure] {msg}", file=sys.stderr)

    def is_excluded(fname):
        return os.path.basename(fname) in exclude

    # Collect files
    files = []
    for d in dirs:
        if os.path.isfile(d):
            files.append(d)
        elif os.path.isdir(d):
            for root, _dirs, fnames in os.walk(d):
                if ".distill-backup" in root:
                    continue
                for fn in sorted(fnames):
                    if fn.endswith(".md"):
                        files.append(os.path.join(root, fn))

    files.extend(extra_files)

    # Measure each file
    total_lines = 0
    total_chars = 0
    total_tokens = 0
    file_count = 0
    file_entries = []

    for filepath in files:
        fname = os.path.basename(filepath)
        if is_excluded(fname):
            log(f"Excluded: {fname}")
            continue
        if not os.path.isfile(filepath):
            log(f"Not found: {filepath}")
            continue

        with open(filepath, "rb") as f:
            content_bytes = f.read()
        try:
            content = content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            content = content_bytes.decode("utf-8", errors="replace")

        lines = content.count("\n")
        if content and not content.endswith("\n"):
            lines += 1
        chars = len(content_bytes)
        tokens_est = chars // 4

        rel_path = filepath
        if filepath.startswith(claude_dir + "/"):
            rel_path = filepath[len(claude_dir) + 1:]

        total_lines += lines
        total_chars += chars
        total_tokens += tokens_est
        file_count += 1

        entry = {
            "path": rel_path,
            "name": fname,
            "lines": lines,
            "chars": chars,
            "tokens_est": tokens_est,
        }

        if diagnostics:
            content_lines = content.split("\n")

            # Codeblock analysis
            in_block = False
            cb_lines = 0
            for line in content_lines:
                if line.startswith("```"):
                    in_block = not in_block
                elif in_block:
                    cb_lines += 1
            cb_ratio = round(cb_lines / lines, 2) if lines > 0 else 0.0

            # Header extraction (## level)
            headers = []
            for idx, line in enumerate(content_lines, 1):
                if line.startswith("##"):
                    headers.append({"line": idx, "text": line.strip()})
                    if len(headers) >= 30:
                        break

            # Prompt pattern detection
            prompt_patterns = []
            prompt_re = re.compile(r"📄 프롬프트:|📄 템플릿:|Task prompt:|prompt:")
            for idx, line in enumerate(content_lines, 1):
                if prompt_re.search(line):
                    prompt_patterns.append({"line": idx, "text": line.strip()})
                    if len(prompt_patterns) >= 20:
                        break

            entry["diagnostics"] = {
                "codeblock_lines": cb_lines,
                "codeblock_ratio": cb_ratio,
                "headers": headers,
                "prompt_patterns": prompt_patterns,
            }

        file_entries.append(entry)
        log(f"Measured: {fname} ({lines} lines, ~{tokens_est}tok)")

    # Index mismatch check
    result = {"files": file_entries}

    if index_path and os.path.isfile(index_path):
        with open(index_path) as f:
            index_content = f.read()
        index_files = set(re.findall(r"[a-zA-Z0-9_-]+\.md", index_content))

        disk_files = set()
        for d in dirs:
            if os.path.isdir(d):
                for root, _dirs, fnames in os.walk(d):
                    if ".distill-backup" in root:
                        continue
                    for fn in fnames:
                        if fn.endswith(".md"):
                            disk_files.add(fn)

        mismatches = []
        for m in sorted(index_files - disk_files)[:10]:
            mismatches.append(f"missing_on_disk:{m}")
        for n in sorted(disk_files - index_files)[:10]:
            mismatches.append(f"not_in_index:{n}")

        result["index_mismatches"] = mismatches

    result["total"] = {
        "files": file_count,
        "lines": total_lines,
        "chars": total_chars,
        "tokens_est": total_tokens,
    }

    json_output(result)
