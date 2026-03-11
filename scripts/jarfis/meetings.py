"""JARFIS Recent Meetings — list recent meetings as JSON.

Usage: jarfis meetings [count]
"""

import json
import os
import re

from .utils import get_workspace_dir, json_output


def main(args):
    count = int(args[0]) if args else 3

    workspace_dir = get_workspace_dir()
    meetings_dir = os.path.join(workspace_dir, "meetings")

    if not os.path.isdir(meetings_dir):
        json_output([])
        return

    # Find meeting directories with summary.md
    meeting_dirs = []
    try:
        for entry in os.listdir(meetings_dir):
            full = os.path.join(meetings_dir, entry)
            if os.path.isdir(full) and os.path.isfile(os.path.join(full, "summary.md")):
                mtime = os.path.getmtime(full)
                meeting_dirs.append((mtime, full))
    except OSError:
        json_output([])
        return

    if not meeting_dirs:
        json_output([])
        return

    # Sort by mtime descending, take top N
    meeting_dirs.sort(key=lambda x: x[0], reverse=True)
    meeting_dirs = meeting_dirs[:count]

    results = []
    for _, d in meeting_dirs:
        dirname = os.path.basename(d)
        summary_path = os.path.join(d, "summary.md")

        # Extract name: remove YYYYMMDD- prefix
        name = re.sub(r"^\d{8}-", "", dirname)

        date_val = ""
        summary_val = ""
        idea_val = ""

        try:
            with open(summary_path) as f:
                content = f.read()

            # Parse YAML frontmatter
            fm_match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
            if fm_match:
                fm = fm_match.group(1)
                for line in fm.split("\n"):
                    line = line.strip()
                    if line.startswith("date:"):
                        date_val = line.split(":", 1)[1].strip().strip("\"'")
                    elif line.startswith("idea:"):
                        idea_val = line.split(":", 1)[1].strip().strip("\"'")
                    elif line.startswith("meeting_name:") and not name:
                        name = line.split(":", 1)[1].strip().strip("\"'")

            # Fallback date from dirname
            if not date_val:
                date_match = re.match(r"^(\d{4})(\d{2})(\d{2})", dirname)
                if date_match:
                    date_val = f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}"

            # Summary from idea or first body line
            summary_val = idea_val
            if not summary_val:
                parts = content.split("---")
                if len(parts) >= 3:
                    body = parts[2].strip()
                    first_line = body.split("\n")[0].strip().lstrip("#").strip() if body else ""
                    summary_val = first_line[:80]
        except Exception:
            pass

        rel_path = "meetings/" + dirname
        results.append({
            "path": rel_path,
            "name": name,
            "date": date_val,
            "summary": summary_val,
        })

    json_output(results)
