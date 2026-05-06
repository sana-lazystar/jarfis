# JARFIS System Index

> This file is automatically read when `/jarfis:sys-implement` runs and auto-updated after modifications.
> Do not edit manually. Last updated: 2026-05-06 | Version: 4.1.1

## File Structure
```
~/.claude/commands/
├── jarfis.md                      # Main helper — command list + examples (71 lines)
└── jarfis/
    ├── jarfis-index.md            # This file — JARFIS system overview
    ├── agent-composition.yaml     # v4 agent composition spec — persona + skills + context (ADR-17; consumed by `jarfis_cli.py compose`)
    ├── work.md                    # v4 orchestrator — T/0/1a/1b/G1/2∥3/G2/4/4.5/5/G3/6 flow, tmux-per-phase, single-writer state rule (255 lines)
    ├── work-meeting.md            # Planning kickoff meeting — PO/TL open discussion → artifact generation, mid-save compact resilience (256 lines)
    ├── sys-implement.md           # JARFIS self-modification + Dialectic Review ratchet convergence + Python TDD rules (294 lines)
    ├── sys-upgrade.md             # Learning item management + 3-block independent structure + Dialectic Review + agent whitelist protection (298 lines)
    ├── sys-distill.md             # Prompt distillation + agent whitelist protection + Dialectic Review — command analysis only (314 lines)
    ├── sys-version.md             # Version management/updates (160 lines)
    ├── sys-health.md              # Zombie Claude process diagnosis/cleanup (72 lines)
    ├── project-init.md            # Project profile creation (180 lines)
    ├── project-update.md          # Incremental profile update — commit hash-based change detection (175 lines)
    ├── org.md                     # Full organization list — orgs.json + unregistered Org auto-discovery + CWD highlight (98 lines)
    ├── org-init.md                # Organization initialization — scan + wiki creation + semantic index guide (115 lines)
    ├── wiki-storyboard.md         # Design catalog browsing command (50 lines)
    ├── search.md                  # Semantic unified search — meetings/works/wiki filtering + low-memory LLM fallback (92 lines)
    ├── search-setup.md            # Semantic search installation — venv + sentence-transformers one-step (59 lines)
    ├── search-index.md            # Full Org semantic index batch creation/refresh — wiki+meetings+works + memory guard (126 lines)
    ├── level-check.md             # AI-native developer maturity assessment — 7-dimension 10-point + level_check.py auto-collection + interview (244 lines)
    ├── locale.md                  # Locale query — display current workflow language (46 lines)
    ├── locale-set.md              # Locale setting — change language to ko/en/ja (54 lines)
    ├── prompts/                   # Externalized phase prompts — loaded by jarfis-foreman inside the phase's tmux session
    │   ├── phase1b.md             # Phase 1b Discovery Processing — PO + TA artifacts (tmux; Phase 1a runs in main as PO dialogue) (184 lines)
    │   ├── phase2.md              # Phase 2 Architecture & Planning — runs in parallel with phase3 under separate tmux sessions (173 lines)
    │   ├── phase3.md              # Phase 3 Design (figma + text unified) — parallel multi-page processing, per-section v5 generation (546 lines)
    │   ├── phase4.md              # Phase 4 Implementation — parallel BE/FE/DevOps + security pre-review + TDD Step 4-0.5 + TDD Ratchet (conditional on $TDD_ENABLED) (320 lines)
    │   ├── phase4-5.md            # Phase 4.5 Operational Readiness — DevOps-owned, `phase_id = "4-5"` (117 lines)
    │   ├── phase5.md              # Phase 5 Review & QA — review_round loop + pattern-detect + Phase 4 Agent Status injection + Learning Candidate Detection (628 lines)
    │   ├── phase6.md              # Phase 6 Retrospective + Wiki 2-track Sync + Workflow Metrics + semantic index refresh (416 lines)
    │   └── wiki-loading.md        # Wiki loading shared module — 4-step protocol + semantic search fallback (47 lines)
    ├── domains/                   # v3.0 Domain Pack infrastructure (metadata only in v4 — skills relocated to ../skills/)
    │   ├── _schema.yaml           # Domain Pack specification (Published Language, EP1-7)
    │   ├── web.yaml               # Web Development domain pack — base personas only (M2 ADR-0001)
    │   ├── desktop.yaml           # Desktop (Tauri) domain pack — design+ux-designer, review+qa+security (M3 ADR-0003)
    │   └── mobile.yaml            # Mobile (React Native) domain pack — α release scope, rn_engineer role (M4 ADR-0004)
    ├── skills/                    # Flat Skills catalog (v4 — relocated from domains/{web,desktop}/skills/; 17 skills, +react-native M5; +context7 hint blocks v4.1.1)
    │   ├── aws-lambda.md · biome-lint.md · browser.md · cargo-clippy.md
    │   ├── cognito.md · dynamodb.md · express.md · nodejs.md
    │   ├── postgres.md · react.md · react-native.md · redis.md · rust.md
    │   └── s3.md · tauri-backend.md · tauri-webview.md · vue.md
    ├── rules/                     # Cross-cutting rules referenced by personas/prompts (v4.1.1+)
    │   └── context7-research.md   # B15 — Context7 MCP proactive research procedure (3-tier disambig, cost guard, skill priority, telemetry)
    └── templates/                 # Externalized artifact templates (generated by distill; loaded on-demand per phase)
        ├── jarfis-state-schema.md # .jarfis-state.json v4 schema — scope[] + org{} + baseCommit + sessionKey + phases.{N}.status + phase-results/
        ├── learnings.md           # jarfis-learnings.md template — Universal/Project-Specific structure
        ├── project-context.md     # project-context.md template
        ├── project-profile.md     # Project profile template + org back-reference
        ├── meeting-artifacts.md   # Meeting artifact 4-type templates (summary/notes/decisions/tech-research)
        ├── org-profile.md         # Organization profile template
        ├── wiki-index.md          # Wiki INDEX.md initial template
        ├── wiki-section-index.md  # Wiki section _index.md template
        ├── ux-direction.md        # UX direction document template
        ├── design-html-meta.md    # HTML mockup meta comment template
        └── skill-template.md      # Skill file template (v4 new — checkpoint style used by sys-distill for skill creation)

~/.claude/agents/jarfis/           # JARFIS agent prompts (v4 — 4 agents + 9 personas, ALL ENGLISH + $LOCALE output)
├── jarfis-foreman.md              # v4 per-phase tmux executor — loads phase prompt, spawns sub-agents via Task + compose CLI, merges outputs (executor only, no autonomous judgment)
├── jarfis-engineer.md             # v4 migration domain expert — loads v3→v4 decisions, safety principles, milestone-aware context (persona loaded by main Claude at session start)
├── jarfis-advocate.md             # Dialectic Review — change advocate (scope: sys-implement/sys-upgrade/sys-distill only, per ADR-13 + F-14)
├── jarfis-critic.md               # Dialectic Review — change critic (scope: sys-* only, per ADR-13 + F-14)
└── personas/                      # v4 role-specific cognitive frameworks (composed dynamically via agent-composition.yaml). M1 (v4.1-m1) absorbed v3 senior-* domain knowledge per ADR-0001 — lines below reflect post-absorption state (1,055 lines total, 69.7% of v3 senior-* 1,512 lines).
    ├── product-owner.md           # PO perspective (107 lines) — business value, JTBD, Working Backwards, Empathy Map, RICE/MoSCoW, Last Responsible Moment, escalation gates
    ├── technical-architect.md     # Architect perspective (130 lines) — system design, NFR quantification, ADR writing, Pattern Selection, Data Architecture, Phase 1~4 process
    ├── tech-lead.md               # TL perspective (114 lines) — code review, refactoring triggers, 5-stage tech debt, Feedback Ladder, "Good Enough" 5 questions, ADR
    ├── frontend-developer.md      # FE perspective (109 lines) — Classic Web/Modern Frameworks/Cross-Browser/Performance Infra + Learned Rules (12~15 항목, 5 카테고리 균형)
    ├── backend-developer.md       # BE perspective (92 lines) — Languages/Frameworks/Databases/Server Types/Troubleshooting + production-ready judgment
    ├── devops-engineer.md         # DevOps perspective (73 lines) — CI/CD, containers, IaC, Reliability/Observability/FinOps, behavioral guidelines
    ├── qa-engineer.md             # QA perspective (122 lines) — test design, risk assessment, compatibility, Quality Advocate mindset, escalation
    ├── security-engineer.md       # Security perspective (133 lines) — threat modeling mindset, Detection Patterns, Quality Gate, escalation (도구별 STRIDE/SAST/DAST 는 별도 skill 후보)
    └── ux-designer.md             # UX perspective (175 lines) — user empathy, Constraint-First, Nielsen Checkpoints, Trade-off Matrix, WCAG 2.2 AA, Critique Loop, Learned Rules (reference.png + Figma)
```

