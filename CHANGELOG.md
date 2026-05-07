# Changelog

All notable changes to JARFIS will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [4.5.0] - 2026-05-07

- implement: agent-skill-system-v1 — single /jarfis:agent command + agent_admin.py module (skill+persona registry CRUD, Context7-aware, diff-only YAML safety)

## [4.4.0] - 2026-05-07

- implement: v4.4.0 — org_root data-source restructure (.jarfis-org single container; D1-D7 + Critic Fix A/B + auto-migration)

## [4.3.0] - 2026-05-07

- implement: monorepo SSOT walk-up resolver fallback (.jarfis-project/ prefix-gated, org.root/.git/depth=3 boundary, dedupe with from_scope_indices) + project-init monorepo detection + project-profile Monorepo Layout template section

## [4.2.0] - 2026-05-07

Minor release — sys-implement reborn as a Saga-style state machine with self-knowledge RAG and a Force-Acknowledge dialectic. Major surface change is invisible from outside (`/jarfis:sys-implement` still entry point), but every run now produces a versioned, resumable workspace and the dialectic converges on file:line citations rather than free-form rhetoric.

### Added
- **`jarfis-engineer` Hybrid Persona + Spawnable mode (ADR-0001)**: Mode A loaded as session persona for general JARFIS context; Mode B spawnable via `Task` for tmux-isolated execution per ADR-0004. Pre-Hybrid v4-migration body archived verbatim at `agents/jarfis/legacy/v4-migration-jarfis-engineer.md`.
- **RAG self-knowledge (ADR-0002)**: ChromaDB collection `jarfis-system` at `{JARFIS_SOURCE}/.personal/.jarfis-index/` indexes `~/.claude/` + repo md/yaml/python files with sentence-transformers bge-m3 embeddings. Query via `jarfis_cli.py search jarfis "<keywords>"`. Incremental update via `search index jarfis --incremental --files <csv>`. ~951 chunks at release.
- **sys-implement workspace (ADR-0003)**: every `/jarfis:sys-implement` run produces `{JARFIS_SOURCE}/.personal/sys-implements/{plan-name}/` with `manifest.json` (immutable) + `state.json` (mutable state machine) + append-only `log/NNNN-{step}-{event}.json` + `artifacts/step{N}/` (per-step deliverables incl. step2/before+after diff snapshots) + `compensation/` (rollback dir; see Migration). Saga + LangGraph + Command + Clean Architecture synthesis — no external orchestrator dep.
- **Execution Mode dispatch (ADR-0004)**: sys-implement Step 1.7 selects `single` (main Claude direct) vs `tmux` (jarfis-engineer Mode B) via `recommend_execution_mode(impact_scope)`. Force-tmux when file_count ≥ 6 OR change_type=structural. `--mode=single`/`--mode=tmux` overrides. "Skip Step 2" available for analysis-only plans.
- **RAG auto-update (ADR-0002 §2.4)**: sys-implement Step 4.5 calls `jarfis_cli.py search index jarfis --incremental --files <csv>` after Step 4 sync. Best-effort — failure logs but does not roll back.
- **`jarfis_cli.py implement` subcommand**: `init` / `state` (--get / --set / --set-nested) / `log append` / `resume` / `archive` / `list`. Plan-name validated against `^[a-z][a-z0-9-]*$` (≤40 chars).
- **Skill: cloudflare** (`commands/jarfis/skills/cloudflare.md`) — Cloudflare Workers / Pages Functions / Durable Objects expertise. Mapped via `cloudflare-workers: [cloudflare, nodejs]` in `agent-composition.yaml`.

### Changed
- **Dialectic Review → Force-Acknowledge (ADR-0005)**: 1-round; orchestrator runs `validate_citations()` (form-only check — path on disk + line in range; backticked `path:LNN` mandatory). No valid citation = formal violation. Three verdicts: ACKNOWLEDGED-advocate-wins / ACKNOWLEDGED-critic-wins / UNRESOLVED → user Confirm.
- **`jarfis-advocate.md` / `jarfis-critic.md`**: mandatory Citation Format + explicit `### Conceded` block (Concession Protocol).
- **`sys-implement.md`** (294 → 555 lines): Step 0 workspace init, Step 1.5 force-ack rewrite, Step 1.7 mode dispatch (new), Step 4.5 RAG hook (new). Step 0 → Step 5 mandatory order enforced.
- **`wiki_search.py`** (~950 → 1,409 lines): adds `jarfis` scope (reads `~/.claude/` + repo + `.personal/.jarfis-index/`) + `--incremental --files <csv>` for Step 4.5 hook.
- **`commands/jarfis/search.md` / `search-index.md`**: `jarfis` scope added.
- **`commands/jarfis/skills/aws-lambda.md`**: cost guard one-liner added under Version & Environment Notes (M7.2 small E2E dogfood).

### Fixed
- **Test isolation**: `scripts/tests/conftest.py` `jarfis_env` fixture now `monkeypatch.chdir(tmp_path)` — previously, `meetings.main()` calling `get_org_dir(os.getcwd())` walked up to the caller's real org root (e.g. when pytest was invoked from inside an org-marked project), bypassing the fixture's seed and surfacing 3 spurious `test_meetings.py` failures.
- **`implement.py:_set_nested_key`**: dotted literal keys (`step1.5`, `step3.5`, `step4.5`) were silently nested as `step1 → "5"`, leaving the real keys at `pending`. Fixed with greedy longest-prefix match honoring existing literal keys + 2 regression tests.

### Tests
- **751 PASSED** (was 704 baseline + 28 M4 + 14 M3.2 + 20 M5.1 + 11 M6 + 2 M7.2 dotted-key regression gates; 0 regressions across all gates). New module: `test_implement.py` (57 tests covering plan-name validation / cmd_init/state/log/resume/archive/list / `validate_citations` / `classify_verdict` / `recommend_execution_mode` / `extract_changed_files`). 26 test modules total.

### Migration
- **No code change required for users.** Existing `/jarfis:sys-implement` invocations transparently produce the new workspace.
- **`compensation/undo.sh` rollback automation deferred to v4.2.1** (D10): ADR-0003 §3.2 already noted self-rollback safety holes (idempotency, three-way consistency across `~/.claude/` + repo + RAG, external mutation blindness). v4.2.1 will redesign `/jarfis:sys-rollback` around `git revert` of the Step 5 commit SHA — git history as truth source. Until then, manual revert remains the recommended rollback path.
- **Skipped during v4.2.0 release**: tmux mode end-to-end exercise (no large change in scope to trigger `recommend_execution_mode → tmux`); will surface naturally in user workflow. `_TECH_STACK_ALIASES` cloudflare/workers/wrangler entries (M7.2 medium critic flag) tracked as follow-up.

## [4.1.1] - 2026-05-06

