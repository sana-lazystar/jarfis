# JARFIS — Available Commands Help

> **Locale**: All user-facing output must be presented in $LOCALE language. Internal instructions: English.

JARFIS command helper. Display the following list of available commands to the user.

---

Display the following as-is:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  JARFIS - IT Team Workflow Orchestration
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Available commands:

  /jarfis:org
    View Organization info (registration guidance if not set up)
  /jarfis:org-init
    Create a new Organization (project scan + wiki structure)
    Wiki knowledge accumulates → ADRs, policies, designs auto-shared across projects
  /jarfis:project-init [--depth basic|medium|deep]
    Generate project profile (one-time, per project)
  /jarfis:project-update
    Incremental profile refresh (Git history based, run anytime)
  /jarfis:work-meeting [topic]
    PO+TL planning kickoff meeting (idea exploration, selection)
  /jarfis:work [description]
    Run full workflow (plan → design → implement → review → retrospective)
  /jarfis:wiki-storyboard                          [Org]
    Browse the service-wide design catalog

  /jarfis:search [--meetings] [--works] [--wiki] query  [Org]
    Unified semantic search (meetings + works + wiki)
  /jarfis:search-setup                              [Org]
    Enable semantic search (install sentence-transformers)
  /jarfis:search-index [--current]                  [Org]
    Batch-create/refresh semantic indexes for all Orgs (wiki + meetings + works)

  /jarfis:locale          View current locale setting
  /jarfis:locale-set      Set locale (ko/en/ja)

  /jarfis:level-check     AI-native developer maturity assessment
  /jarfis:sys-upgrade     Manage learning items + apply to agents
  /jarfis:sys-distill     Token efficiency analysis + optimization
  /jarfis:sys-implement   Modify the JARFIS system itself
  /jarfis:sys-version     Check version + update
  /jarfis:sys-health      Diagnose/clean up zombie processes
  /jarfis:agent           Manage skills + inspect personas (skill list/add/update/remove, persona list)

  [Org] = Organization registration required
    With Org registration, wiki knowledge is auto-injected into work/work-meeting,
    and Phase 6 retrospective outputs automatically accumulate in the wiki.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Example A — With Organization (recommended):
    cd ~/your-company-name
    /jarfis:org-init                      ← Register Org (one-time)
    cd ~/your-company-name/my-project
    /jarfis:project-init                  ← One-time per project
    /jarfis:work-meeting payment system renewal
    /jarfis:work payment system renewal
    /jarfis:wiki-storyboard              ← View design catalog
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Example B — Quick start without Org:
    cd ~/my-project
    /jarfis:project-init
    /jarfis:work bulletin board CRUD + comments
    /jarfis:work add comment notifications
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