## Command Mapping
| Command | File | Role |
|---------|------|------|
| `/jarfis` | `jarfis.md` | Display command list |
| `/jarfis:work-meeting` | `jarfis/work-meeting.md` | Planning kickoff meeting (PO/TL open discussion → artifact generation) |
| `/jarfis:work` | `jarfis/work.md` | v4 full workflow: triage → pre-flight → discovery → plan → design → implement → ops-readiness → review → retro |
| `/jarfis:project-init` | `jarfis/project-init.md` | Project analysis → generate `./.jarfis-project/project-profile.md` |
| `/jarfis:project-update` | `jarfis/project-update.md` | Incremental profile update (commit hash-based, date fallback) |
| `/jarfis:sys-implement` | `jarfis/sys-implement.md` | JARFIS system self-modification/feature addition + version bump (Dialectic Review scope) |
| `/jarfis:sys-upgrade` | `jarfis/sys-upgrade.md` | Learning item CRUD + apply to agent/workflow prompts (Dialectic Review scope) |
| `/jarfis:sys-distill` | `jarfis/sys-distill.md` | Prompt distillation — token efficiency analysis/optimization (Dialectic Review scope) |
| `/jarfis:sys-version` | `jarfis/sys-version.md` | Version check/update/install specific version |
| `/jarfis:sys-health` | `jarfis/sys-health.md` | Zombie Claude process diagnosis/cleanup (tmux-per-phase operational cost mitigation) |
| `/jarfis:org` | `jarfis/org.md` | Full registered Org list (orgs.json based, CWD highlight) |
| `/jarfis:org-init` | `jarfis/org-init.md` | Organization initialization (scan + wiki creation) |
| `/jarfis:wiki-storyboard` | `jarfis/wiki-storyboard.md` | Design catalog browsing (wiki/DESIGN → browser) |
| `/jarfis:search` | `jarfis/search.md` | Semantic unified search (meetings+works+wiki, filterable) |
| `/jarfis:search-setup` | `jarfis/search-setup.md` | Semantic search installation (venv + sentence-transformers one-step) |
| `/jarfis:search-index` | `jarfis/search-index.md` | Full Org semantic index batch creation/refresh (wiki+meetings+works) |
| `/jarfis:level-check` | `jarfis/level-check.md` | AI-native developer maturity assessment (auto-collection + interview, 7-dimension 10-point) |
| `/jarfis:locale` | `jarfis/locale.md` | View current locale setting |
| `/jarfis:locale-set` | `jarfis/locale-set.md` | Change locale setting (ko/en/ja) |