Patch release — v4.1.1 backlog items B1, B2, B15 (β cut). Tooling self-bootstrapping verified at release: B1 fix syncs fixtures cleanly, B2 fix updates `Last updated: ... (note) | Version: ...` index lines without manual intervention.

### Added
- **B15 — Context7 MCP integration (proactive research pattern)**: `rules/context7-research.md` defines 3-tier disambiguation (skill hint pin → Tech Stack versioned ID → autonomous decision tree), 5-call cost guard, skill-priority override on conflict, and `context7_query_emitted` telemetry (7th JARFIS_TRACE event). 17 skills carry curated `<!-- jarfis:context7 -->` hints (library_id + 5–7 query topics). 4 implement personas (BE/FE/DevOps/Security) reference the rule. `compose/context7_research.py` (`parse_skill_hint` / `select_library_id` / `ResearchSession`) is the pure-Python helper consumed by Phase 4 sub-agents. ADR-0005.

### Fixed
- **B1 — `sync.py` fixture sync gap**: walking `scripts/jarfis/` previously yielded only `.py` files, dropping non-Python fixtures (manifests, build configs, lockfiles, marker files) and forcing manual `cp -r` recovery during v4.1.0 milestones. Pattern-blind walk under `tests/fixtures/` plus an explicit `__pycache__` prune now syncs all 23 fixture files in one pass. Permanent regression gate: `test_sync_fixtures.py` (10 tests).
- **B2 — `version` command regex narrowness**: the index-line update regex matched only the strict `Last updated: <date> | Version: <semver>` shape, silently skipping lines with milestone parentheticals (e.g. `Last updated: 2026-05-06 (M7 release) | Version: 4.0.7`). Regex now tolerates an optional parenthetical after the date and arbitrary whitespace around the pipe; replacement is canonical (annotations dropped on bump for idempotency). Permanent regression gate: `test_version_regex.py` (8 tests).

### Tests
- 676 PASSED (was 628 after M2; +48 from B15: 43 wrapper + 5 telemetry; +0 regressions across all v4.1.0 gates).

## [4.1.0] - 2026-05-06

- implement: JARFIS v4.1 — senior-* consolidation + desktop reinforcement + mobile pack (RN)

## [4.0.7] - 2026-04-21

Docs-only PATCH. `jarfis-index.md` (system inventory) refresh — closes findings F-01 by aligning the index 1:1 with v4.0.6 reality. Also resolves a pre-existing `~/.claude/.jarfis-version` drift that the v4.0.6 release missed (`4.0.5` → `4.0.7`). Backlog files cascade-renamed (v4.0.7 → v4.0.8, v4.0.8 → v4.0.9) to free the v4.0.7 slot for this docs-only patch.

No code / schema / CLI / prompt changes. Backward-compatible for all callers.

### Changed
- **`commands/jarfis/jarfis-index.md`** — 256 → 259 lines, realigned to v4 reality:
  - `work.md` "~890 lines" → actual 255 lines (v4 rewrite); v3/v4 lineage notes corrected.
  - `prompts/`: `phase1.md` → `phase1b.md` (Phase 1a runs in main inside work.md); `phase3-figma.md` merged into unified `phase3.md`; line counts for phase2/3/4/4-5/5/6 corrected.
  - Agents: v3 senior-* engineers removed. Now 4 top-level agents (`jarfis-foreman`, `jarfis-engineer`, `jarfis-advocate`, `jarfis-critic`) + 9 personas under `personas/` composed via `agent-composition.yaml` (ADR-17).
  - Skills: flat `commands/jarfis/skills/` catalog (16 skills, relocated from `domains/{web,desktop}/skills/`).
  - Templates: `skill-template.md` added (v4 new, checkpoint style used by sys-distill for skill creation).
  - Scripts: `verify.py` (ADR-15, 1,349 lines — replaces v3 `jarfis-black` LLM gate), `tmux_claude.py` (ADR-16), `trace.py` (ADR-20, v4.0.5 opt-in), `compose/` package (ADR-17) documented.
  - `jarfis_cli.py`: v4 top-level verify commands documented (`gate-check` / `phase-check` / `phase-verify` / `pattern-detect` / `compose`).
  - Single-writer state rule (ADR-18), Dialectic Review scope (sys-* only, ADR-13 + findings F-14), v3 state silent-migration ban (findings F-08) cross-referenced.
  - Header: `Version: 4.0.6 → 4.0.7`, `Last updated: 2026-04-19 → 2026-04-21`.
- **`README.md`** — L497 jarfis-index row note updated from `(별도 세션 갱신 대상)` to `(v4.0.7 refreshed)`.

### Fixed
- **`~/.claude/.jarfis-version`** — drift repaired: `4.0.5` → `4.0.7`. v4.0.6 release did not bump this local marker (pre-existing bug). Same bump applied to `~/.claude/scripts/jarfis/__init__.py` (also at `4.0.5`).
- **findings F-01** (jarfis-index.md stale) — marked Resolved in `~/Upscales/jarfis-v4-docs/findings.md` with evidence trail.

### Migration
- **Backlog cascade rename** — to free the v4.0.7 slot for this docs-only patch:
  - `v4.0.7-backlog.md` (Operational Threshold Tuning, EVAL-1/2/3) → `v4.0.8-backlog.md`
  - `v4.0.8-backlog.md` (Audit CLI, N-4 data-gated, originally moved from v4.0.6 on 2026-04-20) → `v4.0.9-backlog.md`
  - Internal self-refs, commit-message templates, preflight/postflight script names, hotfix branch names, and dependency references updated inside both renamed files. Dependency chain now explicit: `v4.0.6 → v4.0.7 → v4.0.8 → v4.0.9`.
- **Cross-doc `v4.0.7+` cleanup refs** updated to `v4.0.9+` (work-legacy.md removal target, `state.py` v3 dual-shape cleanup) in: `DESIGN.md`, `MIGRATION.md`, `commands/jarfis/jarfis-index.md`, `commands/jarfis/work-legacy.md`. Removal window itself unchanged (post-2026-05-03).

### Tests
- No new tests (docs-only). `pytest scripts/tests/ --ignore=scripts/tests/test_meetings.py` expected unchanged from v4.0.6 baseline (**448 passed**).

## [4.0.6] - 2026-04-20

Docs refresh + polish release. Root documentation (PHILOSOPHY, DESIGN, WORKFLOW, AGENTS, INFRASTRUCTURE, README, WIKI_SEARCH) realigned to v4 reality; MIGRATION.md created as v3→v4 transition guide with §Principle Changes as footnote landing target. Two v4.0.6-pre polish items bundled. No v4 code or prompt changes — documentation-only refresh.

Original v4.0.6 plan (`jarfis audit` subcommand) deferred to v4.0.8 due to its data gate (`org_wiki_usage_count >= 3`) not yet met. v4.0.7 (Operational Threshold Tuning, EVAL-1/2/3) retains its original scope.

