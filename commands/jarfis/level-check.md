# JARFIS Level Check — AI-Native Developer Maturity Assessment

> **Locale**: All user-facing output must be presented in $LOCALE language. Internal instructions: English.

> Assess AI-native developer maturity using a research-based framework (AIDMM + AI-MM SET + Anthropic Agentic Coding Report).

---

## Execution Flow

### Step 1: Automated Collection (Local Desktop Survey)

Run the JARFIS collection script to gather data. No external dependencies.

```bash
python3 ~/.claude/scripts/jarfis/level_check.py
# Or full session analysis (no 30-day limit):
python3 ~/.claude/scripts/jarfis/level_check.py --all
```

Collected items (JSON output):
- `sessions`, `avg_prompts` — session count, average prompts per session
- `tools` — call count per tool (Bash, Read, Edit, Agent, etc.)
- `skills.total`, `skills.usage` — skill file count + usage count per skill
- `mcp.total`, `mcp.servers` — MCP server count + call count per server
- `agents.custom`, `agents.personas`, `agents.dialectic`, `agents.delegations`, `agents.types` — agent details
- `hooks.total`, `hooks.events`, `hooks.names` — hook details
- `memory.total`, `memory.types` — memory count + type distribution
- `claude_md.total_lines`, `claude_md.files` — total CLAUDE.md lines across projects
- `models` — model usage ratios
- `permissions.mode` — permission mode
- `orchestration.jarfis`, `orchestration.omc`, `orchestration.superclaude`, `orchestration.custom` — orchestration system detection
- `domains.packs`, `domains.skills` — domain pack/skill count
- `wiki` — wiki system presence
- `tests` — test function count
- `plugins` — plugin count

Store the automated collection results in `$AUTO_DATA` and show the user a summary:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  JARFIS Level Check — Automated Collection Complete
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Sessions: {N} | Avg prompts: {N}/session
🔧 Skills: {N} | Hooks: {N} | MCP: {N}
🤖 Agents: {N} types ({N} delegations)
🧠 Memory: {N}
📁 CLAUDE.md: {N} lines (total across projects)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Proceed to Step 2

### Step 2: Manual Input (Interview)

Use AskUserQuestion to ask about items that cannot be determined from automated collection. **Present all questions at once** so the user can answer them in one go.

```
Please answer the following 7 questions. You can simply write the number and a brief answer.

1. Which stages of the SDLC do you use AI for?
   a) Coding only  b) Coding + testing  c) Planning through testing  d) Planning through deployment  e) Entire lifecycle including monitoring

2. Have you designed and operated custom agents?
   a) None  b) 1-3  c) 4-10  d) 10+  e) Built an orchestration system

3. To what degree do you delegate autonomous work to AI agents?
   a) No delegation  b) Single-task delegation  c) Multi-step delegation  d) Parallel agents  e) End-to-end autonomous

4. How do you verify AI output quality? (multiple selections allowed)
   a) Manual review  b) Automated tests  c) CI/CD integration  d) Dialectic review (pro/con)  e) Automated learning accumulation

5. How do you maintain knowledge across sessions? (multiple selections allowed)
   a) Not maintained  b) Memory/CLAUDE.md  c) Domain encoding (skills/templates)  d) Wiki/documentation system  e) Automated retrospective + learning loop

6. Do you have a self-improvement loop where AI improves AI?
   a) None  b) Manual prompt refinement  c) AI-assisted prompt optimization  d) AI modifies its own system  e) Autonomous evolution loop

7. Do you operate AI-native processes at the team/organization level?
   a) Individual only  b) Shared within team  c) Team standard  d) Organization-wide standard  e) Non-engineers also use it
```

Proceed to Step 3

### Step 3: Score Calculation

Evaluate on a 10-point scale across 7 dimensions. Derive scores by combining **automated collection data + manual input answers**.

#### Evaluation Framework

| Dimension | Weight | Criteria |
|-----------|--------|----------|
| **D1. AI Literacy & Tool Adoption** | 10% | Model selection strategy, tool count, usage frequency, bypass ratio, session depth |
| **D2. Workflow & SDLC Integration** | 20% | Interview Q1 + automated data (skill usage patterns, SDLC coverage) |
| **D3. Agent Design & Orchestration** | 25% | Interview Q2+Q3 + automated data (agent count/types/delegation count) |
| **D4. Tooling Infrastructure** | 15% | Automated data (MCP, hooks, skills, commands, CLAUDE.md line count) |
| **D5. Quality & Safety Governance** | 15% | Interview Q4 + automated data (safety/quality-related hooks, test agents) |
| **D6. Knowledge Persistence** | 10% | Interview Q5 + automated data (memory count, memory type distribution) |
| **D7. Meta-Engineering** | 5% | Interview Q6 + automated data (sys-implement usage count, self-modification patterns) |

#### Scoring Guide (0-10 per dimension)

**D1. AI Literacy & Tool Adoption**
| Score | Criteria |
|-------|----------|
| 0-2 | No AI tools or basic ChatGPT only |
| 3-4 | Basic Copilot/Claude usage, sessions <10 |
| 5-6 | 100+ sessions, 2-3 MCP servers, prompts <20/session |
| 7-8 | 100+ sessions, 5+ MCP servers, 30+ prompts/session, strategic model selection |
| 9-10 | 200+ sessions, 7+ MCP servers, 50+ prompts/session, 90%+ bypass, top-tier model usage |

