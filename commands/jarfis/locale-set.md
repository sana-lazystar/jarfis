---
name: jarfis:locale-set
description: "JARFIS Locale Set — Change locale setting"
---

# JARFIS Locale Set — Change Locale
<!-- locale: en -->

User request: $ARGUMENTS

## Usage

```
/jarfis:locale-set <language_code>
```

Supported languages: `ko` (Korean), `en` (English), `ja` (Japanese)

## Execution Logic

1. Parse the language code from `$ARGUMENTS`.
   - Valid codes: `ko`, `en`, `ja`
   - Invalid code: show error message `"Unsupported locale: {input}. Supported: ko, en, ja"`
   - No argument: display the current locale (same behavior as `/jarfis:locale`)

2. Look for `.jarfis-state.json` in the current workspace:
   - CWD or the most recent workflow's `$DOCS_DIR`

3. If `.jarfis-state.json` exists:
   ```bash
   python3 ~/.claude/scripts/jarfis_cli.py state set "$STATE_FILE" "locale" "$LANGUAGE_CODE"
   ```

4. If `.jarfis-state.json` does not exist:
   - Display message: `"No active JARFIS workflow. Locale will be applied on next /jarfis:work execution."`
   - In this case the setting is not persisted, but it will be auto-detected in Phase 0 on the next `/jarfis:work` run.

5. Display confirmation message:
   ```
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     JARFIS Locale Updated
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     Language:  {code} ({language_name})
     Internal:  English (fixed)

     All subsequent output will be in {language_name}.
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   ```

## Scope of Effect

- Locale changes apply only to the **current workflow**.
- On the next `/jarfis:work` run, locale will be auto-detected or reset in Phase 0.
- JARFIS internal reasoning/instruction language is always English (not configurable).