### Changed
- **Root docs v4 refresh** — identified by three-round external review (ChatGPT + Claude, 2026-04-19) as v4's largest remaining gap ("system advanced to v4 but philosophy/design docs stayed on v3"). This batch closes the self-explanation drift.
  - `PHILOSOPHY.md` — 57 → 335 lines. 7 principles (P0 Function over Form + #1~#6). v3 P1 (Orchestration for All) deleted — no decision-driving evidence across 46 days. v3 P2+P5+P6 merged into #5 Context as Investment (economics + artifact format + composition aspects). v3 P4 renamed #2 Dialectic for Self-Modification with sys-* scope explicit. ROI framing + aspiration + falsifiable clause on P0.
  - `DESIGN.md` — 585 → 1,359 lines. Append + revise + supersede. 14 existing ADRs preserved as history with status banners + v4 Update sections. ADR-4 superseded by ADR-21; ADR-6 superseded by ADR-19. New ADR-15 verify.py, ADR-16 tmux-per-phase, ADR-17 agent-composition.yaml, ADR-18 single-writer state, ADR-19 Phase 4.5, ADR-20 JARFIS_TRACE opt-in, ADR-21 Ratchet reality (honesty clause). Appendix B maps v3 P{N} → v4 #{N}; Appendix C links distributed ADRs (e.g., `adr/v4.0.5-trace-design.md`).
  - `WORKFLOW.md` — full rewrite (678 lines). 13-step narrative (T/0/1a/1b/G1/2∥3/G2/4/4.5/5/G3/6). Main vs tmux-foreman boundary. Triage A/C/Resume (Type B removed M7). v3 state silent migration ban (findings F-08). Phase 5 review_round loop + pattern-detect.
  - `AGENTS.md` — full rewrite (486 lines). 4 top-level agents (foreman/engineer/advocate/critic). 9 personas with verified model tags (6 opus judgment / 3 sonnet execution). 10 composition roles including tech-lead split (reviewer/strategist, M4). 16 skills + 4-stage fallback chain. Dialectic scope sys-* only (findings F-14); level-check excluded with rationale.
  - `INFRASTRUCTURE.md` — full rewrite (627 lines). Directory trees (install/work/org/project levels). 4 hooks with actual sizes + kill switches. tmux B1 isolation, `--save-pane` (v4.0.4), `JARFIS_TRACE` (v4.0.5). Single-writer state rule (ADR-18, source: work.md:22). Explicit Trade-offs section (findings F-10): zombie sessions, debug cost, tmux dependency, init overhead, solo dogfooding pool.
  - `README.md` — full rewrite (521 lines). Depth-first positioning (14-axis rubric internal benchmark: 82.5/100 unweighted, 85.5 depth-first weighted). Bridge sentence (FE 6yr systems thinking ↔ AI orchestration). 13-step mermaid flow. 5 core concepts. Limitations honesty section.
  - `WIKI_SEARCH.md` — fact-check + partial rewrite (260 lines). Actual `wiki_search.py` implementation reflected: BAAI/bge-m3, 4GB memory guard, MPS GPU deduction (Apple Silicon), LLM fallback path.

### Added
- **MIGRATION.md** (new, 501 lines). v3→v4 transition guide + `§Principle Changes` section (landing target for PHILOSOPHY v2 footnotes). Breaking changes across 8 areas (state schema, agents, verification, ratchet, triage, phase structure, skills, misc). Transition paths for in-flight v3 workflows. work-legacy.md handling (F-02: banner + 2026-05-03 expiry). Troubleshooting 8 common v3→v4 confusions. CHANGELOG cross-reference.
- **N-4-pre** `version.py` `__init__.py` path isolation. `version.py::init_file` now resolved against `claude_dir` so `pytest scripts/tests/test_version.py` no longer mutates real-install `scripts/jarfis/__init__.py` with fixture values. Production path behavior unchanged. +1 regression test `test_patch_bump_does_not_mutate_installed_init`. Fixes pytest-triggered preflight "uncommitted changes" FAIL observed after v4.0.5 merge.
- **N-4-legacy-banner** `work-legacy.md` deprecation banner. `/jarfis:work-legacy` slash command remains operational for emergency v3 rollback, but title now flags `(LEGACY v3)` and body banner documents the 2026-05-03 removal window and dependency on `state.py` v3 flat-key dual-emit. `state.py` dual-shape compat preserved until banner expiry. Removal target: v4.0.7+ cleanup item (now v4.0.9+ since v4.0.8 is audit CLI batch).

### Migration
- v4.0.5 → v4.0.6 is backward-compatible for existing callers. No schema / prompt / CLI change. Documentation-only update + 2 pre-items that do not alter runtime behavior.
- **Audit CLI deferred to v4.0.8**: `v4.0.6-backlog.md` renamed to `v4.0.8-backlog.md` (was originally scoped for v4.0.6 N-4 but data-gated on `org_wiki_usage_count >= 3` which has not yet accumulated). `v4.0.7` retains its existing Operational Threshold Tuning scope.
- **External-facing docs change**: anyone linking to the old README / PHILOSOPHY sections may see section IDs shift. DESIGN ADRs preserve their `<a id="adr-N">` anchors across the rewrite — ADR-1 through ADR-14 still resolve.

### Tests
- No new tests in this batch (docs-only). `pytest scripts/tests/ --ignore=scripts/tests/test_meetings.py` → **448 passed** (unchanged from v4.0.5 baseline). 3 pre-existing `test_meetings.py` failures unchanged.

## [4.0.5] - 2026-04-20

HIGH-risk batch: `trace.py` subsystem activation. 1 logical item (N-2) executed across 3 sub-batches (5a skeleton → 5b instrumentation → 5c documentation). Gated by `JARFIS_TRACE` environment variable — defaults remain unchanged, zero cost when off.

### Added
- **5a** `trace.is_enabled()` gate (`os.getenv("JARFIS_TRACE", "0") != "0"`) + `_safe_append` helper that swallows any write/serialization error. Both existing entry points (`trace_agent` context manager, `trace_phase`) now return early when disabled. Identifiable no-op span id (`agent-<persona>-disabled`) preserved so callers can log/assert the off path. +11 tests in `test_trace.py` (off path, env unset, write-failure shield, yield-after-failure).
- **5b** `trace.log_event(event, attrs=None, path=None)` free-form event API for hot-path instrumentation. Resolution order for path: explicit arg → `$JARFIS_TRACE_PATH` → `/tmp/jarfis-trace.jsonl`. Output format: JSONL with `{ts, event, attrs}`. +6 tests covering env override precedence and failure shield.
- **5b** Hot-path instrumentation, one commit per site:
  - `tmux_claude.py` main loop emits `tmux_session_start` / `tmux_session_ready` / `tmux_prompt_sent` / `tmux_session_end` (with session name, workspace, status, duration_ms, reason).
  - `verify.cmd_phase_verify` emits `phase_verify_start` / `phase_verify_end` (phase_id, verdict, missing_count, duration_ms).
  - `compose/__main__::_compose` emits `compose_start` / `compose_end` (agent, scope_index, context_files, injected_files, skills_count, prompt_chars, duration_ms).
- **5c** `work.md` new `## Troubleshooting` section: activation / deactivation commands, event schema table (8 events), safety notes, file-growth caveat.
- ADR at `adr/v4.0.5-trace-design.md` documenting context, decision, alternatives (default-on rejected; out-of-process daemon rejected; new `start_span`/`log_event`/`flush` API reduced to just `log_event`), consequences, and rollback strategy per sub-batch.

### Safety
- Every instrumentation site is doubly guarded: outer `try / except Exception: pass` + inner `if trace.is_enabled():`. A trace-side failure cannot flip a Phase outcome.
- Kill switch: `export JARFIS_TRACE=0` or `unset JARFIS_TRACE`. Takes effect at the next process boundary — no code revert required.
- Default behaviour (unset env) is identical to v4.0.4. Opt-in is the only path to collect data.

### Performance
- `JARFIS_TRACE` unset / "0": zero additional I/O. Gate is a single `os.getenv` call.
- `JARFIS_TRACE=1`: micro-benchmarked at ~25 μs/event (200 events × 30 repeats, median). Projected Phase 6 trace surface ~14 events → ~0.35 ms overhead vs. typical 60 s Phase 6 wall time → 0.008% (≪ ±20% tolerance). Real-env on-state measurement deferred to first production session; will be back-filled in v4.0.6+.

### Tests
- `pytest scripts/tests/ --ignore=scripts/tests/test_meetings.py` → **447 passed** (was 431; +16 from trace gated-path + log_event coverage). 3 pre-existing test_meetings.py failures unchanged.

### Migration
- v4.0.4 → v4.0.5 is a no-op for existing callers — `JARFIS_TRACE` defaults to off. Enable per-session only when observability is needed.

## [4.0.4] - 2026-04-20

Small independent infra sprints. 2 items touching context injection and tmux post-mortem debugging. Both changes are additive — existing call sites keep working unchanged.

### Added
- **N-1** `tmux_claude.py --save-pane <path>` option. Captures full tmux scrollback via `tmux capture-pane -S -` right before the session is killed, writing to the given path (standard recommendation: `{docsDir}/phase-results/phase{N}/attempt{K}.pane.log`). Best-effort — capture/write failures emit a stderr warning and do not flip the phase exit code. Addresses M8 Step 8.5 Attempts 1–3 where verify FAIL root cause was unrecoverable after the tmux session ended. +3 tests in `test_tmux_claude.py`.
- **N-3** `compose/__main__.py` emits a `[compose warning]` stderr line per context block whose `sections:` filter references a heading absent from the target file. `meta.context_files[].missing_sections` record is unchanged; the stderr line just surfaces the same data to humans running compose interactively. +3 tests in `test_compose_warnings.py`.

### Changed
- **N-3** `agent-composition.yaml` audit header documents the section-mapping rubric (BE/FE developer, architect/reviewer, qa, security/devops, PO/ux-designer). `backend-developer` and `frontend-developer` context filters extended with `Notes & Caveats` so project-specific gotchas reach implementers.
- **N-1** `work.md` tmux execution block recommends `--save-pane {docsDir}/phase-results/phase{N}/attempt{K}.pane.log` and documents the best-effort semantics.

### Tests
- `pytest scripts/tests/ --ignore=scripts/tests/test_meetings.py` → **431 passed** (was 425; +6 from N-1/N-3). 3 pre-existing test_meetings.py failures unchanged.

## [4.0.3] - 2026-04-20

Fast-track polish batch. 4 prompt / docstring-level items deferred from v4.0.2. All changes are text-only (no behavior change); fully revertable via `git revert`.

### Added
- **UX-1** `work.md` Progress Tracking section. Main session now creates one TaskCreate entry per Phase (0 / 1a / 1b / 2 / 3 / 4 / 4.5 / 5 / 6) and per Gate (1 / 2 / 3), with explicit state-transition rules (enter → `in_progress`, verify PASS / Gate Approve → `completed`, retry updates `activeForm` without creating a new task). Addresses M8 Attempt 3 observation of TODO compression hiding Phase-4 progress.
- **N-5** `prompts/phase3.md` "On-brand extension scope" section + PO review rubric. Codifies which UX-added elements beyond prd.md / ux-direction.md are allowed vs. forbidden (Voice/Tone preserved + reinforces existing story + self-contained vs. new flow / primary-journey change / missing-API dependency). Grey-zone items marked `<!-- [EXT_QUERY] -->` for explicit PO decision. Makes M8 Step 8.3 I-M8-P3-1 tacit rule explicit.

### Changed
- **UX-2** `work.md` tmux phase execution block documents the Bash-tool `description` convention: `"JARFIS Phase {phase_id} execution"` (first attempt) / `"JARFIS Phase {phase_id} retry attempt {K}"` (retry). Keeps background-completion notifications legible across multi-work sessions. Harness-fixed `Background command` wrapper is called out as not customizable.
- **N-6** `tmux_claude.py::kill_existing_session` docstring now notes tmux's prefix-match semantics on `-t` and confirms JARFIS's `jf-{shortId}-phase{N}` scheme with nanoid/uuid-based shortIds makes prefix collisions impossible. Includes a forward-looking reminder to re-audit if shortId generation changes to a sequential scheme.

### Tests
- `pytest scripts/tests/ --ignore=scripts/tests/test_meetings.py` → **425 passed** (v4.0.2 baseline unchanged). 3 pre-existing test_meetings.py failures unchanged.
- All 4 items are documentation / prompt-level; no Python logic touched.

## [4.0.2] - 2026-04-20

Minor hotfix batch. 6 items (SPEC-2, OBS-3, OBS-1, OBS-4, OBS-2, SPEC-1) surfaced during M8 E2E but outside v4.0.1 inline hotfix scope. No breaking changes; all backward-compatible.

### Added
- **SPEC-2** `sync.py` version drift detection. New `check_version_drift()` compares 4 sources (~/.claude/.jarfis-version, ~/.claude/scripts/jarfis/__init__.py, repo/VERSION, repo/scripts/jarfis/__init__.py). `jarfis sync` now prints pre-sync/post-sync drift warnings; new `jarfis sync --version-check` flag exits 1 on drift (CI-friendly). +11 tests in test_sync.py.
- **OBS-2** `utils.parse_json_value` over-quoting resilience. When shell preserves outer quotes (`'"[]"'`), the function now re-parses the intermediate string and returns the intended list/dict. Non-string inputs pass through unchanged. +7 tests in test_utils.py.

### Changed
- **OBS-3** `agent-composition.yaml::security-engineer` scope promoted `per-project` → `work-wide`; context `base: project` → `all-projects`. Matches phase4.md Step 1 "1 spawn" intent. Multi-scope workflows now get a single security pre-review with concatenated project-profile context (verified with 2-project fixture).
- **OBS-1** `phase2.md` api-spec.md generation condition aligned with `verify.py::_gate2_checks` fallback. New precompute fields `<has_frontend>`, `<api_spec_required>`. BE-only workflows without a frontend consumer no longer emit api-spec.md.
- **OBS-4** `state.tddEnabled` canonicalized to top-level. `jarfis-state-schema.md` example moved `tdd_enabled: false` from `phases.4` to top-level `tddEnabled: false`. Nested `phases.4.tdd_enabled` marked deprecated. `phase4.md` precompute comment reinforces no fallback to the nested location.
- **SPEC-1** `system-spec.md §5.4, §13.1` M11-1/M11-2 rewritten as "prompt-inject" approach (superseding the original "auto-load" assumption invalidated in M8). Added phase-by-phase audit table identifying where scope CLAUDE.md injection is required (Phase 4/5 ✅) vs. optional for future consideration (Phase 2/3 → v4.1 observation). Doc-only change in migration workspace; no jarfis repo commit.

### Infrastructure
- `sync.py` sync scope extended for `commands/jarfis/**` from `.md` only to `.md + .yaml + .yml`. `agent-composition.yaml` and `domains/*.yaml` now sync correctly; closes a path-level gap SPEC-2 drift detection cannot cover.
- VERSION 4.0.1 → 4.0.2; __init__.py aligned (no drift warning on fresh checkout).

### Tests
- `pytest scripts/tests/ --ignore=tests/test_meetings.py` → **425 passed** (was 419). 3 pre-existing test_meetings.py failures unchanged (tracked in v4.1 backlog).

### Migration
- v4.0.1 → v4.0.2: `/jarfis:work` next session picks up automatically. Existing in-flight workflows unaffected (schema/prompt changes are forward-compatible).

## [4.0.1] - 2026-04-19

M8 E2E 검증 과정에서 발견된 hotfix (Round 1/2/3). v4.0.0 Critical 블로커 제거 + state 스키마 v4 완전 반영.

### Fixed
- **Round 1 — Gate 1 경로/ratchet 정합** (Attempt 1, Gate 1 FAIL):
  - `verify.py::_gate1_checks` 파일 경로 → `discovery/working-backwards.md`, `discovery/prd.md`
  - `phases.1.ratchet.prd_score` 프로덕서 부재 → PRD ratchet 블록 전면 제거 (`verify.py`, `jarfis-state-schema.md`, `phase6.md workflow-metrics.tsv`, `jarfis-index.md`, `test_gate_check.py`)
  - `phase1b.md` PO 섹션 "Workspace" → "Scope" + no-numeric-prefix 규칙 명시
- **Round 2 — Gate 2 경로 + state v4 dual-emit** (Attempt 2, Gate 2 FAIL):
  - `verify.py::_gate2_checks` always_required → `planning/architecture.md`, `planning/tasks.md`, `planning/test-strategy.md`. `impact-analysis.md` 제거. `ux-direction` → `discovery/`
  - `verify.py::_phase_check` Phase 4 진입 체크 경로 정합
  - `validate.py::PHASE_ARTIFACTS` 경로 갱신
  - `verify.py::PHASE_VERIFIERS` `"1"`, `"1a"`, `"4.5"` alias 추가
  - `organization.py::cmd_detect(<project_path>)` 구현 (ancestors scan → `.jarfis-org/org-profile.md` marker)
  - `state.py::cmd_read` `ensure_ascii=False` (한글 unicode-escape 방지)
  - `state.py::cmd_init` v4 nested dual-emit: `sessionKey`, `locale`, `org`, `domain`, `design`, `responsive`, `api`, `devops`, `po_extras`, `work={name,input,docsDir,startedAt,meetings}`
- **Round 3 — M11-2 scope CLAUDE.md 자동 로드** (Attempt 3, 구조적 FAIL):
  - `phase4.md` Sub-agent common rules: `scope[$i].path/CLAUDE.md` (HIGHEST AUTHORITY) + project-profile.md 명시적 Read + marker echo 지시 주입
  - `phase5.md` Fix agent (review round cycle): 동일 지시 추가
  - 근본 원인: Claude Code Task 도구 schema에 `working_dir` 파라미터 부재 → sub-agent가 부모 cwd 상속. docsDir ≠ scope 구조에서 scope CLAUDE.md 자동 로드 불가. prompt-inject 방식으로 우회.

### Changed
- VERSION 4.0.0 → 4.0.1
- `scripts/jarfis/__init__.py` 버전 drift 수정 (M7 version bump 누락분) → 4.0.1

### Tests
- `pytest scripts/tests/` → 410 passed (+3 pre-existing test_meetings.py failures unrelated to v4.0.1 scope — tracked in v4.1 backlog)

### Migration
- v4.0.0 → v4.0.1: `/jarfis:work` 신규 세션부터 hotfix 자동 적용. 이미 진행 중인 v4.0.0 워크플로는 영향 없음 (state 스키마 backward-compatible).

## [4.0.0] - 2026-04-19

JARFIS v4: tmux orchestration + Python verification.

### Changed
- **Phase execution**: each phase (1b/2/3/4/4.5/5/6) now runs inside a dedicated tmux session; main session only does T/0/1a and the three Gates. `work.md` shrinks from 902 to ~200 lines.
- **Executor agent**: `jarfis-white` → `jarfis-foreman` (tmux-scoped orchestrator: compose invocation + sub-agent spawn + artifact merge). `jarfis-black` removed.
- **Verification**: new `verify.py` replaces the `jarfis-black` LLM gate. Exposes `gate-check`, `phase-check`, `phase-verify`, `pattern-detect` as top-level `jarfis_cli.py` subcommands. Deterministic Python checks, JSON output, machine-verifiable.
- **Agent composition**: new `agent-composition.yaml` + `jarfis_cli.py compose` CLI. Persona + domain skills + context[] (base/path/sections/importance) assembled deterministically instead of inferred by an LLM.
- **State schema**: redesigned around `scope[] + org{} + locale + baseCommit` (implement-plan A.1). Per-project agents get `working_dir = scope[i].path`; work-wide agents stay at `docsDir`. Main session is the only writer.
- **Skills**: flattened to `commands/jarfis/skills/` (10 existing + 6 new — aws-lambda, dynamodb, redis, postgres, s3, cognito). Domain yaml references skills by name only; empty `domains/{web,desktop}/skills/` dirs removed.
- **Global locale**: `~/.claude/.jarfis-locale` persists user locale across sessions (M12).

### Removed
- `jarfis-black.md` (LLM verifier) — replaced by `verify.py`.
- v3 `work.md` archived at `work-legacy.md`.
- `state gate-check` / `state phase-check` routing aliases in `state.py` (top-level subcommands only).

### Migration
- v3 `.jarfis-state.json` is **not compatible** with v4. In-flight v3 workflows should be finished under v3 (`/jarfis:work-legacy`) or re-started under v4.
- v4 entry point is `/jarfis:work`; legacy v3 remains available as `/jarfis:work-legacy` for the coexistence window.

## [3.10.1] - 2026-04-15

- implement: anti-optimization rules + phase5_agents gate-check enforcement

## [3.10.0] - 2026-04-15

- implement: add gate-check/phase-check programmatic prerequisite validation

## [3.9.0] - 2026-04-14

- implement: rename .jarfis/ to .jarfis-project/ and .jarfis-org/

## [3.8.1] - 2026-04-14

- implement: cleanup stale work-continue refs, add phase4 QA context injection note

## [3.8.0] - 2026-04-14

- implement: Phase 4+4.5+5 — meeting expert context, sys-upgrade stale refs, work-continue removed

## [3.7.0] - 2026-04-14

- implement: Phase 3 — context injection matrix, lazy loading, scope guard, handoff/agent-status injection

## [3.6.1] - 2026-04-14

- implement: Phase 2 — remove $LEARNINGS runtime loading from all prompts

## [3.6.0] - 2026-04-14

- implement: Phase 1 migration — compose() persona+skills only, preflight has_rule, project-rule.md creation

## [3.5.2] - 2026-04-13

- implement: Python scripts and hooks migrated to English — 8 source files + 3 test files + 1 hook

## [3.5.1] - 2026-04-13

- implement: Templates and domain skills migrated to English — 10 templates + 13 domain/skill files

## [3.5.0] - 2026-04-13

- implement: Core workflow + system commands migrated to English — work.md, work-continue, work-meeting, sys-implement/upgrade/distill/health/version, project-init/update, org/org-init, search/search-index/search-setup, level-check, wiki-storyboard, jarfis-index, jarfis.md, locale/locale-set (20 files)

## [3.4.0] - 2026-04-13

- implement: Agent personas migrated to English — all 20 agent files (11 senior + 9 persona) converted with $LOCALE directive

## [3.3.0] - 2026-04-13

- implement: Phase prompts migrated to English — all 9 prompt files (phase1-6, phase3-figma, phase4-5, continue-extend, wiki-loading) converted with Locale Output directive

## [3.2.0] - 2026-04-13

- implement: Locale infrastructure — locale/locale-set commands, state schema locale field, Phase 0 locale detection

## [3.1.2] - 2026-04-10

- implement: level_check.py self-contained data collection (remove collect.py dependency)

## [3.1.1] - 2026-04-10

- fix: v3.0 코드 버그 4건 수정 (web.yaml persona, desktop react 중복, fallback 매핑, agent name 충돌)

## [3.1.0] - 2026-04-10

- implement: add jarfis:level-check - AI-native developer maturity assessment

## [3.0.0] - 2026-04-10

JARFIS v3.0 Domain Plugin Architecture — 모놀리식 에이전트 → Persona + Skill + Rule 합성 체계 전환.
120회 래칫 수렴 + 11개 병렬 에이전트 분석 기반 설계.

### Added
- **Domain Pack 인프라**: _schema.yaml (Published Language), domain.py (Registry/Compose/Detect/Validate/Scaffold/Install)
- **Web Domain Pack**: web.yaml + skills 6개 (react, vue, browser, nodejs, express, biome-lint)
- **Desktop Domain Pack**: desktop.yaml + skills 4개 (rust, tauri-backend, tauri-webview, cargo-clippy)
- **Persona 9개**: 기존 모놀리식 에이전트에서 역할 정체성만 추출 (backend-developer, frontend-developer, tech-lead 등)
- **audit.py**: append-only 감사 로그 (state.json 하이브리드)
- **trace.py**: 성능 추적 (에이전트 토큰/소요시간)
- **test_architecture.py**: Leaky Abstraction 경계 검증 자동화

### Changed
- **work.md**: Phase 0에 Domain 감지, Phase 4에 `if DOMAIN` 분기 (기존 하드코딩 fallback 유지)
- **state.py**: `audit_path` optional 파라미터 추가 (기존 동작 100% 호환)
- **install.sh**: 에이전트 재귀 복사 + 도메인 팩 복사 지원
- **sys-implement.md**: Dialectic Review를 래칫 수렴 방식으로 전면 재설계 (분석→검증→이력→개선 루프)

## [2.5.7] - 2026-04-09

- implement: Fix mode test ratchet for work-continue (AutoResearch pattern)

## [2.5.6] - 2026-04-09

- implement: TDD code quality ratchet for Phase 4 (AutoResearch pattern)

## [2.5.5] - 2026-04-09

- implement: workflow metrics recording (AutoResearch results.tsv pattern)

## [2.5.4] - 2026-04-09

- implement: PRD Completeness Check ratchet (AutoResearch pattern)

## [2.5.3] - 2026-04-06

- implement: wiki_search.py MPS 메모리 크래시 수정 — CPU 강제 + MPS 메모리 차감

## [2.5.2] - 2026-04-06

- implement: SentenceTransformer 메모리 가드 추가 (4GB 임계값, macOS/Linux 지원, LLM 폴백 경고)

## [2.5.1] - 2026-04-06

- implement: wiki_search.py model.encode()에 batch_size=2 추가 (대량 청크 인덱싱 OOM 방지)

## [2.5.0] - 2026-04-03

- implement: 시맨틱 검색 확장 — meetings/works 인덱싱 + 통합 검색 CLI + /jarfis:search 커맨드

## [2.4.5] - 2026-04-03

- implement: work-meeting --prev-meeting flag for referencing previous meetings

## [2.4.4] - 2026-04-03

- implement: meeting context dynamic scan — load all .md files from meeting directory

## [2.4.3] - 2026-04-03

- implement: fix meeting context load — meeting-notes.md, tech-research.md 누락 수정

## [2.4.2] - 2026-03-31

- implement: prompts/templates/agents 경로 해석 규칙 명시 (work, work-continue, work-meeting, jarfis-index)

## [2.4.1] - 2026-03-30

- implement: MIT → AGPL-3.0 라이선스 변경

## [2.4.0] - 2026-03-30

- implement: Phase 4 TDD 도입 — Step 4-0.5 테스트 선행 작성 + BE/FE Green Phase + Phase 5 경량화

## [2.3.4] - 2026-03-30

- implement: harness 품질 개선 — Phase 4 Agent Status 주입, Fix 원설계 참조, Extend QA 전략, Artifact Loading Checklist

## [2.3.3] - 2026-03-30

- upgrade: Medistream 학습 적용 — FE 21건, TL 4건

## [2.3.2] - 2026-03-30

- upgrade: JarfisOrg 학습 적용 — FE 3건, PO 2건, Architect 2건, project-context 2건

## [2.3.1] - 2026-03-27

- implement: Phase 3 MCP 도구 가용성 체크 Step 추가

## [2.3.0] - 2026-03-27

- implement: 디자이너 유무 분기, 복수 Figma 페이지 병렬, reference.png 통일, FE Design Contract, Phase 5 이중 비교

## [2.2.0] - 2026-03-26

- implement: Phase 3 Figma-Driven Design Path 분기 추가 (Framelink MCP + 에셋 다운로드 + 토큰맵 + UX 재현 + 리뷰 루프 max 20회)

## [2.1.3] - 2026-03-24

- implement: fix test isolation leak — TestOrg cleanup + jarfis_env usage

## [2.1.2] - 2026-03-24

- implement: fix sync to include scripts/tests/ directory

## [2.1.1] - 2026-03-24

- implement: fix venv detection bug + search-index batch all orgs

## [2.1.0] - 2026-03-24

- implement: add /jarfis:search-index command

## [2.0.1] - 2026-03-24

- implement: rename wiki-setup → search-setup

## [2.0.0] - 2026-03-24

JARFIS v2 LTS — v1.11.3에서 전면 재설계된 AI IT Team Workflow Orchestration 시스템.

### Agent 고도화
- 6개 에이전트(PO, UX, QA, Security, TL, Architect) v2 업그레이드 — Mindset & Disposition, Judgment Framework, Escalation Criteria 섹션 추가
- 에이전트 보호 규칙: 화이트리스트 방식 (`## Learned Rules`만 수정 가능, 나머지 전체 읽기 전용)
- Dialectic Review 시스템: Advocate/Critic 에이전트 토론 게이트 (implement, upgrade, distill)
- Learning 2-Layer 분리: `[universal]` → agent Learned Rules, `[project]` → project-context.md

### Organization & Wiki
- Org 개념 도입: org-profile.md, wiki/ 구조, 프로젝트 횡단 지식 관리
- Wiki Semantic Search: sentence-transformers bge-m3 기반 시맨틱 검색
- Org 자동 등록: preflight 시 Org 감지 → orgs.json 자동 등록 + 프로젝트 테이블 자동 추가
- Org 자동 발견: /jarfis:org 실행 시 등록된 Org의 형제 디렉토리 스캔

### 산출물 디렉토리 재구조화
- `.local/workspace` → `.personal/orgs/{org_name}/` Org별 워크스페이스 분리
- orgs.json 레지스트리 + `_standalone` 폴더 (Org 미등록 사용자)
- Org별 learnings.md 분리
- `.jarfis-works-dir` → `.jarfis-personal-dir` 설정 파일 변경

### 커맨드 체계
- resource-verb 패턴 통일: continue→work-continue, meeting→work-meeting, implement→sys-implement, upgrade→sys-upgrade, distill→sys-distill, version→sys-version, health→sys-health, wiki-search-setup→wiki-setup, storyboard→wiki-storyboard
- 커맨드 보호 규칙: distill은 커맨드 파일 분석만, 수정은 sys-implement만 가능
- /jarfis:org 전체 Org 목록 표시 (orgs.json 기반 + CWD 하이라이트)
- /jarfis:wiki-setup 원스텝 설치 커맨드

### 워크플로우 강화
- Phase 3 PO→Designer 핸드오프: ux-direction.md → HTML 시안 → 피드백 루프
- Phase 5 UX Designer 리뷰: playwright 시각적 비교 기반 디자인 QA
- Gate 1/2/3 명시적 AskUserQuestion 블록
- `.jarfis-state.json`에 status + key_decisions 필드 추가

### Python CLI & 테스트
- Bash → Python 마이그레이션: 8개 모듈 + jarfis_cli.py 디스패처
- pytest 테스트 176개 (전 모듈 커버, TDD 규칙 enforce)
- `get_workspace_dir` → `get_org_dir` 의미론적 리네이밍
- install.sh .personal 구조 마이그레이션 지원

### Infrastructure
- 4개 Hook 인프라: PreCompact, Safety(PreToolUse), Quality Gate(PostToolUse), SessionStart
- 9 Principles 문서 (PHILOSOPHY.md)
- Git-based versioning + Semantic Versioning

## [1.11.3] - 2026-03-19

- implement: upgrade.md 잔존 Learned Workflow Patterns 참조 제거 (F-1)

## [1.11.2] - 2026-03-19

- implement: 9 Principles 검수 반영 — upgrade.md Workflow Patterns SSOT 변경, PHILOSOPHY.md Principle Zero + 트레이드오프 추가

## [1.11.1] - 2026-03-19

- implement: 미비점 수정 (정본 표기 통일, index 잔여 텍스트 제거, version.py regex 보강)

## [1.11.0] - 2026-03-19

- implement: jarfis validate 명령어 + jarfis_check.sh 구조 검증 스크립트

## [1.10.2] - 2026-03-19

- implement: health.md 외부 스크립트 가드 보강 + Hook 주석 영어 통일

## [1.10.1] - 2026-03-19

- implement: upgrade.md 3블록 독립 분리 + Dialectic Review 정본 참조 패턴

## [1.10.0] - 2026-03-19

- implement: state validate 서브커맨드 추가 + 미팅 라운드 카운터 상태 관리

## [1.9.12] - 2026-03-19

- implement: prompts Task prompt 레이블 통일 + install.sh TTY 자동 감지

## [1.9.11] - 2026-03-19

- implement: work.md Learned Workflow Patterns 제거 (~500tok 절감, jarfis-learnings.md가 SSOT)

## [1.9.10] - 2026-03-19

- implement: 에이전트 모델 frontmatter 통일 (QA/Security → opus) + 모델 라우팅 SSOT 강화

## [1.9.9] - 2026-03-19

- implement: version bump 시 __init__.py 버전도 함께 갱신하도록 개선

## [1.9.8] - 2026-03-18

- upgrade: API 마이그레이션 학습 적용 (FE 3건, QA 3건, WF 3건)

## [1.9.7] - 2026-03-16

- upgrade: 학습 적용 — FE 7건(API 전환 패턴), WF 4건(전환 워크플로우)

## [1.9.6] - 2026-03-12

- implement: senior-ux-designer 전면 개편 (브랜드 디자인 + SVG 에셋 제작 + 디자인 토큰 + 비평 루프)

## [1.9.5] - 2026-03-12

- implement: project-update 변경 감지를 commit hash 기반으로 개선

## [1.9.4] - 2026-03-12

- upgrade: 학습 적용 (FE 5건, TL 2건, WF 3건)

## [1.9.3] - 2026-03-11

- implement: agent model routing 통일 (UX/QA/Security → opus)

## [1.9.2] - 2026-03-11

- implement: implement/distill/upgrade 완료 시 commit+push 명령어 제공

## [1.9.1] - 2026-03-11

- implement: LICENSE 파일 추가 + README Philosophy 링크

## [1.9.0] - 2026-03-11

- implement: Hook infrastructure (safety/quality-gate/session-start) + workflow handoff + learning candidates

## [1.8.4] - 2026-03-11

- implement: remove deprecated sh scripts replaced by py modules

## [1.8.3] - 2026-03-11

- implement: 명령어 .md 파일 스크립트 참조를 .sh → Python CLI(jarfis_cli.py)로 일괄 전환

## [1.8.2] - 2026-03-11

- implement: 스텝 강제 실행 규칙, 수정 위치 명시, 동기화 방향 경고, 스텝 간 흐름 연결 강화

## [1.8.1] - 2026-03-11

- implement: CHANGELOG 버전 범프 로직 개선 — [Unreleased] → [X.Y.Z] 릴리스 섹션 자동 전환

## [1.8.0] - 2026-03-11

### Changed
- **Bash → Python 마이그레이션**: 9개 Bash 스크립트 중 8개를 Python stdlib-only 패키지로 전환
- **jarfis-detect-project.sh**: `grep` 기반 JSON 파싱 → `json.load()` 정확 파싱
- **jarfis-state.sh**: Bash + `python3 -c` 인라인 혼합 → 순수 Python 모듈
- **workspace 경로 해석**: 4개 스크립트에 중복되던 로직을 `utils.py`로 통합
- **jarfis-sync.sh + jarfis-readme-update.sh**: `sync.py`로 병합 (`--readme-only` 플래그)
- **install.sh**: Python 패키지(`scripts/jarfis/`, `jarfis_cli.py`) 백업/설치 로직 추가

### Added
- `scripts/jarfis/` Python 패키지 (8 모듈 + utils)
- `scripts/jarfis_cli.py` CLI 디스패처
- `PHILOSOPHY.md` — JARFIS 9 Principles 문서

## [1.7.1] - 2026-03-11

### Changed
- JARFIS 약어를 **Just A Rather Foolish Integration System**으로 확정
- README.md 현행화: Artifacts 경로 `.local/` 반영, python3 요구사항 추가, jq optional 변경, (NEW) 태그 제거

## [1.7.0] - 2026-03-11

### Changed
- **Data 경로 통합**: workspace/learnings를 `{JARFIS_SOURCE}/.local/`로 이동
- **install.sh**: `.local/` 마이그레이션 로직 추가
- **jarfis-state.sh**: 환경변수 방식으로 변경 — single quote 인젝션 취약점 해결
- **jarfis-pre-compact.sh**: jq → python3 → 기본값 3단계 fallback
- **statusline-command.sh**: jq → python3 → 기본값 3단계 fallback

### Added
- flat 디렉토리 구조 전환 + 미팅 선택 기능 + source_meeting 필드
- README.md 자동 갱신 기능

## [1.6.0] - 2026-03-11

### Changed
- **workspace 경로**: `~/.jarfis-workspace` → `~/.jarfis/workspace`로 통합
- **learnings 경로**: `~/.claude/jarfis-learnings.md` → `~/.jarfis/jarfis-learnings.md`로 이동

## [1.5.0] - 2026-03-11

### Changed
- **디렉토리 구조 flat 전환**: `meetings/{YYYYMMDD}/{name}/` → `meetings/{YYYYMMDD}-{name}/`

### Added
- **jarfis-recent-meetings.sh**: 최근 미팅 N개 JSON 출력 스크립트

## [1.4.2] - 2026-03-11

### Added
- **jarfis-readme-update.sh**: README.md 섹션 자동 갱신

## [1.4.1] - 2026-03-10

### Added
- **Batch 1+2 스크립트**: jarfis-measure.sh, jarfis-version-bump.sh, jarfis-preflight.sh, jarfis-state.sh, jarfis-detect-project.sh

## [1.3.5] - 2026-03-10

### Changed
- Distill: phase4/phase2/continue/meeting/phase1/phase5/work.md 토큰 절감 (~3,596tok)

## [1.3.4] - 2026-03-10

### Fixed
- work.md: distill 압축 시 누락된 규칙 2건 복원

## [1.3.3] - 2026-03-10

### Changed
- Distill: work.md ~5,000tok 절감, continue.md ~530tok, agent 규칙 추상화

### Added
- prompts/continue-extend.md: Extend 모드 프롬프트 외부화

## [1.3.2] - 2026-03-10

### Added
- distill.md: 에이전트 추상화 분석 (abstract-rule, deduplicate-agent-rule)

## [1.3.1] - 2026-03-10

### Added
- distill.md: 표현 밀도 분석 (condense-section, compress-expression)

## [1.3.0] - 2026-03-10

### Added
- install.sh: Workspace 디렉토리 설정
- work.md: Workspace Detection (AskUserQuestion)

## [1.2.6] - 2026-03-10

### Changed
- Distill: 에이전트 description 축소 (~3,294tok 절감)

## [1.2.5] - 2026-03-10

### Changed
- Learnings 적용: 27개 학습 항목 반영

## [1.2.4] - 2026-03-10

### Changed
- Repo 동기화 자동화: jarfis-sync.sh

## [1.2.3] - 2026-03-10

### Added
- Continue 프로젝트 프로필 로드

## [1.2.2] - 2026-03-10

### Added
- Continue Agent Model Routing

## [1.2.1] - 2026-03-10

### Added
- Continue 플래그 지원 (--workflow, --mode)

## [1.2.0] - 2026-03-10

### Added
- **Continue Command** (`/jarfis:work-continue`): Fix/Extend 모드

## [1.1.1] - 2026-03-10

### Changed
- jarfis.md 도움말에 Dialectic Review 반영

## [1.1.0] - 2026-03-10

### Added
- **Dialectic Review System**: Advocate/Critic 에이전트
- **Learning 2-Layer 분리**: universal vs project-specific

## [1.0.7] - 2026-03-05

### Added
- Agent Learned Rules 머지 + work.md 강화

## [1.0.6] - 2026-03-04

### Changed
- 산출물 디렉토리 `./jarfis/` → `./.jarfis/`

## [1.0.5] - 2026-03-04

### Fixed
- claude-cleanup.sh bash set -u 버그 수정

## [1.0.4] - 2026-03-04

### Changed
- README.md 소개 섹션 개선

## [1.0.3] - 2026-03-04

### Changed
- README.md public release 용 재작성

## [1.0.2] - 2026-03-04

### Added
- Repo 동기화 step (implement/upgrade/distill)

## [1.0.1] - 2026-03-04

### Removed
- /jarfis:pack command

## [1.0.0] - 2026-03-04

### Added
- Git-based version management with Semantic Versioning
- install.sh, /jarfis:sys-version, VERSION, CHANGELOG.md

### Migration
- Previous v17 (Ouroboros) → 1.0.0 (first Git-tracked release)