**D2. Workflow & SDLC Integration**
| Score | Criteria |
|-------|----------|
| 0-2 | No AI usage or coding assistance only |
| 3-4 | AI used for coding + testing |
| 5-6 | AI used from planning through testing, partial automation |
| 7-8 | AI integrated from planning through deployment, SDLC pipeline built |
| 9-10 | Entire SDLC operated as AI workflows, declarative process definitions |

**D3. Agent Design & Orchestration**
| Score | Criteria |
|-------|----------|
| 0-2 | No agent usage |
| 3-4 | Basic agent usage (general-purpose) |
| 5-6 | 1-3 custom agents, single-task delegation |
| 7-8 | 4-10 custom agents, parallel delegation, persona design |
| 9-10 | 10+ agents, orchestration system, dialectic review, end-to-end autonomous |

**D4. Tooling Infrastructure**
| Score | Criteria |
|-------|----------|
| 0-2 | Default settings only |
| 3-4 | CLAUDE.md written, basic MCP integration |
| 5-6 | Custom skills created, 3+ hooks, 3+ MCP servers |
| 7-8 | Domain skills, template system, CI integration, 500+ lines in CLAUDE.md |
| 9-10 | Full-stack infra (30+ skills, 5+ hooks, 7+ MCP, domain packs, 50+ commands) |

**D5. Quality & Safety Governance**
| Score | Criteria |
|-------|----------|
| 0-2 | Accept AI output without verification |
| 3-4 | Manual review only |
| 5-6 | Automated tests + CI integration |
| 7-8 | Safety hooks, quality gates, structured verification loops |
| 9-10 | Dialectic review (pro/con), automated learning accumulation, ratchet convergence, 20+ round verification |

**D6. Knowledge Persistence**
| Score | Criteria |
|-------|----------|
| 0-2 | No cross-session knowledge retention |
| 3-4 | CLAUDE.md only |
| 5-6 | 10+ memories, per-project CLAUDE.md |
| 7-8 | Domain encoding (skills/templates), documentation system |
| 9-10 | Wiki system, automated retrospective + learning loop, 25+ memories, cross-session continuity |

**D7. Meta-Engineering**
| Score | Criteria |
|-------|----------|
| 0-2 | AI used as a tool only |
| 3-4 | Manual prompt refinement |
| 5-6 | AI-assisted prompt/config optimization (distill, etc.) |
| 7-8 | AI modifies its own system (sys-implement) |
| 9-10 | Autonomous evolution loop, recursive structure where AI builds systems for AI |

#### Weighted Sum

```
Total = D1×0.10 + D2×0.20 + D3×0.25 + D4×0.15 + D5×0.15 + D6×0.10 + D7×0.05
```

Organization bonus (Interview Q7):
- a) Individual only → +0.0
- b) Shared within team → +0.1
- c) Team standard → +0.2
- d) Organization-wide → +0.3
- e) Non-engineers also use it → +0.5

**Final Score = min(Total + Organization bonus, 10.0)**

Proceed to Step 4

### Step 4: Output Results

#### Level System

| Level | Title | Score Range | AIDMM Mapping | AI-MM SET Mapping |
|-------|-------|------------|---------------|-------------------|
| Lv.0 | Human-Only | 0 - 1.0 | Level 0 | - |
| Lv.1 | AI-Curious | 1.0 - 3.0 | Level 0-1 | Exploratory |
| Lv.2 | AI-Assisted | 3.0 - 5.0 | Level 1 | Applied |
| Lv.3 | AI-Collaborative | 5.0 - 6.5 | Level 2 | Standardized |
| Lv.4 | AI-Delegated | 6.5 - 8.0 | Level 3 | Strategic |
| Lv.5 | AI-Orchestrator | 8.0 - 9.5 | Level 3-4 | Strategic+ |
| Lv.6 | AI-Native | 9.5 - 10.0 | Level 4 | Transformational |

#### Output Format

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  JARFIS Level Check — AI-Native Maturity
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Lv.{N} {title}    {score}/10
  {progress bar 20 chars}  {percent}%

  ┌─ Dimension Scores ───────────────────────────┐
  │ D1 Tool Adoption      {score}/10  {bar}      │
  │ D2 SDLC Integration   {score}/10  {bar}      │
  │ D3 Agent Orchestration {score}/10  {bar}      │
  │ D4 Tooling Infra       {score}/10  {bar}      │
  │ D5 Quality Governance  {score}/10  {bar}      │
  │ D6 Knowledge Persist   {score}/10  {bar}      │
  │ D7 Meta-Engineering    {score}/10  {bar}      │
  └─────────────────────────────────────────────┘

  Organization bonus: +{N} ({level})

  📊 Automated collection summary:
     Sessions {N} | Agents {N} types {N} delegations | MCP {N}
     Skills {N} | Hooks {N} | Memory {N}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Ref: AIDMM (DEV Community) · AI-MM SET (Gigacore)
  Ref: Anthropic 2026 Agentic Coding Trends Report
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

#### Next Level Guide

Provide 1-3 specific suggestions for advancing to the next level:

```
  🎯 To reach Lv.{N+1} {next title}:
     1. {specific suggestion}
     2. {specific suggestion}
     3. {specific suggestion}
```

Examples:
- Lv.2 to 3: "Add CLAUDE.md to your project and integrate at least 2 MCP servers"
- Lv.3 to 4: "Create custom agents and delegate repetitive tasks to them"
- Lv.4 to 5: "Build an SDLC pipeline with multi-agent orchestration"
- Lv.5 to 6: "Standardize AI-native processes across your entire team/organization"
