---
name: jarfis:locale
description: "JARFIS Locale — View current locale setting"
---

# JARFIS Locale — View Current Locale
<!-- locale: en -->

Displays the current locale setting for the JARFIS workflow.

## Execution Logic

1. Look for `.jarfis-state.json` in the current workspace:
   - Use `.jarfis-state.json` if it exists in CWD
   - Otherwise, search `$DOCS_DIR/.jarfis-state.json` (most recent workflow)

2. If `.jarfis-state.json` exists and contains a `locale` field:
   ```
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     JARFIS Locale Configuration
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     Language:  {locale} ({language_name})
     Internal:  English (fixed)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   ```

3. If `.jarfis-state.json` does not exist or lacks a `locale` field:
   ```
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     JARFIS Locale Configuration
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     Language:  ko (Korean) — default
     Internal:  English (fixed)

     No active workflow.
     Use /jarfis:locale-set to change.
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   ```

## Language Code Mapping

| Code | Language |
|------|----------|
| `ko` | Korean |
| `en` | English |
| `ja` | Japanese |
