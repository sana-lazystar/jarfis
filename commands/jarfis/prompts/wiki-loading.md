# Wiki Loading — Shared Module

> This file is a shared wiki-loading module referenced by work.md and meeting.md.
> **Locale**: Present ALL user-facing output in $LOCALE language. Internal reasoning: English.
> Only runs in projects registered under an Org.

## Prerequisites

- `preflight` JSON's `org_root` is non-null
- `{org_root}/.jarfis/wiki/INDEX.md` exists

## 2-Step Lightweight Loading (for Fix mode)

1. **Read INDEX.md**: Read `{org_root}/.jarfis/wiki/INDEX.md` to identify Quick Reference + Directory Map
2. **Selectively load relevant sections only**: Read only the `_index.md` of sections related to the current task
   - e.g.: FE bug fix → DESIGN/_index.md + QA/_index.md
   - e.g.: BE API change → TA/_index.md + QA/_index.md

> 2-Step reads INDEX.md + at most 2 relevant _index.md files. Individual files are not read.
> (Optional: can be replaced with `jarfis_cli.py wiki search --top-k 2`, but the default _index.md approach is preferred)

## 4-Step Full Loading (for Work mode, Extend mode)

1. **Read INDEX.md**: Quick Reference + Directory Map → understand the full wiki structure
2. **Read all section _index.md files**: Read the `_index.md` of all 4 sections — PO, DESIGN, TA, QA
3. **Load related files via semantic search**:
   ```bash
   python3 ~/.claude/scripts/jarfis_cli.py search wiki "{core keywords/phrases of the current plan}" --top-k 5
   ```
   - From the result JSON's `results` array, read only files with `score` >= 0.5
   - If `stale_warning` is present, display it to the user (recommend index refresh)
   - **Fallback**: On search failure (no index / module not installed / insufficient memory) → display to the user: `⚠️ Semantic search is unavailable. Falling back to LLM-based search.` (if the error includes a `memory_insufficient` hint, append `(insufficient memory)`) → use the legacy approach (_index.md summary-based LLM judgment) to select up to 5 related files
4. **Apply Cascading Specificity**: When wiki content conflicts with $DOCS_DIR artifacts, $DOCS_DIR takes precedence

> 4-Step reads INDEX.md → 4 _index.md files → up to 5 related files.

## Cascading Specificity Rules

Priority when information conflicts:
```
$DOCS_DIR (current task artifacts) > project/.jarfis (project profile/context) > wiki/ (accumulated org knowledge) > INDEX.md (table of contents)
```

- Topics **covered by this task**: $DOCS_DIR artifacts are the most current and take precedence over wiki
- Topics **not covered by this task**: Wiki content remains valid — reference it to maintain consistency
