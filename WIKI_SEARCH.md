# JARFIS Semantic Search

> **Last aligned**: v4.0.5 · 2026-04-20
> **구현**: `~/.claude/scripts/jarfis/wiki_search.py` (31,115 bytes)
> **모델**: `BAAI/bge-m3` via [sentence-transformers](https://sbert.net/)

---

## 1. 개요

JARFIS는 Org 레벨 자산(wiki · meetings · works) 에 대한 **시맨틱 통합 검색** 을 제공한다. 한국어/영어 혼용 마크다운에서 의미 기반으로 관련 문서를 찾아 Phase 0 wiki 로딩(`prompts/wiki-loading.md`) 에 자동 투입한다.

### 1.1 핵심 스펙

| 항목 | 값 |
|------|-----|
| 모델 | `BAAI/bge-m3` (multilingual embedding) |
| Top-k 기본 | 5 |
| Score threshold | 0.5 (cosine similarity) |
| Chunk threshold | 500 토큰 (문자 수 / 4 추정) |
| Index 포맷 | `.vectors.npz` (numpy) + `.vectors-meta.json` (metadata) |
| venv 위치 | `~/.claude/.jarfis-venv` |
| 메모리 가드 | 기본 4 GB (`JARFIS_MEMORY_THRESHOLD_GB` env override) |

### 1.2 검색 범위 (scope)

| Scope | 대상 디렉토리 |
|-------|--------------|
| `wiki` | `{org_root}/.jarfis-org/wiki/` |
| `meetings` | `{org_root}/works/{work}/meetings/` + 기타 meetings 위치 |
| `works` | `{org_root}/works/**/{discovery,planning,design,review,ops,retrospective}.md` |
| `all` | 위 3가지 통합 검색 |

---

## 2. 명령어

### 2.1 v4 통합 인터페이스 (권장)

```bash
# 검색
python3 ~/.claude/scripts/jarfis_cli.py search {all|meetings|works|wiki} <query> [--top-k N] [--pretty]

# 인덱스 생성/갱신
python3 ~/.claude/scripts/jarfis_cli.py index {all|meetings|works|wiki} [--org-root PATH]

# 상태 확인
python3 ~/.claude/scripts/jarfis_cli.py status [--org-root PATH]
```

### 2.2 Legacy wiki-only 인터페이스

```bash
python3 ~/.claude/scripts/jarfis_cli.py wiki index <org_root>
python3 ~/.claude/scripts/jarfis_cli.py wiki search <org_root> <query> [--top-k N]
python3 ~/.claude/scripts/jarfis_cli.py wiki status <org_root>
python3 ~/.claude/scripts/jarfis_cli.py wiki rebuild-index <org_root>   # M6: INDEX.md 재생성 (section _index.md 통합)
```

### 2.3 Slash commands

| Command | 역할 |
|---------|------|
| `/jarfis:search-setup` | venv + sentence-transformers 설치 (one-step) |
| `/jarfis:search` | 시맨틱 검색 (meetings + works + wiki 필터 가능) |
| `/jarfis:search-index` | 전체 Org 인덱스 일괄 생성/갱신 (wiki + meetings + works) |

---

## 3. 인덱싱

### 3.1 청킹 규칙

- 파일 단위로 읽되, **500 토큰 초과 시 청크 분할**
- 토큰 추정: `len(content) / 4` (ASCII 기준 근사)
- CJK 파일은 추정치가 낮아 실제보다 청크 수 많을 수 있음 — 검색 정확도엔 영향 미미
- frontmatter (YAML 헤더) 는 stripping 후 인덱싱

### 3.2 인덱스 출력

각 대상 디렉토리 루트에:
- `.vectors.npz` — numpy 배열 (청크별 embedding vectors, shape `(N, 1024)` for bge-m3)
- `.vectors-meta.json` — 청크별 메타 (file path, chunk id, content preview, embed time 등)

### 3.3 Staleness 감지

인덱스 생성 후 파일 `mtime` 변경 감지. `wiki status` / `search-index` 실행 시 stale 여부 리포트. Stale 시 `stale_warning` 필드 추가.

---

## 4. 검색 동작

### 4.1 쿼리 처리

1. 쿼리 문자열 → bge-m3 encode → query embedding
2. 해당 scope의 `.vectors.npz` 로드
3. cosine similarity 계산
4. score ≥ 0.5 & top-k 기준으로 결과 필터
5. JSON 결과 반환

### 4.2 결과 포맷

```json
{
  "results": [
    {
      "file": "DESIGN/payment-adr.md",
      "chunk_id": 2,
      "score": 0.73,
      "preview": "환불 정책은 주문 완료 후 7일 이내 ..."
    },
    ...
  ],
  "stale_warning": "12 files modified after last index. Run: jarfis_cli.py index wiki --org-root ...",
  "query": "결제 환불 정책"
}
```

### 4.3 Phase 0 wiki-loading 에서의 사용

`prompts/wiki-loading.md` 4-Step Full Loading 중 step 3:

```bash
python3 ~/.claude/scripts/jarfis_cli.py search wiki "{core keywords/phrases of the current plan}" --top-k 5
```

결과 `results` 배열에서 `score >= 0.5` 파일만 read. `stale_warning` 존재 시 사용자에게 인덱스 갱신 권장 메시지 표시.

---

## 5. 메모리 가드

bge-m3 모델 로드는 대략 **2-3 GB 메모리**를 소비한다. JARFIS는 사전 체크로 OOM/커널 패닉을 방지.

### 5.1 임계값

```bash
# 환경변수 override
export JARFIS_MEMORY_THRESHOLD_GB=6.0
```

기본 4.0 GB. 임계값 미달 시 `_ensure_dependencies()` 에서 `json_error` (hint=`memory_insufficient`) 반환 후 종료.

### 5.2 가용 메모리 계산

**macOS**: `vm_stat` parsing → `free + speculative + inactive` 페이지 × page size.

**Apple Silicon 특수 처리**:
- `torch.mps.driver_allocated_memory()` 로 MPS GPU 사용량 조회
- `vm_stat` 에 보이지 않는 unified memory 영역을 차감
- `effective = available - mps_gb`
- 결과에 `(MPS GPU: X.XGB in use)` 힌트 표시

**Linux**: `/proc/meminfo MemAvailable` 줄 파싱.

**기타 (FreeBSD, Windows 등)**: `None` 반환 → pass-through (가드 비활성).

### 5.3 CPU 강제 실행

Apple Silicon에서 MPS backend 사용 시 unified memory 소진 사고 관찰됨. `_load_model()` 에서 **CPU 강제** — bge-m3 추론 속도는 CPU로도 충분.

---

## 6. LLM Fallback

sentence-transformers 미설치 / 메모리 부족 / 인덱스 부재 등 상황에서 **LLM 기반 판단 fallback** 동작.

### 6.1 폴백 시나리오

| 상황 | 감지 | 메시지 |
|------|------|--------|
| sentence-transformers 미설치 | `ImportError` | "sentence-transformers is not installed. Run /jarfis:search-setup" |
| 메모리 부족 | `_check_available_memory_gb()` < threshold | "Insufficient memory: available X.XGB / minimum 4.0GB required" |
| 인덱스 부재 | `.vectors.npz` 없음 | "Wiki index not found. Run /jarfis:search-index" |

### 6.2 폴백 흐름 (Phase 0)

`prompts/wiki-loading.md` 4-Step step 3:

> **Fallback**: On search failure (no index / module not installed / insufficient memory) → display to the user: `⚠️ Semantic search is unavailable. Falling back to LLM-based search.` (if the error includes a `memory_insufficient` hint, append `(insufficient memory)`) → use the legacy approach (_index.md summary-based LLM judgment) to select up to 5 related files.

**즉**: semantic search 실패 → 사용자 경고 → `_index.md` 요약 기반 LLM 판단으로 최대 5개 관련 파일 선정. JARFIS 워크플로우는 중단되지 않는다.

### 6.3 폴백 품질

- LLM 판단은 `_index.md` 의 요약 기반이라 **semantic search 대비 재현율 낮음**
- 대안책이지 목표 아님 — `/jarfis:search-setup` 으로 semantic search 설치 권장

---

## 7. 설치

### 7.1 one-step 설치

```
/jarfis:search-setup
```

내부 동작:
1. `~/.claude/.jarfis-venv` 위치에 Python venv 생성
2. `pip install sentence-transformers torch` (bge-m3 로드에 torch 필요)
3. 모델 사전 다운로드 (`BAAI/bge-m3`, ~2.3 GB)
4. 메모리 가드 self-test

### 7.2 수동 설치

```bash
python3 -m venv ~/.claude/.jarfis-venv
source ~/.claude/.jarfis-venv/bin/activate
pip install sentence-transformers torch

# 확인
python3 -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-m3')"
```

### 7.3 초기 인덱싱

```
/jarfis:search-index
```

전체 Org 에 대해 wiki + meetings + works 인덱스 일괄 생성. 파일 수에 따라 1-10분 소요.

---

## 8. Trade-offs

### 8.1 장점

- **의미 기반 검색**: "환불" 쿼리가 "cancellation", "refund" 문서도 매칭
- **다국어**: bge-m3는 한/영 혼용 문서에서도 작동
- **Phase 0 자동 투입**: 사용자가 수동으로 관련 문서 찾을 필요 없음

### 8.2 비용

- **메모리**: 모델 로드 시 2-3 GB (메모리 가드로 완화)
- **설치**: venv + torch + sentence-transformers (~2.5 GB) 필요 — 선택적 설치
- **첫 실행 지연**: 모델 첫 로드 시 20-40초 (이후 캐시됨)
- **인덱스 crawl**: 파일 수에 따라 초 ~ 분 단위

### 8.3 보완 관계 — LLM Fallback

메모리 / 설치 / 인덱스 중 하나라도 미충족이면 LLM fallback 으로 우회. **JARFIS 워크플로우는 항상 진행 가능** (semantic search는 gate가 아닌 enhancement).

---

## 9. 관련 파일 + 참조

- **구현**: `~/.claude/scripts/jarfis/wiki_search.py` (31,115 bytes)
- **v4 통합 CLI**: `jarfis_cli.py search|index|status`
- **legacy wiki CLI**: `jarfis_cli.py wiki {index|search|status|rebuild-index}`
- **Slash commands**: `/jarfis:search-setup · /jarfis:search · /jarfis:search-index`
- **Phase 0 사용**: `~/.claude/commands/jarfis/prompts/wiki-loading.md`
- **venv 위치**: `~/.claude/.jarfis-venv`
- **환경변수**: `JARFIS_MEMORY_THRESHOLD_GB` (기본 4.0)
- **관련 ADR**: [DESIGN ADR-11 Cascading Specificity](./DESIGN.md#adr-11) (wiki 우선순위 규칙)

---

*이 문서는 `wiki_search.py` v4.0.5 구현을 narrative로 기술한다. 실제 코드가 1차 source이며, 구현 변경 시 이 문서보다 코드가 우선한다.*