## Artifacts / Data Files
- `{project_path}/.jarfis-project/project-rule.md` — User-defined project rules (created by project-init, never AI-modified. Highest priority context)
- `{project_path}/.jarfis-project/project-profile.md` — Generated by project-init, referenced by work (inside each project)
- `{project_path}/.jarfis-project/project-context.md` — Context referenced during work execution (inside each project, optional)
- `$JARFIS_ORG_DIR/learnings.md` — Per-Org learning items (managed by upgrade, applied via sys-upgrade only — NOT loaded at runtime)
- `~/.claude/.jarfis-personal-dir` — .personal directory path configuration file (created by install.sh)
- `$JARFIS_ORG_DIR/works/{YYYYMMDD}-{type}-{ticket-name}/` — Workflow artifact directory created by work (`$DOCS_DIR`; v4 standardized subdirs: `discovery/`, `planning/`, `design/`, `review/`, `ops/`, `phase-results/phase{N}/attempt{K}.json`)
- `$JARFIS_ORG_DIR/meetings/{YYYYMMDD}-{plan-name}/` — Meeting artifact directory created by meeting (flat structure):
  - `summary.md` — YAML frontmatter + meeting summary (for work.md auto-detection)
  - `meeting-notes.md` — Meeting notes organized by topic
  - `decisions.md` — Decision table + rationale + alternatives
  - `tech-research.md` — Expert research results (generated only when expert is summoned)
