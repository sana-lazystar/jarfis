# JARFIS Search Index

> **Locale**: All user-facing output must be presented in $LOCALE language. Internal instructions: English.

> Batch-create or refresh semantic indexes for wiki, meetings, and works across registered Orgs.

User request: $ARGUMENTS

---

## Prerequisites

- `/jarfis:search-setup` completed (sentence-transformers installed)
- `/jarfis:org-init` completed (Org registered + wiki structure created)

## Flag Parsing

- If `$ARGUMENTS` contains the `--current` flag: Index current Org only
- No flag: Index all Orgs (default)

## Execution Flow

### 1. Check venv

```bash
test -d ~/.claude/.jarfis-venv && echo "OK" || echo "MISSING"
```

If `MISSING`, inform the user and abort:
```
sentence-transformers is not installed.
Please run /jarfis:search-setup first.
```

### 2. Load Org List

**`--current` mode**: Use `jarfis_cli.py preflight` to identify the current Org only
```bash
python3 ~/.claude/scripts/jarfis_cli.py preflight
```
Use `org_root` and `org_dir` from the JSON to target only the current Org.

**Full mode** (default):
```bash
python3 -c "
import json, os
personal_file = os.path.expanduser('~/.claude/.jarfis-personal-dir')
if os.path.isfile(personal_file):
    with open(personal_file) as f:
        personal = f.read().strip()
else:
    source_file = os.path.expanduser('~/.claude/.jarfis-source')
    if os.path.isfile(source_file):
        with open(source_file) as f:
            personal = os.path.join(f.read().strip(), '.personal')
    else:
        personal = os.path.expanduser('~/repos/jarfis/.personal')
orgs_path = os.path.join(personal, 'orgs', 'orgs.json')
if os.path.isfile(orgs_path):
    with open(orgs_path) as f:
        data = json.load(f)
    print(json.dumps(data, ensure_ascii=False))
else:
    print(json.dumps({'orgs': []}))
"
```

**If 0 Orgs are registered** — inform the user and abort:
```
No registered Organizations found.
Please register an Org first with /jarfis:org-init.
```

### 3. Batch Indexing per Org

For each Org, sequentially index all 3 types: **wiki, meetings, works**.

**3-1. Check index status**:
```bash
python3 ~/.claude/scripts/jarfis_cli.py search status --org-root {org_root}
```

**3-2. Run indexing** (only for scopes that are stale or not yet indexed):

```bash
# Wiki
python3 ~/.claude/scripts/jarfis_cli.py search index wiki --org-root {org_root}

# Meetings
python3 ~/.claude/scripts/jarfis_cli.py search index meetings --org-root {org_root}

# Works
python3 ~/.claude/scripts/jarfis_cli.py search index works --org-root {org_root}
```

On first run, display the bge-m3 model download notice:
```
Note: On first run, the bge-m3 model will be downloaded automatically (~2GB).
```

### 4. Report Results

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Search Index Complete
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  {org_name}:
    ✅ wiki     — {files} files, {chunks} chunks
    ✅ meetings — {files} files, {chunks} chunks
    ✅ works    — {files} files, {chunks} chunks
    ⏭️ wiki     — Up to date (skipped)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

If any scope failed, display the error message alongside:
```
  ❌ {scope} — {error message}
```

If the error includes a `memory_insufficient` hint: Abort all indexing + show warning:
```
  ⚠️ Indexing aborted due to insufficient memory.
  Available memory: {N}GB / Minimum required: 4GB
  Close other apps (VS Code, Chrome, Figma, etc.) and try again.
  Alternatively, adjust the threshold via the JARFIS_MEMORY_THRESHOLD_GB environment variable.
```
