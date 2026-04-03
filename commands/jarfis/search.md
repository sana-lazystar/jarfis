# JARFIS Search — 시맨틱 검색

> meetings, works, wiki를 시맨틱 검색합니다.

사용자 요청: $ARGUMENTS

---

## 플래그 파싱

`$ARGUMENTS`에서 플래그와 쿼리를 분리한다:

| 플래그 | 의미 |
|--------|------|
| `--meetings` | meetings만 검색 |
| `--works` | works만 검색 |
| `--wiki` | wiki만 검색 |
| (없음) | 전체 검색 (기본) |

복수 플래그 가능: `--meetings --works 검색어` → meetings + works만 검색

**순서**: 플래그가 먼저, 쿼리가 뒤. 예: `/jarfis:search --works 교환반품`

## 실행

### 1. 쿼리 추출

플래그를 제거한 나머지를 `$QUERY`로 사용한다.
`$QUERY`가 비어있으면 AskUserQuestion으로 검색어를 입력받는다.

### 2. scope 결정

- 플래그 없음 → `all`
- `--meetings` → `meetings`
- `--works` → `works`
- `--wiki` → `wiki`
- 복수 플래그 → 해당 scope들만 검색 (CLI를 각각 호출 후 결과 합산)

### 3. 검색 실행

```bash
python3 ~/.claude/scripts/jarfis_cli.py search {scope} "{$QUERY}" --top-k 10 --pretty
```

복수 scope인 경우 (`--meetings --works` 등):
```bash
# 각각 JSON으로 호출하여 결과 합산
python3 ~/.claude/scripts/jarfis_cli.py search meetings "{$QUERY}" --top-k 5
python3 ~/.claude/scripts/jarfis_cli.py search works "{$QUERY}" --top-k 5
```
결과를 score 순으로 합산하여 사람 읽기용으로 표시.

### 4. 결과 표시

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  검색: "{$QUERY}"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  1. [meetings] 20260326-API-GET-Tanstack-도입/summary.md
     score: 0.87  |  section: 핵심 결정사항
     TanStack Query 도입하여 GET API를...

  2. [works] 20260326-feature-IWS26H1-417/prd.md
     score: 0.82  |  section: 배경
     ...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

결과가 없으면:
```
  결과 없음. 인덱스가 최신인지 확인하세요: /jarfis:search-index --current
```

### 5. 상세 보기 안내

결과 하단에 안내:
```
  💡 파일 내용을 보려면 해당 파일 경로를 말씀해주세요.
```
사용자가 파일 경로를 언급하면 해당 파일을 읽어서 보여준다.