- `~/.claude/scripts/jarfis_cli.py` — Python CLI dispatcher (single interface for all commands below; auto re-execs in `~/.claude/.jarfis-venv` for `wiki`/`search`)
  - `jarfis_cli.py state` — .jarfis-state.json CRUD (init/read/write/set/set-nested/validate/list-workflows). **Single-writer rule (ADR-18)**: only the main session writes state; tmux sub-agents write to `phase-results/phase{N}/attempt{K}.json` + phase output dirs.
  - `jarfis_cli.py gate-check` — Gate 1/2/3 prerequisite validation (v4 top-level, mandatory before any Gate presentation)
  - `jarfis_cli.py phase-check` — Phase-start prerequisite validation (Gate approval + prior Phase complete)
  - `jarfis_cli.py phase-verify` — Per-phase output verification (consumed by tmux foreman)
  - `jarfis_cli.py pattern-detect` — Review round pattern detection (Phase 5 review_round loop)
  - `jarfis_cli.py compose` — Compose agent invocation — persona + skills + context (v4 M2; 4-stage skill fallback chain, reads `agent-composition.yaml`)
  - `jarfis_cli.py detect` — Framework/language auto-detection (file pattern-based JSON output)
  - `jarfis_cli.py measure` — Prompt file token measurement + structural diagnosis (used in sys-distill D-0/D-1/D-4)
  - `jarfis_cli.py preflight` — Pre-validation + project-rule check + Org auto-registration + project table auto-addition
  - `jarfis_cli.py meetings` — Output recent N meetings as JSON (used in work.md Phase 0 meeting selection)
  - `jarfis_cli.py version` — Semver version bump automation (used by sys-implement/sys-distill/sys-upgrade)
  - `jarfis_cli.py sync` — Repo sync (`~/.claude/` → `{repo_path}/` auto diff+copy + README update + tests/ sync)
  - `jarfis_cli.py quality-gate` — Per-file lint/type-check execution (used by PostToolUse hook)
  - `jarfis_cli.py validate` — Workflow state + artifact + Git validation (manual tool)
  - `jarfis_cli.py org` — Organization management (init --name/scan/info — unregistered returns exit 0 + registered:false)
  - `jarfis_cli.py search` — Semantic search (search {all|meetings|works|wiki}, index, status; CWD-based Org resolution)
  - `jarfis_cli.py wiki` — Wiki semantic search (deprecated → search wiki; backward compatibility)
  - `jarfis_cli.py domain` — Domain Pack management (list/detect/agents/compose/validate/scaffold/install)
