# JARFIS Org Init — Organization Initialization

> **Locale**: All user-facing output must be presented in $LOCALE language. Internal instructions: English.

Initialize a new Organization. Automatically scan sub-projects and create the wiki structure.

User request: $ARGUMENTS

---

## Step 1: Determine Path

AskUserQuestion:
```
question: "Select the Organization root path (the parent directory that contains sub-projects)"
header: "Org Root"
options:
  - label: "Current directory"
    description: "{current CWD absolute path}"
  - label: "Enter path manually"
    description: "Specify a different path"
```

If "Enter path manually" is selected: Use AskUserQuestion to receive the path input (use Other)

Store the selected absolute path in `$ORG_ROOT`.

---

## Step 2: Determine Organization Name

Suggest the directory name of `$ORG_ROOT` as the default.

AskUserQuestion:
```
question: "Choose a name for the Organization"
header: "Org Name"
options:
  - label: "{directory name of $ORG_ROOT}"
    description: "Use the directory name as-is"
  - label: "Enter manually"
    description: "Specify a different name"
```

If "Enter manually" is selected: Use AskUserQuestion to receive the name input (use Other)

Store the result in `$ORG_NAME`.

---

## Step 3: Scan Projects

```bash
python3 ~/.claude/scripts/jarfis_cli.py org init "$ORG_ROOT"
```

Display the `projects` array from the JSON output to the user:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━
  Organization Init: {$ORG_NAME}
━━━━━━━━━━━━━━━━━━━━━━━━━━
📂 Root: {$ORG_ROOT}
🔍 Detected projects:
   - {name} ({type}) — {relative_path}
   - {name} ({type}) — {relative_path}
━━━━━━━━━━━━━━━━━━━━━━━━━━
```

If 0 projects are detected:
```
No sub-projects were detected.
Please run /jarfis:project-init in each project first.
```
Then exit.

---

## Step 4: Confirm and Create

AskUserQuestion:
```
question: "Create Organization '{$ORG_NAME}' with the projects listed above?"
header: "Confirm"
options:
  - label: "Create"
    description: "Generate org-profile.md + wiki structure"
  - label: "Cancel"
    description: "Cancel initialization"
```

If "Create" is selected:
```bash
python3 ~/.claude/scripts/jarfis_cli.py org init "$ORG_ROOT" --confirm --name "$ORG_NAME"
```

Result banner:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━
  Organization Created
━━━━━━━━━━━━━━━━━━━━━━━━━━
📂 {$ORG_ROOT}/.jarfis/org-profile.md
📚 {$ORG_ROOT}/.jarfis/wiki/
   ├── INDEX.md
   ├── PO/_index.md
   ├── DESIGN/_index.md
   ├── TA/_index.md
   └── QA/_index.md

Next steps:
  1. cd {project_path} && /jarfis:project-init
  2. Enable semantic search (optional):
     /jarfis:search-setup → /jarfis:search-index
━━━━━━━━━━━━━━━━━━━━━━━━━━
```
