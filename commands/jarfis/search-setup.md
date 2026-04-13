# JARFIS Search Setup

> **Locale**: All user-facing output must be presented in $LOCALE language. Internal instructions: English.

> One-step installation of sentence-transformers for semantic search

## Execution Flow

### 1. Check Environment

```bash
python3 --version
```

If Python 3 is not available, inform the user and abort:
```
Python 3 is required. Install it with: brew install python3
```

### 2. Create venv + Install Packages

```bash
python3 -m venv ~/.claude/.jarfis-venv && ~/.claude/.jarfis-venv/bin/pip install sentence-transformers
```

- If `~/.claude/.jarfis-venv/` already exists, skip venv creation and only run pip install (upgrade/reinstall)
- Before starting installation, inform the user: "Installing sentence-transformers + dependencies. This may take several minutes on first install."

### 3. Verify Installation

```bash
~/.claude/.jarfis-venv/bin/python3 -c "from sentence_transformers import SentenceTransformer; print('OK')"
```

### 4. Report Results

On success:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Wiki Semantic Search Installation Complete
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  venv: ~/.claude/.jarfis-venv/
  Package: sentence-transformers

  Next steps:
    /jarfis:search-index
    Select an Org to build the wiki index.

  Note: On first indexing, the bge-m3 model
  will be downloaded automatically (~2GB).
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

On failure: Show the error message to the user and provide manual installation commands:
```
Manual installation:
  python3 -m venv ~/.claude/.jarfis-venv
  ~/.claude/.jarfis-venv/bin/pip install sentence-transformers
```
