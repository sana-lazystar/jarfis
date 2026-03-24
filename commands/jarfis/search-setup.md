# JARFIS Search Setup

> 시맨틱 검색을 위한 sentence-transformers 원스텝 설치

## 실행 흐름

### 1. 환경 확인

```bash
python3 --version
```

Python 3이 없으면 안내하고 중단:
```
Python 3이 필요합니다. brew install python3 으로 설치하세요.
```

### 2. venv 생성 + 패키지 설치

```bash
python3 -m venv ~/.claude/.jarfis-venv && ~/.claude/.jarfis-venv/bin/pip install sentence-transformers
```

- 이미 `~/.claude/.jarfis-venv/`가 존재하면 venv 생성을 건너뛰고 pip install만 실행 (업그레이드/재설치)
- 설치 시작 전 사용자에게 안내: "sentence-transformers + 의존성을 설치합니다. 최초 설치 시 수 분이 걸릴 수 있습니다."

### 3. 설치 확인

```bash
~/.claude/.jarfis-venv/bin/python3 -c "from sentence_transformers import SentenceTransformer; print('OK')"
```

### 4. 결과 보고

성공 시:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Wiki Semantic Search 설치 완료
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  venv: ~/.claude/.jarfis-venv/
  패키지: sentence-transformers

  다음 단계:
    /jarfis:search-index
    Org을 선택하여 wiki 인덱스를 생성합니다.

  Note: 최초 인덱싱 시 bge-m3 모델이
  자동 다운로드됩니다 (~2GB).
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

실패 시: 에러 메시지를 사용자에게 보여주고, 수동 설치 명령어를 안내:
```
수동 설치:
  python3 -m venv ~/.claude/.jarfis-venv
  ~/.claude/.jarfis-venv/bin/pip install sentence-transformers
```
