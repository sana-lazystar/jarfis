"""Read Markdown + extract sections under `##` headings.

v4.0 policy (system-spec §5.6, phase-spec context-injection):
    * files ≤ 50 lines → return full text (section filter ignored)
    * files > 50 lines → sections list, if given, filters
    * sections is None / [] → return full text
    * directory path → return INDEX.md content (if any); else None
      (directory walk is v4.1)
"""

import os
import re


_HEADING_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
_SMALL_FILE_THRESHOLD = 50


class ReadResult:
    """Light wrapper returned by `read_and_extract` to expose meta.

    Not a dataclass — created ad-hoc with only the keys the caller needs.
    """

    __slots__ = ("text", "meta")

    def __init__(self, text, meta):
        self.text = text
        self.meta = meta


def read_file(path, optional=True):
    """Read a file or None if missing and optional.

    Raises:
        FileNotFoundError — file absent and optional=False.
    """
    if os.path.isdir(path):
        index_md = os.path.join(path, "INDEX.md")
        if os.path.isfile(index_md):
            with open(index_md, encoding="utf-8") as f:
                return f.read()
        if optional:
            return None
        raise FileNotFoundError(f"Directory has no INDEX.md: {path}")

    if not os.path.isfile(path):
        if optional:
            return None
        raise FileNotFoundError(f"File not found: {path}")

    with open(path, encoding="utf-8") as f:
        return f.read()


def extract_sections(markdown_text, section_titles):
    """Return concatenation of `## <title>` sections in order of appearance.

    - Case-insensitive title match.
    - Each section includes its heading line + body until the next `##` (or EOF).
    - Missing titles are simply skipped (caller records via `missing_sections`).
    - Returns tuple (joined_text, missing_titles_list).
    """
    if not section_titles:
        return markdown_text, []

    wanted = {t.strip().lower(): t for t in section_titles}
    found = {}

    sections = _split_sections(markdown_text)
    for heading, body in sections:
        key = heading.strip().lower()
        if key in wanted and key not in found:
            found[key] = f"## {heading}\n{body}".rstrip() + "\n"

    ordered_parts = []
    missing = []
    for title in section_titles:
        key = title.strip().lower()
        if key in found:
            ordered_parts.append(found[key])
        else:
            missing.append(title)

    return "\n".join(ordered_parts), missing


def file_size_check(text):
    """Return the number of lines in `text` (fast heuristic for 50-line rule)."""
    if not text:
        return 0
    return text.count("\n") + (0 if text.endswith("\n") else 1)


def read_and_extract(path, sections, optional=True):
    """High-level helper: read + (size check) + section extract.

    Returns `ReadResult` with:
        .text  — str or None (None = file missing and optional=True,
                 OR directory without INDEX.md)
        .meta  — dict with keys:
            injected (bool)
            reason (str, present when injected=False)
            sections_applied (bool, present when file > threshold and sections given)
            missing_sections (list[str], present when any section not found)
            directory_no_index (bool, present when path was a dir without INDEX.md)
    """
    meta = {}

    if os.path.isdir(path):
        index_md = os.path.join(path, "INDEX.md")
        if not os.path.isfile(index_md):
            return ReadResult(
                None,
                {"injected": False, "reason": "directory_no_index",
                 "directory_no_index": True},
            )
        with open(index_md, encoding="utf-8") as f:
            text = f.read()
    elif not os.path.isfile(path):
        if optional:
            return ReadResult(None, {"injected": False, "reason": "file_not_found"})
        raise FileNotFoundError(f"File not found: {path}")
    else:
        with open(path, encoding="utf-8") as f:
            text = f.read()

    line_count = file_size_check(text)

    if sections and line_count > _SMALL_FILE_THRESHOLD:
        extracted, missing = extract_sections(text, list(sections))
        meta["sections_applied"] = True
        if missing:
            meta["missing_sections"] = missing
        meta["injected"] = bool(extracted)
        if not extracted:
            meta["reason"] = "no_matching_sections"
        return ReadResult(extracted or None, meta)

    if sections and line_count <= _SMALL_FILE_THRESHOLD:
        meta["sections_applied"] = False
        meta["sections_skipped_small_file"] = True

    meta["injected"] = True
    return ReadResult(text, meta)


def _split_sections(markdown_text):
    """Return [(heading_title, body), ...] in document order.

    Body excludes the heading line itself; preceding preamble (before first
    heading) is discarded (not a section).
    """
    headings = list(_HEADING_RE.finditer(markdown_text))
    sections = []
    for i, m in enumerate(headings):
        title = m.group(1).strip()
        body_start = m.end() + 1  # skip newline after heading line
        body_end = headings[i + 1].start() if i + 1 < len(headings) else len(markdown_text)
        body = markdown_text[body_start:body_end]
        sections.append((title, body))
    return sections
