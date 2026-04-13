# JARFIS Version — Version Management and Updates

> **Locale**: All user-facing output must be presented in $LOCALE language. Internal instructions: English.

Check the currently installed JARFIS version and manage updates.

User request: $ARGUMENTS

---

## Execution Flow

### Step 1: Display Current Version

Read the following files to gather version information:

1. `~/.claude/.jarfis-version` — installed version
2. `~/.claude/.jarfis-source` — Git repo path
3. `~/.claude/commands/jarfis/jarfis-index.md` — Version notation in the index

Display the information:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  JARFIS Version Info
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Installed : v{version}
  Source    : {repo path}
  Index     : {index Version notation}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

If `.jarfis-version` is missing:
```
  [WARN] Version file not found. Please run install.sh.
```

### Step 2: Select Action

Use AskUserQuestion to let the user choose one of the following:

```
question: "What would you like to do?"
header: "Action"
options:
  - label: "Check for updates"
    description: "Check the latest version from Git remote"
  - label: "Run update"
    description: "Update to the latest version (git pull + install.sh)"
  - label: "Install specific version"
    description: "Select and install a specific version from Git tags"
  - label: "View CHANGELOG"
    description: "Display the change history"
```

### Step 3: Handle Each Action

---

#### When [Check for updates] is selected

1. Read the repo path from `.jarfis-source`.
2. Run `git fetch --tags` in that directory.
3. Compare the latest tag with the currently installed version:

```bash
cd {repo_path}
git fetch --tags 2>/dev/null
LATEST=$(git tag -l 'v*' | sort -V | tail -1 | sed 's/^v//')
```

4. Display the result:
```
  Installed : v{current}
  Latest    : v{latest}
  Status    : {Up to date / Update available}
```

If an update is available, use AskUserQuestion to confirm whether to run the update.

---

#### When [Run update] is selected

1. Read the repo path from `.jarfis-source`.
2. Check the repo's git status:

```bash
cd {repo_path}
git status --porcelain
```

3. **If the repo is dirty**: Use AskUserQuestion to let the user choose how to proceed:
```
question: "There are uncommitted changes. How would you like to proceed?"
header: "Dirty repo"
options:
  - label: "Stash & Update"
    description: "Stash changes before updating, then stash pop after completion"
  - label: "Force"
    description: "Discard changes and force update (git checkout .)"
  - label: "Cancel"
    description: "Cancel the update"
```

4. Run the update:
```bash
cd {repo_path}
git pull origin main
bash install.sh --force
```

5. Display the result:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  JARFIS Update Complete
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Previous : v{previous}
  Current  : v{current}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

#### When [Install specific version] is selected

1. Read the repo path from `.jarfis-source`.
2. Fetch the list of available tags:

```bash
cd {repo_path}
git fetch --tags 2>/dev/null
git tag -l 'v*' | sort -rV | head -10
```

3. Use AskUserQuestion to let the user select the version to install (show the 4 most recent tags as options).
4. Install the selected version:

```bash
cd {repo_path}
bash install.sh --version {selected_version} --force
```

---

#### When [View CHANGELOG] is selected

1. Read the repo path from `.jarfis-source`.
2. Read and display `{repo_path}/CHANGELOG.md`.
3. If the file does not exist, inform the user: "CHANGELOG.md not found."

---

## Notes

- If `.jarfis-source` does not exist, the repo path is unknown. Ask the user to enter the path manually or advise them to run `install.sh` first.
- If a Git command fails (e.g., network error), display an appropriate error message and ask whether to continue.
- After an update, inform the user that the previous version's prompts may still be loaded in the current Claude Code session.
