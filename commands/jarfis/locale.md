---
name: jarfis:locale
description: "JARFIS Locale — 현재 locale 설정 조회"
---

# JARFIS Locale — 현재 locale 조회

현재 JARFIS 워크플로우의 locale 설정을 표시합니다.

## 실행 로직

1. 현재 워크스페이스에서 `.jarfis-state.json`을 찾는다:
   - CWD에 `.jarfis-state.json`이 있으면 사용
   - 없으면 `$DOCS_DIR/.jarfis-state.json` 탐색 (가장 최근 워크플로우)

2. `.jarfis-state.json`이 존재하고 `locale` 필드가 있으면:
   ```
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     JARFIS Locale Configuration
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     Language:  {locale} ({language_name})
     Internal:  English (fixed)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   ```

3. `.jarfis-state.json`이 없거나 `locale` 필드가 없으면:
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

## 언어 코드 매핑

| 코드 | 언어명 |
|------|--------|
| `ko` | Korean |
| `en` | English |
| `ja` | Japanese |