- `~/.claude/scripts/jarfis/` — Python module directory (referenced by `jarfis_cli.py`)
  - `state.py` — .jarfis-state.json CRUD (v4 schema: work{} + org + sessionKey + phases.{N}.status; v3 flat-key dual emit removed in v4.1 per ADR-0002 — backward-compat read still accepted)
  - `verify.py` — Unified gate/phase/pattern verification (`gate-check` + `phase-check` + `phase-verify` + `pattern-detect`). v4 replacement for v3 `jarfis-black` LLM gate — deterministic Python, ~10ms, machine-verifiable (ADR-15; 1,349 lines)
  - `verify_helpers.py` — Shared helpers for verify.py entrypoints
  - `tmux_claude.py` — tmux-per-phase orchestration (B1 isolation: exact-match session name only; `--save-pane` post-mortem debugging; v4.0.4)
  - `trace.py` — Performance tracing module — opt-in via `JARFIS_TRACE` env var; `trace.log_event` API → `/tmp/jarfis-trace.jsonl` (or `$JARFIS_TRACE_PATH`); ~0.008% overhead when enabled, zero cost when off (ADR-20; v4.0.5)
  - `compose/` — Compose CLI package (`__main__.py` + `assembler.py` + `config.py` + `context7_research.py` + `models.py` + `reader.py` + `resolver.py` + `skills.py` + `skills_lib.py` + `validate.py`) — deterministic agent composition with 4-stage skill fallback, N-3 section-missing audit; `context7_research.py` (v4.1.1 B15) carries Tier-1 hint parsing + Tier-2/3 disambiguation + ResearchSession (cost guard + cache + telemetry)
  - `domain.py` — Domain Pack management module (list/detect/agents/compose/validate/scaffold/install)
  - `audit.py` — Audit log module (append-only JSONL)
  - `detect.py` — Framework/language auto-detection
  - `level_check.py` — AI-native maturity auto-collection (filesystem survey + jsonl session parsing, orchestration detection)
  - `measure.py` — Prompt token measurement + structural diagnosis
  - `meetings.py` — Recent meetings list
  - `organization.py` — Organization management module (init/scan/info)
  - `preflight.py` — Pre-flight validation module
  - `quality_gate.py` — Quality Gate module (biome/prettier detection, per-extension checks)
  - `sync.py` — Repo sync (.claude → repo, diff+copy + README update)
  - `utils.py` — Shared helpers
  - `validate.py` — Workflow validation module (state + artifact + wiki structure + Git status)
  - `version.py` — Semver version bump (VERSION + __init__.py + CHANGELOG)
  - `wiki_search.py` — Semantic search (sentence-transformers bge-m3, wiki/meetings/works indexing+search + memory guard + CPU forced + MPS memory deduction, 950 lines)
- `~/.claude/scripts/tests/` — pytest test directory (25 test modules covering all jarfis/ modules; run via `python3 -m pytest ~/.claude/scripts/tests/ -v --tb=short`)
  - `conftest.py` — Shared fixtures (jarfis_env, state_file, project_dir — tmpdir-based isolation)
  - `test_architecture.py` — Architecture invariants (domain boundaries, import hygiene)
  - `test_state.py` · `test_verify.py`-family (`test_gate_check.py`, `test_phase_verify.py`) · `test_tmux_claude.py` · `test_trace.py` · `test_compose_warnings.py`
  - `test_detect.py` · `test_domain.py` · `test_audit.py` · `test_measure.py` · `test_meetings.py`
  - `test_preflight.py` · `test_quality_gate.py` · `test_organization.py` · `test_validate.py`
  - `test_sync.py` · `test_utils.py` · `test_version.py` · `test_wiki_search.py` · `test_level_check.py` · `test_jarfis_cli.py`
- `~/.claude/scripts/jarfis_check.sh` — grep-based JARFIS structural validation script (Phase headings, prompt files, version matching, model consistency)
- `~/.claude/hooks/` — 4 hooks (all kill-switchable via env var)
  - `jarfis-pre-compact.sh` — PreCompact hook: backs up `.jarfis-state.json` + meeting files from `$JARFIS_ORG_DIR` before auto-compact (shell-only)
  - `jarfis-safety.sh` — PreToolUse(Bash) blocking: force push, --no-verify, direct commit to main/master | warning: .env, rm -rf, credentials, curl|bash (kill switch: `JARFIS_SAFETY_HOOK=0`)
  - `jarfis-quality-gate.sh` — PostToolUse(Edit/Write/MultiEdit) lint/type-check warning (never blocks; kill switch: `JARFIS_QUALITY_GATE=0`)
  - `jarfis-session-start.sh` — SessionStart hook: discovers in-progress workflows → injects context via stdout (kill switch: `JARFIS_SESSION_RESTORE=0`)
