---
name: jarfis:locale-set
description: "JARFIS Locale Set — locale 설정 변경"
---

# JARFIS Locale Set — locale 설정

사용자 요청: $ARGUMENTS

## 사용법

```
/jarfis:locale-set <language_code>
```

지원 언어: `ko` (Korean), `en` (English), `ja` (Japanese)

## 실행 로직

1. `$ARGUMENTS`에서 언어 코드를 파싱한다.
   - 유효한 코드: `ko`, `en`, `ja`
   - 유효하지 않은 코드 → 에러 메시지: `"Unsupported locale: {input}. Supported: ko, en, ja"`
   - 인자 없음 → 현재 locale 표시 (`/jarfis:locale`과 동일 동작)

2. 현재 워크스페이스에서 `.jarfis-state.json`을 찾는다:
   - CWD 또는 가장 최근 워크플로우의 `$DOCS_DIR`

3. `.jarfis-state.json`이 존재하면:
   ```bash
   python3 ~/.claude/scripts/jarfis_cli.py state set "$STATE_FILE" "locale" "$LANGUAGE_CODE"
   ```

4. `.jarfis-state.json`이 없으면:
   - 메시지 출력: `"No active JARFIS workflow. Locale will be applied on next /jarfis:work execution."`
   - 이 경우 설정은 저장되지 않지만, 다음 `/jarfis:work` 실행 시 Phase 0에서 auto-detect 된다.

5. 확인 메시지 출력:
   ```
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     JARFIS Locale Updated
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     Language:  {code} ({language_name})
     Internal:  English (fixed)

     All subsequent output will be in {language_name}.
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   ```

## 동작 범위

- locale 변경은 **현재 워크플로우**에만 적용된다.
- 다음 `/jarfis:work` 실행 시 Phase 0에서 다시 auto-detect 또는 재설정.
- JARFIS 내부 추론/지시 언어는 항상 English (변경 불가).
