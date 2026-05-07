# JARFIS Agent — Skill & Persona Registry

> **Locale**: All user-facing output must be presented in $LOCALE language. Internal instructions: English.

Manage JARFIS agent skills (Context7-aware) and inspect composed personas.
**Read-only inspection + manual approval for any registry write.**

User request: $ARGUMENTS

---

## Subcommand routing

Parse `$ARGUMENTS` as `<subcommand> <action> [args...]`:

- `skill list`
- `skill add <name> [--library <ctx7-id>] [--bind-framework <fw>] [--apply]`
- `skill update <name>`
- `skill remove <name> [--apply]`
- `persona list`

If `$ARGUMENTS` is empty or unrecognized, print the usage banner and exit:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  /jarfis:agent — Skill & Persona Registry
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Subcommands:
    skill list                                         Show registered skills
    skill add <name> [--library <id>] [--bind-framework <fw>] [--apply]
                                                       Create new skill (Context7-aware)
    skill update <name>                                Refresh existing skill
    skill remove <name> [--apply]                      Delete skill (refs surfaced)

    persona list                                       Show all composed personas

  Notes:
    - skill add/remove default to dry-run. Add --apply to commit.
    - Framework binding is suggested-only — agent-composition.yaml is
      never auto-edited (manual approval required).
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## skill list

Run:
```bash
python3 ~/.claude/scripts/jarfis_cli.py agent skill list
```

Render the JSON as a table:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Registered Skills (N)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  {name}            {one-line description}
  ...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Sort alphabetically. If a skill has no `> ` summary line, show `(no description)`.

---

## skill add

1. **Validate name format** — the Python script enforces `^[a-z][a-z0-9-]*$`, length ≤ 40. If exit code ≠ 0, surface the error JSON to the user and stop.

2. **If `--library <id>` was given** — fetch Context7 docs first:
   - Call `mcp__context7__resolve-library-id` with the id to get the canonical library ID.
   - Call `mcp__context7__query-docs` with focused topic queries:
     - "Common Pitfalls"
     - "Anti-patterns"
     - "Version compatibility / breaking changes"
   - Hold the docs summary in memory for step 4.

3. **Run with `--apply`** to write the skeleton:
   ```bash
   python3 ~/.claude/scripts/jarfis_cli.py agent skill add <name> [--library <id>] [--bind-framework <fw>] --apply
   ```

4. **If Context7 docs were fetched in step 2**: open the just-written skeleton with `Edit` and replace the `- TODO` placeholders with **checkpoint-style** entries derived from Context7 (NOT verbatim doc text — checkpoint style only per `~/.claude/commands/jarfis/templates/skill-template.md:7,11-13`):
   - ❌ Don't summarize official docs (token waste — search is available).
   - ✅ "흔히 놓치는 함정" / "결정 휴리스틱" / "반(反)패턴" / "버전·환경 의존성".
   - Aim for 5–10 bullets total across 5 sections, ~1–2 KB.

5. **If `--bind-framework` was used**: surface the `composition_yaml_diff` from the script output to the user with a manual-edit hint:
   ```
   To activate, edit ~/.claude/commands/jarfis/agent-composition.yaml under
   `extra_skills_by_framework:` and set:
       <suggested mapping>

   After editing, run:
       python3 ~/.claude/scripts/jarfis_cli.py compose --validate
   ```
   Do NOT auto-edit `agent-composition.yaml` — single-writer rule.

6. **Final banner**: created path + suggested next step (e.g., "Verify via `/jarfis:agent skill list` or open with your editor.").

---

## skill update

1. Run:
   ```bash
   python3 ~/.claude/scripts/jarfis_cli.py agent skill update <name>
   ```
   This locates the file, returning `path` + `size_bytes` + `mtime`.

2. AskUserQuestion:
   - **Refresh from Context7?** — fetch latest docs and rewrite the file in checkpoint style.
   - **Open in editor manually** — surface the path; user edits with their tool of choice.
   - **Cancel** — do nothing.

3. If "Refresh from Context7":
   - Ask for the Context7 library ID (or infer from existing `<!-- Context7 ID: ... -->` comment if present).
   - Call `mcp__context7__resolve-library-id` + `mcp__context7__query-docs`.
   - Use `Edit` to update the file's body (preserve title + 5-section structure).
   - Confirm the diff with the user before applying.

---

## skill remove

1. **Default dry-run**:
   ```bash
   python3 ~/.claude/scripts/jarfis_cli.py agent skill remove <name>
   ```
   Surfaces the file path + every reference to `<name>` in:
   - `~/.claude/commands/jarfis/agent-composition.yaml`
   - `~/.claude/commands/jarfis/domains/*.yaml`

2. **AskUserQuestion**: confirm deletion (Yes / No). Show the references list so the user understands the manual cleanup required.

3. **On Yes** — run with `--apply`:
   ```bash
   python3 ~/.claude/scripts/jarfis_cli.py agent skill remove <name> --apply
   ```
   Then surface the `manual_cleanup_required` list as a checklist for the user:
   ```
   The skill file was removed, but these references remain — please clean up manually:
     - {file}:{line}  {content}
     ...
   ```

---

## persona list

Run:
```bash
python3 ~/.claude/scripts/jarfis_cli.py agent persona list
```

Render the JSON as a table:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  JARFIS Personas (N agents)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  {agent_name}       persona={persona}  scope={scope}  skills_from_domain={Y/N}  context={count}  model={model}
  ...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Sort alphabetically by `agent_name`. Compact `skills_from_domain: true` → `Y`, `false` → `N`.

This is read-only inspection. To modify a persona, edit `~/.claude/commands/jarfis/agent-composition.yaml` directly.
