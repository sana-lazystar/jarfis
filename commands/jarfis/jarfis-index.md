# JARFIS System Index

> This file is automatically read when `/jarfis:sys-implement` runs and auto-updated after modifications.
> Do not edit manually. Last updated: 2026-05-07 | Version: 4.6.0

## File Structure
```
~/.claude/commands/
├── jarfis.md                      # Main helper — command list + examples (71 lines)
└── jarfis/
    ├── jarfis-index.md            # This file — JARFIS system overview
    ├── agent.md                       # Agent skill+persona registry CRUD (skill list/add/update/remove, persona list); Context7-aware skill_add; diff-only composition.yaml safety (172 lines)
    ├── agent-composition.yaml     # v4 agent composition spec — persona + skills + context (ADR-17; consumed by `jarfis_cli.py compose`)
    ├── work.md                    # v4 orchestrator — T/0/1a/1b/G1/2∥3/G2/4/4.5/5/G3/6 flow, tmux-per-phase, single-writer state rule (255 lines)
    ├── work-meeting.md            # Planning kickoff meeting — PO/TL open discussion → artifact generation, mid-save compact resilience (256 lines)
    ├── sys-implement.md           # JARFIS self-modification + workspace ({JARFIS_SOURCE}/.personal/sys-implements/{plan-name}/, ADR-0003) + Force-Acknowledge Dialectic (ADR-0005) + execution mode dispatch (ADR-0004) + RAG auto-update (ADR-0002 §2.4) + Python TDD rules (555 lines)
    ├── sys-upgrade.md             # Learning item management + 3-block independent structure + Dialectic Review + agent whitelist protection (298 lines)
    ├── sys-distill.md             # Prompt distillation + agent whitelist protection + Dialectic Review — command analysis only (314 lines)
    ├── sys-version.md             # Version management/updates (160 lines)
    ├── sys-health.md              # Zombie Claude process diagnosis/cleanup (72 lines)
    ├── project-init.md            # Project profile creation + Step 4.0 monorepo detection (v4.3.0; 202 lines)
    ├── project-update.md          # Incremental profile update — commit hash-based change detection (175 lines)
    ├── org.md                     # Full organization list — orgs.json + unregistered Org auto-discovery + CWD highlight (98 lines)
    ├── org-init.md                # Organization initialization — scan + wiki creation + semantic index guide (115 lines)
    ├── wiki-storyboard.md         # Design catalog browsing command (50 lines)
    ├── search.md                  # Semantic unified search — meetings/works/wiki/jarfis filtering + low-memory LLM fallback (94 lines; +jarfis scope v4.2.0)
    ├── search-setup.md            # Semantic search installation — venv + sentence-transformers one-step (59 lines)
    ├── search-index.md            # Full Org semantic index batch creation/refresh — wiki+meetings+works+jarfis + incremental + memory guard (137 lines; +jarfis scope v4.2.0)
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
    ├── skills/                    # Flat Skills catalog (v4 — relocated from domains/{web,desktop}/skills/; 18 skills; +react-native M5; +context7 hint blocks v4.1.1; +cloudflare v4.2.0)
    │   ├── aws-lambda.md · biome-lint.md · browser.md · cargo-clippy.md
    │   ├── cloudflare.md · cognito.md · dynamodb.md · express.md
    │   ├── nodejs.md · postgres.md · react.md · react-native.md
    │   ├── redis.md · rust.md · s3.md · tauri-backend.md
    │   └── tauri-webview.md · vue.md
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
        ├── ia-schema.md           # ia.json schema for supplied design mode (Information Architecture; SSOT 자동생성 금지) — v4.6.0
        ├── skill-template.md      # Skill file template (v4 new — checkpoint style used by sys-distill for skill creation)
        └── sitemap.md             # Sitemap markdown template for supplied design mode (SSOT 자동생성 금지) — v4.6.0

~/.claude/agents/jarfis/           # JARFIS agent prompts (v4 — 4 agents + 9 personas, ALL ENGLISH + $LOCALE output)
├── jarfis-foreman.md              # v4 per-phase tmux executor — loads phase prompt, spawns sub-agents via Task + compose CLI, merges outputs (executor only, no autonomous judgment)
├── jarfis-engineer.md             # Hybrid Persona + Spawnable engineer (v4.2.0 ADR-0001) — Mode A: persona loaded by main Claude (general JARFIS context); Mode B: spawnable subagent for tmux-isolated execution per ADR-0004 (129 lines)
├── legacy/                        # Archived v4-migration-only context (preserved verbatim per F-08)
│   └── v4-migration-jarfis-engineer.md  # Pre-Hybrid jarfis-engineer body — v3→v4 decisions, safety principles, milestone-aware context (144 lines, archived 2026-05-07 by ADR-0001)
├── jarfis-advocate.md             # Dialectic Review — change advocate; **Force-Acknowledge** Citation Format `path:LNN` (backticks; ADR-0005) + Concession Protocol; scope: sys-implement/sys-upgrade/sys-distill only (101 lines)
├── jarfis-critic.md               # Dialectic Review — change critic; **Force-Acknowledge** Citation Format `path:LNN` (backticks; ADR-0005) + Concession Protocol; scope: sys-* only (95 lines)
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
| `/jarfis:agent` | `jarfis/agent.md` | Skill+persona registry CRUD — skill list/add/update/remove (Context7-aware, diff-only YAML), persona list |
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
  - `jarfis_cli.py agent` — Skill+persona registry CRUD (`agent {skill,persona} {list,add,update,remove}`); SSOT = skill `.md` files; agent-composition.yaml is read-only from Python (diff-only via stdout); env-var configurable for testability (`JARFIS_SKILLS_DIR`, `JARFIS_COMPOSITION_PATH`). [v4.5 — agent-skill-system-v1]
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
  - `jarfis_cli.py migrate` — v4.3 → v4.4 org-root data-source migration (subcommand `v4.3-to-v4.4`; flags `--dry-run`, `--no-backup`)
- `~/.claude/scripts/jarfis/` — Python module directory (referenced by `jarfis_cli.py`)
  - `state.py` — .jarfis-state.json CRUD (v4 schema: work{} + org + sessionKey + phases.{N}.status; v3 flat-key dual emit removed in v4.1 per ADR-0002 — backward-compat read still accepted)
  - `verify.py` — Unified gate/phase/pattern verification (`gate-check` + `phase-check` + `phase-verify` + `pattern-detect`). v4 replacement for v3 `jarfis-black` LLM gate — deterministic Python, ~10ms, machine-verifiable (ADR-15; 1,349 lines)
  - `verify_helpers.py` — Shared helpers for verify.py entrypoints
  - `tmux_claude.py` — tmux-per-phase orchestration (B1 isolation: exact-match session name only; `--save-pane` post-mortem debugging; v4.0.4)
  - `trace.py` — Performance tracing module — opt-in via `JARFIS_TRACE` env var; `trace.log_event` API → `/tmp/jarfis-trace.jsonl` (or `$JARFIS_TRACE_PATH`); ~0.008% overhead when enabled, zero cost when off (ADR-20; v4.0.5)
  - `compose/` — Compose CLI package (`__main__.py` + `assembler.py` + `config.py` + `context7_research.py` + `models.py` + `reader.py` + `resolver.py` + `skills.py` + `skills_lib.py` + `validate.py`) — deterministic agent composition with 4-stage skill fallback, N-3 section-missing audit; `context7_research.py` (v4.1.1 B15) carries Tier-1 hint parsing + Tier-2/3 disambiguation + ResearchSession (cost guard + cache + telemetry); `resolver.py` (v4.3.0) walk-up fallback for monorepo SSOT — `base: all-projects` paths prefixed `.jarfis-project/` ascend `scope[i].path` until org.root / `.git` ancestor / depth=3 boundary, dedupe by absolute path with `from_scope_indices` provenance, trace event `compose_walkup_resolved`
  - `domain.py` — Domain Pack management module (list/detect/agents/compose/validate/scaffold/install)
  - `agent_admin.py` — `jarfis_cli.py agent` backend; reads `commands/jarfis/skills/*.md` + `commands/jarfis/agent-composition.yaml` (read-only); never writes composition.yaml — only diff stdout for `--bind-framework`; default-dry-run for skill add/remove; CLI subparsers for skill {list/add/update/remove} + persona list (462 lines)
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
  - `migrate.py` — v4.3 → v4.4 org-root data-source migration (v4.4.0; 341 lines; moves `.personal/orgs/{name}/{meetings,works,learnings.md}` into `{org.root}/.jarfis-org/`, flattens `_standalone` bucket, rewrites active `.jarfis-state.json` docsDir strings, git-orphan detection + `sync` field write, dry-run + backup tarball + idempotency, archives legacy `orgs/` as `orgs.v4.3-archive/`)
  - `wiki_search.py` — Semantic search (sentence-transformers bge-m3, wiki/meetings/works/**jarfis** indexing+search + incremental update + memory guard + CPU forced + MPS memory deduction; jarfis scope reads `~/.claude/` + repo + `.personal/.jarfis-index/` ChromaDB, 1,409 lines)
  - `implement.py` — sys-implement workspace manager (v4.2.0 ADR-0003) — manifest/state/log/RESUME/README + atomic writes + plan-name validation + workspace lock + cmd_init/state/log/resume/archive/list + `validate_citations` (path:LNN backticks, ADR-0005) + `classify_verdict` (Force-Acknowledge) + `recommend_execution_mode` (ADR-0004) + `extract_changed_files` (Step 4.5 RAG hook) (925 lines)
- `~/.claude/scripts/tests/` — pytest test directory (28 test modules covering all jarfis/ modules; run via `python3 -m pytest ~/.claude/scripts/tests/ -v --tb=short`; 820 tests passing @ v4.6.0)
  - `conftest.py` — Shared fixtures (jarfis_env, state_file, project_dir — tmpdir-based isolation)
  - `test_architecture.py` — Architecture invariants (domain boundaries, import hygiene)
  - `test_state.py` · `test_verify.py`-family (`test_gate_check.py`, `test_phase_verify.py`) · `test_tmux_claude.py` · `test_trace.py` · `test_compose_warnings.py`
  - `test_detect.py` · `test_domain.py` · `test_audit.py` · `test_measure.py` · `test_meetings.py`
  - `test_preflight.py` · `test_quality_gate.py` · `test_organization.py` · `test_validate.py`
  - `test_sync.py` · `test_utils.py` · `test_version.py` · `test_wiki_search.py` · `test_level_check.py` · `test_jarfis_cli.py`
  - `test_agent_admin.py` — agent_admin module tests (v4.5; 21 tests across TestSkillList/TestSkillAdd/TestSkillUpdate/TestSkillRemove/TestPersonaList/TestDispatcher; covers dry-run vs --apply, name validation, framework binding diff suggestion, persona enumeration; uses env-var injection for fixture isolation)
  - `test_implement.py` — sys-implement workspace + Force-Acknowledge dialectic + execution mode dispatch tests (v4.2.0; 670 lines, 57 tests covering plan-name validation / cmd_init/state/log/resume/archive/list / validate_citations / classify_verdict / recommend_execution_mode / extract_changed_files)
  - `test_compose_resolver_walkup.py` — monorepo SSOT walk-up resolver tests (v4.3.0; 10 tests covering walk-up engagement, prefix gating to `.jarfis-project/`, boundary precedence (org.root → `.git` ancestor → depth=3), per-package precedence, dedupe with `from_scope_indices`, shared SSOT label rendering)
  - `test_migrate.py` — v4.3 → v4.4 migration tests (v4.4.0; 10 tests covering dry-run listing, meetings/works/learnings move under `.jarfis-org/`, standalone flatten, sync field git/none branch, state.json docsDir string rewrite, backup tarball, idempotent re-run)
  - `test_state.py` — state.py module tests; v4.6.0 supplied 모드 9개 추가 (TestDesignSuppliedSchema, TestSetDesignMode, TestSetNestedDesignModeIntegration) — design.mode mutual exclusion + set_design_mode helper coverage
  - `test_phase_verify.py` — phase-verify entrypoint tests (M3 `_phase_3_verify`); v4.6.0 TestPhase3 supplied 모드 6개 추가 (mutual exclusion + per-page validation: pages/{slug}/index.html + reference.png + figmaPages == [] enforcement)
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
- `{JARFIS_SOURCE}/.personal/orgs/orgs.json` — Org registry (`org_name` → `org_root` path mapping; auto-registered during org-init)
- `{org_root}/.jarfis-org/` — Per-Org container (`wiki/`, `meetings/`, `works/`, `learnings.md`; physical org-root based; v4.4.0)
- `{JARFIS_SOURCE}/.personal/{meetings, works, learnings.md}` — Standalone fallback (no `wiki/`; flat, no `_standalone` wrapper)
- `{JARFIS_SOURCE}/.personal/sys-implements/{plan-name}/` — sys-implement workspace (v4.2.0 ADR-0003): `manifest.json` (immutable) + `state.json` (mutable state machine) + `RESUME.md` + `README.md` + `log/NNNN-{step}-{event}.json` (append-only event log) + `artifacts/step{N}/` (per-step deliverables incl. step2/before+after diff snapshots) + `compensation/` (rollback dir; undo.sh auto-generation deferred to v4.2.1+ per D10)
- `{JARFIS_SOURCE}/.personal/.jarfis-index/` — JARFIS self-knowledge ChromaDB (v4.2.0 ADR-0002 §2.4): `chroma.sqlite3` + `.vectors.npz` + collection `jarfis-system` (md/yaml/python files chunked + bge-m3 embeddings; refreshed via Step 4.5 incremental update; ~951 chunks @ 2026-05-07)
- `$JARFIS_ORG_DIR/workflow-metrics.tsv` — Workflow metrics cumulative record (AutoResearch results.tsv pattern, appended at Phase 6 Step 6-2.5)
- `{JARFIS_SOURCE}/VERSION` — Git repo semver version (currently 4.0.6)
- `{JARFIS_SOURCE}/CHANGELOG.md` — Keep-a-Changelog format change history

## Internal Reference Map
- `agent.md` → user-facing slash command. Calls `jarfis_cli.py agent` for CRUD; orchestrates Context7 MCP at the slash-command layer (skill add/update flesh-out); never auto-writes `agent-composition.yaml` — surfaces diff lines for manual application.
- `agent_admin.py` → backs `jarfis_cli.py agent` subcommand (skill list/add/update/remove + persona list). Reads `commands/jarfis/skills/*.md` + `commands/jarfis/agent-composition.yaml` (safe_load only). **Never writes composition.yaml** (Critic blocker: 51-line operator-spec comments must be preserved). Skill `.md` is SSOT; framework/role binding is opt-in via diff suggestion to stdout.
- `jarfis.md` → references all commands (helper text)
- `work-meeting.md` → independent (optionally references project-profile, context, learnings) + mid-save for compact resilience
- `work.md` → v4 orchestrator. References `/jarfis:project-init` (profile load guide) + meeting artifacts (Phase 0 queries `jarfis_cli.py meetings` + AskUserQuestion selection + dynamic scan of selected meeting dir) + `.compact-backups/` reference (on Resume) + `prompts/*.md` (per-Phase executor prompts, loaded by jarfis-foreman in each phase's tmux session) + `agent-composition.yaml` (via `jarfis_cli.py compose`). v3 state detected → halt + advise user; **no silent migration** (per F-08).
- `work.md` Phase 0 → step 11 supplied mode pre-validation (preflight 직후 main session 검증; suppliedPath 디렉토리 + pages/ + 최소 1개 page index.html+reference.png).
- `prompts/*.md` → agent prompts externalized from work.md; loaded by **jarfis-foreman** inside each phase's dedicated tmux session (`{sessionKey}-phase{N}`).
- `prompts/phase3.md` → unified figma + text design path (parallel multi-Figma page processing, per-section v5 generation, Framelink MCP + asset download + token-map + UX Designer reproduction + PO/UX review loop).
- `prompts/phase3.md` → Branch A (figma) / Branch B (text) / **Branch C (supplied — v4.6.0)**: jarfis-foreman 이 외부 시안 디렉토리(`state.design.suppliedPath`)를 `$DOCS_DIR/design/` 로 cp/rsync + 누락 responsive PNG 만 Playwright 캡처. ux-designer spawn 안 함. ia.json/sitemap.md 자동생성 금지.
- `templates/*.md` → artifact templates externalized from work.md/work-meeting.md (generated by distill, loaded when needed in corresponding Phase).
- `templates/sitemap.md` → supplied 모드 한정 IA 사이트맵 마크다운 템플릿. 사용자가 시안에 직접 동봉. **시스템 자동 생성 금지** (SSOT). Phase 6 Track B 가 wiki/DESIGN/pages/{project}/sitemap.md 로 sync.
- `templates/ia-schema.md` → supplied 모드 한정 ia.json 스키마 문서. 사용자가 시안에 직접 동봉. **시스템 자동 생성 금지** (SSOT). 미동봉 시 wiki sync 시 ia.json 생략.
- `project-update.md` → references `/jarfis:project-init` (guide when no profile exists, analysis criteria reference).
- `project-init.md` → references `templates/project-profile.md` (profile artifact format).
- `sys-distill.md` → reads `jarfis-index.md` first → measures tokens via `jarfis_cli.py measure` → analyzes commands/jarfis/*.md + agents/jarfis/*.md, updates this index.
- `~/.claude/agents/jarfis/personas/*.md` → composed dynamically by `jarfis_cli.py compose` (reads `agent-composition.yaml` + base project-profile + project-rule + wiki-cache + domain skills fallback chain). Main work path; Dialectic agents are sys-* only.
- `~/.claude/agents/jarfis/jarfis-foreman.md` → loaded by `Task` tool inside each phase's tmux session; runs phase prompt + spawns sub-agents via Task + compose CLI + merges outputs.
- `~/.claude/agents/jarfis/jarfis-engineer.md` → **Hybrid Persona + Spawnable** (v4.2.0 ADR-0001). **Mode A**: loaded as a persona by main Claude for general JARFIS context. **Mode B**: spawnable subagent (e.g. via `Task` from sys-implement Step 2 tmux mode) — RAG-searches affected files via `jarfis_cli.py search jarfis "..."` (consumes `wiki_search.py` jarfis scope) + applies edits + runs Python TDD + writes `attempt{K}.json` per ADR-0004.
- `~/.claude/agents/jarfis/legacy/v4-migration-jarfis-engineer.md` → archived pre-Hybrid body (v4-migration only); preserved verbatim per F-08, no longer auto-loaded.
- `~/.claude/agents/jarfis/jarfis-advocate.md` / `jarfis-critic.md` → Dialectic Review with **Force-Acknowledge Citation Format** (ADR-0005): every claim must cite `path:LNN` (or `path:N-M`) wrapped in backticks; orchestrator's `validate_citations()` (in `implement.py`) checks form only — path exists + line in range; no valid citation = formal violation. `classify_verdict()` decides ACKNOWLEDGED-advocate-wins / ACKNOWLEDGED-critic-wins / UNRESOLVED. Concession Protocol: explicit `### Conceded` block when superseded by stronger citation. Scope: sys-implement/sys-upgrade/sys-distill only (per ADR-13 + F-14 + ADR-0005). No participation in phase*.md workflow prompts.
- `sys-implement.md` → reads/updates `jarfis-index.md` + bumps VERSION/CHANGELOG via `jarfis_cli.py version` + delegates workspace mgmt to `implement.py` (`jarfis_cli.py implement init/state/log/resume/archive/list`) + spawns advocate+critic at Step 1.5 + dispatches Step 2/3 to single-mode (main) or tmux-mode (jarfis-engineer Mode B) per `recommend_execution_mode()` + triggers `search index jarfis --incremental` at Step 4.5.
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
- `prompts/phase6.md` Track B → rsync 가 시안 전체를 wiki/DESIGN/pages/{project}/ 로 sync (sitemap.md, ia.json, assets/ 자동 포함). supplied 모드 한정으로 시안에 없는 항목은 자동 생성하지 않는다 (SSOT).
- `wiki-loading.md` → calls `jarfis_cli.py search wiki` in 4-Step Step 3 (fallback: LLM judgment).
- `wiki_search.py` → referenced by wiki-loading.md/phase6.md/org-init.md/work.md/work-meeting.md/search.md. Supports both `jarfis_cli.py search` (new) and `jarfis_cli.py wiki` (deprecated). **v4.2.0**: also serves the `jarfis` scope (self-knowledge index over `~/.claude/` + repo + `.personal/.jarfis-index/`) consumed by jarfis-engineer Mode B + advocate/critic dialectic context-gathering. `cmd_index_jarfis` supports `--incremental --files <csv>` for Step 4.5 RAG hook.
- `implement.py` → backs `jarfis_cli.py implement` subcommand (init/state/log/resume/archive/list); also exposes `validate_citations()`, `classify_verdict()`, `recommend_execution_mode()`, `extract_changed_files()` consumed inline by sys-implement.md Steps 1.5/1.7/4.5. Dotted-key state paths (`steps.step1.5.status` etc.) addressed via greedy longest-prefix match in `_set_nested_key`.
- `search.md` → calls `jarfis_cli.py search {scope} "query" --pretty` (direct user search).
- `search-setup.md` → standalone execution (venv creation + sentence-transformers installation); guides to `/jarfis:search-index` on completion.
- `search-index.md` → selects Org from orgs.json → runs `jarfis_cli.py search index {scope}` (wiki+meetings+works). `--current` flag for current Org only.
- `work-meeting.md` M-3 → auto-calls `jarfis_cli.py search index meetings` (best-effort).
- `phase6.md` → auto-calls `jarfis_cli.py search index wiki` + `search index works` (best-effort).
- `org-init.md` → displays `/jarfis:search-setup` → `/jarfis:search-index` guide on completion.
- `verify.py` → referenced by work.md Gate Point Rules (mandatory `gate-check` before any Gate presentation); also provides `phase-check` (Phase start) and `phase-verify` / `pattern-detect` (tmux foreman).
- `state.py` → `set_design_mode(state, new_mode)` helper (v4.6.0): mode 전환 시 invariant 강제 (supplied → figmaPages=[]; figma → suppliedPath=null; text/null → 둘 다 reset). `cmd_set_nested` 가 design.mode 변경 시 자동 호출.
- `verify.py` → `_gate2_checks` 와 `_phase_3_verify` 둘 다 mode == "supplied" 분기 추가 (defense in depth): `pages/{slug}/index.html` + `reference.png` 존재 검증, figmaPages mutual exclusion 검사. 위반 시 design 검증 silent skip 방지 (Critic blocker #1).
- `tmux_claude.py` → used by jarfis-foreman to create/reattach/tear down phase-specific tmux sessions (`{sessionKey}-phase{N}`); enforces B1 exact-match isolation; `--save-pane` option for post-mortem debug.
- `trace.py` → opt-in via `JARFIS_TRACE=1`; `trace.log_event(event, attrs)` called from hot paths in tmux_claude / verify / compose; output JSONL at `/tmp/jarfis-trace.jsonl` (or `$JARFIS_TRACE_PATH`).
- `agent-composition.yaml` → consumed by `jarfis_cli.py compose`; defines per-agent persona + scope + skills_from_domain + context (base: project | all-projects | docs | org | org_wiki).
- `tests/` → referenced in sys-implement.md Step 2 Python TDD rules (26 test modules covering all Python scripts incl. `test_implement.py` for v4.2.0 workspace + dialectic + dispatch). Run via `python3 -m pytest ~/.claude/scripts/tests/ -v --tb=short`. **Test isolation invariant** (v4.2.0 conftest fix): `jarfis_env` fixture monkeypatches CWD to `tmp_path` so tests pass regardless of where pytest is invoked.

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
- **Agent skill registry (v4.5+)**: skill `.md` files in `commands/jarfis/skills/` are SSOT. Add via `/jarfis:agent skill add <name>` (default dry-run; `--apply` writes file). Framework binding via `--bind-framework <fw>` produces a diff suggestion only — `agent-composition.yaml` must be hand-edited (operator-spec comments are load-bearing per `~/.claude/commands/jarfis/agent-composition.yaml:1-51`). Removal via `/jarfis:agent skill remove <name>` (dry-run shows references first; `--apply` deletes file but does NOT auto-cleanup yaml refs).
- **State write rule (v4 ADR-18)**: only the main session writes `.jarfis-state.json`; tmux sub-agents write to `phase-results/phase{N}/attempt{K}.json` + phase output dirs. Violating this breaks the single-writer invariant.
- **Version management**: after sys-implement/sys-distill/sys-upgrade completion → update VERSION + .jarfis-version + __init__.py + this index (`Version:` header) + CHANGELOG.
- **Repo sync**: after sys-implement/sys-distill/sys-upgrade completion → run `python3 ~/.claude/scripts/jarfis_cli.py sync` (manual copy prohibited).
- **Python TDD**: when modifying `scripts/jarfis/*.py` → write/update tests first in `scripts/tests/` → modify code → verify all pass via `python3 -m pytest ~/.claude/scripts/tests/ -v --tb=short`.
- **Git repo**: check path in `~/.claude/.jarfis-source` (default: `~/repos/jarfis`).
- **Dialectic Review scope (ADR-13 + F-14)**: Advocate/Critic agents apply **only** to sys-implement/sys-upgrade/sys-distill. Workflow phases (phase*.md) rely on P7 Deterministic Foundation + TDD Ratchet (conditional), not Dialectic.
- **Force-Acknowledge Dialectic (v4.2.0 ADR-0005)**: every claim from advocate/critic must include a `path:LNN` citation wrapped in backticks (e.g. `` `~/.claude/commands/jarfis/sys-implement.md:194` ``). Orchestrator runs `validate_citations()` from `implement.py` — form-only check (path on disk + line in range). No valid citation → formal violation by that side. Concession via explicit `### Conceded` block. Verdict: ACKNOWLEDGED-advocate-wins / ACKNOWLEDGED-critic-wins / UNRESOLVED → user Confirm at sys-implement Step 1.5.
- **sys-implement workspace (v4.2.0 ADR-0003)**: every `/jarfis:sys-implement` run produces a workspace at `{JARFIS_SOURCE}/.personal/sys-implements/{plan-name}/`. plan-name = kebab-case ≤40 chars matching `^[a-z][a-z0-9-]*$`. Manifest is immutable after init; state.json is the mutable state machine; log/ is append-only event log. Use `jarfis_cli.py implement init/state/log/resume/archive/list` — never edit state files manually.
- **Execution mode dispatch (v4.2.0 ADR-0004)**: sys-implement Step 1.7 selects single (main Claude direct) vs tmux (jarfis-engineer Mode B) via `recommend_execution_mode(impact_scope)`. Force-tmux when file_count ≥ 6 OR change_type=structural. Argument override: `--mode=single`/`--mode=tmux`. "Skip Step 2" = analysis-only plan.
- **RAG self-knowledge auto-update (v4.2.0 ADR-0002 §2.4)**: sys-implement Step 4.5 calls `jarfis_cli.py search index jarfis --incremental --files <csv>` after Step 4 sync. Best-effort — failure logs but does not roll back the sync.
- **v3 state detection**: `.jarfis-state.json` with `project_name` (no `sessionKey`) → v4 work.md halts with guidance message in `$LOCALE`. Never silently migrate (F-08 + MIGRATION.md §3).
- **v3 fallback removal (v4.1, ADR-0002)**: legacy `work-legacy.md` and the `state.py:cmd_init` v3 flat-key dual emit were removed in M2; emergency rollback now relies solely on git tag `v4.0.7` + `rollback.sh`.
- **Supplied design mode (v4.6.0+)**: `state.design.mode = "supplied"` 는 외부 시안(HTML+assets)을 jarfis-foreman 이 cp 하는 모드. **SSOT 원칙**: 시안 = 유일 진실. 시스템은 시안에 없는 sitemap.md/ia.json 을 자동 생성하지 않는다 (`templates/sitemap.md`, `templates/ia-schema.md` 둘 다 명시). suppliedPath 변경 시 `verify.py` mode 분기 + `state.py set_design_mode` invariant 동기화 의무. `agent-composition.yaml` ux-designer 는 supplied 모드에서 spawn 되지 않음 (Branch C 는 foreman-only orchestrator step).
