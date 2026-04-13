# JARFIS Org — Organization List and Info

> **Locale**: All user-facing output must be presented in $LOCALE language. Internal instructions: English.

Display the full list of registered Organizations.

User request: $ARGUMENTS

---

## Execution

0. Auto-discover unregistered Orgs — Scan sibling directories of registered Orgs' parent directories:
```bash
python3 -c "
import sys, os
sys.path.insert(0, os.path.expanduser('~/.claude/scripts'))
from jarfis.organization import discover_unregistered_orgs
discovered = discover_unregistered_orgs()
if discovered:
    for d in discovered:
        print(f'  [AUTO] {d[\"name\"]} discovered → auto-registered ({d[\"root\"]})')
"
```
If any Orgs are discovered, display the results.

1. Read the registered Org list from orgs.json:
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
        print(json.dumps(json.load(f), ensure_ascii=False))
else:
    print(json.dumps({'orgs': []}))
"
```

2. Also check the Org context for the current CWD:
```bash
python3 ~/.claude/scripts/jarfis_cli.py org info $(pwd)
```

3. Combine the results and display:

### When 1 or more Orgs are registered

```
━━━━━━━━━━━━━━━━━━━━━━━━━━
  JARFIS Organizations
━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 Registered Orgs: {count}

  {org_name} ← current (shown only when CWD is inside this Org)
    📂 {root}
    📋 Projects: N
    📚 Wiki: available/none

  {org_name}
    📂 {root}
    📋 Projects: N
    📚 Wiki: available/none

━━━━━━━━━━━━━━━━━━━━━━━━━━
```

For each Org, run `jarfis_cli.py org info {root}` to check the project count and wiki availability.
If CWD is under a specific Org's root, append `← current` to that Org.

### When 0 Orgs are registered

```
━━━━━━━━━━━━━━━━━━━━━━━━━━
  No Organization Registered
━━━━━━━━━━━━━━━━━━━━━━━━━━

No registered Organizations found.

Registering an Organization enables:
  • ADRs, policies, and designs accumulate in the wiki across projects
  • Existing knowledge is automatically injected when starting new workflows
  • View a unified design catalog for the entire service

Register now: /jarfis:org-init
━━━━━━━━━━━━━━━━━━━━━━━━━━
```