- `$DOCS_DIR/.compact-backups/` — State backup directory created by PreCompact hook
- `$DOCS_DIR/phase-results/phase{N}/attempt{K}.json` — tmux sub-agent per-attempt meta (single-writer rule: tmux writes here, main reads and selectively reflects into state)
- `~/.claude/.jarfis-version` — Installed version record (created by install.sh)
- `~/.claude/.jarfis-source` — Git repo path record (created by install.sh)
- `~/.claude/.jarfis-personal-dir` — .personal directory path (default: `{JARFIS_SOURCE}/.personal`)
- `~/.claude/.jarfis-locale` — Global locale setting (ko/en/ja); state.locale mirrors this
- `~/.claude/.jarfis-venv/` — sentence-transformers venv (used by `wiki`/`search` commands via jarfis_cli.py auto re-exec)
- `{JARFIS_SOURCE}/.personal/orgs/orgs.json` — Org registry (auto-registered during org-init)
- `{JARFIS_SOURCE}/.personal/orgs/{org_name}/` — Per-Org workspace (works/, meetings/, learnings.md)
- `{JARFIS_SOURCE}/.personal/orgs/_standalone/` — Workspace for unregistered Org users
- `$JARFIS_ORG_DIR/workflow-metrics.tsv` — Workflow metrics cumulative record (AutoResearch results.tsv pattern, appended at Phase 6 Step 6-2.5)
- `{JARFIS_SOURCE}/VERSION` — Git repo semver version (currently 4.0.6)
- `{JARFIS_SOURCE}/CHANGELOG.md` — Keep-a-Changelog format change history

