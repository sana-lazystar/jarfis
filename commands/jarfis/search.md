# JARFIS Search — Semantic Search

> **Locale**: All user-facing output must be presented in $LOCALE language. Internal instructions: English.

> Perform semantic search across meetings, works, and wiki.

User request: $ARGUMENTS

---

## Flag Parsing

Separate flags and query from `$ARGUMENTS`:

| Flag | Meaning |
|------|---------|
| `--meetings` | Search meetings only |
| `--works` | Search works only |
| `--wiki` | Search wiki only |
| `--jarfis` | Search the JARFIS self-knowledge corpus only (org-agnostic — commands/jarfis, agents/jarfis, scripts/jarfis, hooks; ADR-0002) |
| (none) | Search all per-Org scopes (meetings + works + wiki). `--jarfis` is NOT included in `all` because it is a separate, system-level corpus. |

Multiple flags allowed: `--meetings --works query` searches meetings + works only

**Order**: Flags first, query after. Example: `/jarfis:search --works return policy`

## Execution

### 1. Extract Query

Remove flags from the input; the remainder is `$QUERY`.
If `$QUERY` is empty, use AskUserQuestion to prompt for a search term.

### 2. Determine Scope

- No flags: `all`
- `--meetings`: `meetings`
- `--works`: `works`
- `--wiki`: `wiki`
- `--jarfis`: `jarfis` (org-agnostic — runs against `{JARFIS_SOURCE}/.personal/.jarfis-index/`)
- Multiple flags: Search only the specified scopes (call CLI for each, then merge results)

### 3. Run Search

```bash
python3 ~/.claude/scripts/jarfis_cli.py search {scope} "{$QUERY}" --top-k 10 --pretty
```

For multiple scopes (e.g., `--meetings --works`):
```bash
# Call each as JSON and merge results
python3 ~/.claude/scripts/jarfis_cli.py search meetings "{$QUERY}" --top-k 5
python3 ~/.claude/scripts/jarfis_cli.py search works "{$QUERY}" --top-k 5
```
Merge results by score and display in human-readable format.

### 4. Display Results

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Search: "{$QUERY}"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  1. [meetings] 20260326-API-GET-Tanstack-migration/summary.md
     score: 0.87  |  section: Key Decisions
     Adopted TanStack Query for GET APIs...

  2. [works] 20260326-feature-IWS26H1-417/prd.md
     score: 0.82  |  section: Background
     ...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

If no results:
```
  No results found. Verify the index is up to date: /jarfis:search-index --current
```

If the search fails (error JSON returned):
- If `hint` is `memory_insufficient`:
  ```
  ⚠️ Semantic search is unavailable (insufficient memory). Close other apps and retry, or files will be browsed directly.
  ```
  Then use `_index.md` to identify relevant files via LLM judgment and read them directly to answer.
- If `hint` is `/jarfis:search-setup`: Guide the user to install as before

### 5. Detail View Guidance

Display at the bottom of results:
```
  💡 To view file contents, just mention the file path.
```
If the user mentions a file path, read and display that file.