## Internal Reference Map
- `jarfis.md` → references all commands (helper text)
- `work-meeting.md` → independent (optionally references project-profile, context, learnings) + mid-save for compact resilience
- `work.md` → v4 orchestrator. References `/jarfis:project-init` (profile load guide) + meeting artifacts (Phase 0 queries `jarfis_cli.py meetings` + AskUserQuestion selection + dynamic scan of selected meeting dir) + `.compact-backups/` reference (on Resume) + `prompts/*.md` (per-Phase executor prompts, loaded by jarfis-foreman in each phase's tmux session) + `agent-composition.yaml` (via `jarfis_cli.py compose`). v3 state detected → halt + advise user; **no silent migration** (per F-08).
- `prompts/*.md` → agent prompts externalized from work.md; loaded by **jarfis-foreman** inside each phase's dedicated tmux session (`{sessionKey}-phase{N}`).
- `prompts/phase3.md` → unified figma + text design path (parallel multi-Figma page processing, per-section v5 generation, Framelink MCP + asset download + token-map + UX Designer reproduction + PO/UX review loop).
- `templates/*.md` → artifact templates externalized from work.md/work-meeting.md (generated by distill, loaded when needed in corresponding Phase).
- `project-update.md` → references `/jarfis:project-init` (guide when no profile exists, analysis criteria reference).
- `project-init.md` → references `templates/project-profile.md` (profile artifact format).
- `sys-distill.md` → reads `jarfis-index.md` first → measures tokens via `jarfis_cli.py measure` → analyzes commands/jarfis/*.md + agents/jarfis/*.md, updates this index.
- `~/.claude/agents/jarfis/personas/*.md` → composed dynamically by `jarfis_cli.py compose` (reads `agent-composition.yaml` + base project-profile + project-rule + wiki-cache + domain skills fallback chain). Main work path; Dialectic agents are sys-* only.
- `~/.claude/agents/jarfis/jarfis-foreman.md` → loaded by `Task` tool inside each phase's tmux session; runs phase prompt + spawns sub-agents via Task + compose CLI + merges outputs.
- `~/.claude/agents/jarfis/jarfis-engineer.md` → v4 migration domain expert; loaded as a persona by the main Claude at session start for v4 migration context.
- `~/.claude/agents/jarfis/jarfis-advocate.md` / `jarfis-critic.md` → Dialectic Review; referenced **only** in sys-implement/sys-upgrade/sys-distill (per ADR-13 + F-14). No participation in phase*.md workflow prompts.
- `sys-implement.md` → reads/updates `jarfis-index.md` + bumps VERSION/CHANGELOG via `jarfis_cli.py version`.
- `sys-version.md` → references `.jarfis-version`, `.jarfis-source`, Git repo VERSION/CHANGELOG.
- `sys-distill.md` → calls `jarfis_cli.py version patch` on completion.
- `sys-upgrade.md` → calls `jarfis_cli.py version patch` after learning application.
- `sys-implement.md` → calls `jarfis_cli.py version <type>` on completion (user-selected).
- `jarfis_cli.py measure` → used in sys-distill.md D-0/D-1/D-4 for file token measurement + diagnostic data collection.
- `jarfis_cli.py version` → used in sys-implement/sys-distill/sys-upgrade for auto-updating VERSION/CHANGELOG/__init__.py.
- `jarfis_cli.py sync` → includes README update (jarfis-index.md + CHANGELOG.md → README.md section update).
- `jarfis_cli.py meetings` → used in work.md Phase 0 to query recent N meetings as JSON.
- `jarfis_cli.py preflight` → used in work.md Phase 0 / work-meeting.md M-0 for profile/rule/context/git status pre-validation.
- `jarfis_cli.py state` → used across work.md all phases for .jarfis-state.json CRUD (main session only — single-writer rule).
- `jarfis_cli.py gate-check` / `phase-check` / `phase-verify` / `pattern-detect` → v4 top-level verify entrypoints; referenced by work.md Gate Point Rules (gate-check mandatory before any Gate presentation) and by jarfis-foreman for phase-level verification.
- `jarfis_cli.py compose` → used by jarfis-foreman to spawn sub-agents with composed persona + skills + project-profile sections (ADR-17 deterministic composition).
- `jarfis_cli.py detect` → used in project-init.md Step 0 / work.md Phase 0 for framework/language auto-detection.
- `jarfis-pre-compact.sh` → backs up `.jarfis-state.json` + meeting files from `$JARFIS_ORG_DIR` (auto-executed on auto-compact).
- `jarfis-safety.sh` → PreToolUse(Bash) blocking/warning (kill switch: `JARFIS_SAFETY_HOOK=0`).
- `jarfis-quality-gate.sh` → PostToolUse(Edit/Write/MultiEdit) lint/type-check warning (never blocks; kill switch: `JARFIS_QUALITY_GATE=0`).
- `jarfis-session-start.sh` → discovers in-progress workflows at SessionStart → injects context via stdout (kill switch: `JARFIS_SESSION_RESTORE=0`).
- `quality_gate.py` → called by jarfis-quality-gate.sh; runs biome/prettier + tsc (auto-detects project root).
- `phase4.md` → Phase 2 handoff read/write instructions (key_decisions, warnings, unresolved) + Artifact Loading Checklist (required/conditional file distinction) + TDD Step 4-0.5 (QA test-first authoring) + BE/FE TDD Green Phase blocks (TDD Ratchet conditional on `$TDD_ENABLED == 'true'`).
- `phase5.md` → Phase 4 Agent Status injection (phase4_agents status forwarding) + Fix agent original design reference (architecture.md, tasks.md) + Learning Candidate Detection (records learning_candidates when same fix category repeats 2+ times) + pattern-detect for review round convergence.
- `phase6.md` → Suggested Learnings section (auto-generates learning candidates based on learning_candidates) + Wiki re-indexing via `jarfis_cli.py search index wiki` after wiki update (best-effort) + appends `workflow-metrics.tsv`.
- `wiki-loading.md` → calls `jarfis_cli.py search wiki` in 4-Step Step 3 (fallback: LLM judgment).
- `wiki_search.py` → referenced by wiki-loading.md/phase6.md/org-init.md/work.md/work-meeting.md/search.md. Supports both `jarfis_cli.py search` (new) and `jarfis_cli.py wiki` (deprecated).
- `search.md` → calls `jarfis_cli.py search {scope} "query" --pretty` (direct user search).
- `search-setup.md` → standalone execution (venv creation + sentence-transformers installation); guides to `/jarfis:search-index` on completion.
- `search-index.md` → selects Org from orgs.json → runs `jarfis_cli.py search index {scope}` (wiki+meetings+works). `--current` flag for current Org only.
- `work-meeting.md` M-3 → auto-calls `jarfis_cli.py search index meetings` (best-effort).
- `phase6.md` → auto-calls `jarfis_cli.py search index wiki` + `search index works` (best-effort).
- `org-init.md` → displays `/jarfis:search-setup` → `/jarfis:search-index` guide on completion.
- `verify.py` → referenced by work.md Gate Point Rules (mandatory `gate-check` before any Gate presentation); also provides `phase-check` (Phase start) and `phase-verify` / `pattern-detect` (tmux foreman).
- `tmux_claude.py` → used by jarfis-foreman to create/reattach/tear down phase-specific tmux sessions (`{sessionKey}-phase{N}`); enforces B1 exact-match isolation; `--save-pane` option for post-mortem debug.
- `trace.py` → opt-in via `JARFIS_TRACE=1`; `trace.log_event(event, attrs)` called from hot paths in tmux_claude / verify / compose; output JSONL at `/tmp/jarfis-trace.jsonl` (or `$JARFIS_TRACE_PATH`).
- `agent-composition.yaml` → consumed by `jarfis_cli.py compose`; defines per-agent persona + scope + skills_from_domain + context (base: project | all-projects | docs | org | org_wiki).
- `tests/` → referenced in sys-implement.md Step 2 Python TDD rules (25 test modules covering all Python scripts). Run via `python3 -m pytest ~/.claude/scripts/tests/ -v --tb=short`.

## Git Auto-Commit Feature
- Phase 4 (Implementation): BE/FE/DevOps agents auto-commit on each task completion
  - Format: `jarfis(BE-N):`, `jarfis(FE-N):`, `jarfis(DevOps-N):`
- Phase 5 Step 5-3 (Fixes): Auto-commit per issue group
  - Format: `jarfis(fix/BE):`, `jarfis(fix/FE):`
- 3-second wait with retry on git index.lock conflict (up to 3 attempts)
- Phase 4.5 (Operational Readiness): DevOps-only commits use `jarfis(DevOps-N):` under `phase_id = "4-5"`

## Modification Checklist
- Command name change: rename file + grep/replace references across all files
- New command addition: create md file under `jarfis/` + add to `jarfis.md` list + update this index
- `work.md` is the v4 orchestrator (255 lines — drastically reduced from the v3 909-line monolith via externalization to `prompts/`)
- **Externalization structure** (distill v10+):
  - work.md contains only workflow flow/rules
  - Agent Task prompt → edit `prompts/phase{N}.md`
  - Artifact templates → edit `templates/*.md`
  - Adding/removing a Phase → update work.md + corresponding prompts/ + templates/ simultaneously
  - `~/.claude/agents/jarfis/*.md` are Agent tool role prompts (separate from work.md)
- **Agent composition (v4)**: modifications to `agent-composition.yaml` require validation via `jarfis_cli.py compose --validate` (checks base/path resolvability + section existence; stderr warning on missing sections recorded in meta.context_files).
- **State write rule (v4 ADR-18)**: only the main session writes `.jarfis-state.json`; tmux sub-agents write to `phase-results/phase{N}/attempt{K}.json` + phase output dirs. Violating this breaks the single-writer invariant.
- **Version management**: after sys-implement/sys-distill/sys-upgrade completion → update VERSION + .jarfis-version + __init__.py + this index (`Version:` header) + CHANGELOG.
- **Repo sync**: after sys-implement/sys-distill/sys-upgrade completion → run `python3 ~/.claude/scripts/jarfis_cli.py sync` (manual copy prohibited).
- **Python TDD**: when modifying `scripts/jarfis/*.py` → write/update tests first in `scripts/tests/` → modify code → verify all pass via `python3 -m pytest ~/.claude/scripts/tests/ -v --tb=short`.
- **Git repo**: check path in `~/.claude/.jarfis-source` (default: `~/repos/jarfis`).
- **Dialectic Review scope (ADR-13 + F-14)**: Advocate/Critic agents apply **only** to sys-implement/sys-upgrade/sys-distill. Workflow phases (phase*.md) rely on P7 Deterministic Foundation + TDD Ratchet (conditional), not Dialectic.
- **v3 state detection**: `.jarfis-state.json` with `project_name` (no `sessionKey`) → v4 work.md halts with guidance message in `$LOCALE`. Never silently migrate (F-08 + MIGRATION.md §3).
- **v3 fallback removal (v4.1, ADR-0002)**: legacy `work-legacy.md` and the `state.py:cmd_init` v3 flat-key dual emit were removed in M2; emergency rollback now relies solely on git tag `v4.0.7` + `rollback.sh`.
