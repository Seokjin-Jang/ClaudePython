# ClaudePython

AI(Claude)를 활용해 작성한 파이썬 코드 모음입니다.

## 개요

이 저장소는 AI 코딩 도구인 Claude Code와 함께 만든 파이썬 예제와 스크립트를 모아 둔 곳입니다.
각 코드는 AI의 도움을 받아 작성했으며, 실행 방법과 설명을 함께 정리합니다.

## 요구 사항

- Python 3.12 이상
- Git

## 시작하기

### 1. 저장소 복제

```bash
git clone https://github.com/Seokjin-Jang/ClaudePython.git
cd ClaudePython
```

### 2. 가상 환경 만들기 (권장)

Windows (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. 패키지 설치

개발 도구(pytest, pytest-cov, ruff):

```bash
pip install -r requirements-dev.txt
```

## 사용 방법

품질 검사를 모두 실행합니다.

```bash
ruff check src tools tests
ruff format --check src tools tests
pytest tests --ignore=tests/integration --cov=src --cov=tools --cov-branch --cov-fail-under=100
python tools/check_function_length.py src tools tests
python tools/check_comment_ratio.py src tools tests
```

## 프로젝트 구조

```
ClaudePython/
├── .claude/            Claude Code 스킬·서브에이전트
├── docs/
│   ├── 00_plan/        개발 계획서
│   ├── 01_requirements/ SW 요구사항 사양서, Use Case, 추적표, OEM 질의
│   ├── 02_architecture/ SW 아키텍처 설계서
│   └── 03_detailed_design/ SW 상세 설계서
├── src/child_lock/     전자식 차일드락 제어 SW (개발 중)
├── tests/
│   └── tools/          품질 검사 스크립트 테스트
├── tools/              품질 검사 스크립트 (함수 길이, 주석률)
├── Jenkinsfile         CI 품질 게이트
├── pyproject.toml      프로젝트·pytest·ruff 설정
├── requirements-dev.txt
├── CLAUDE.md
└── README.md
```

## 기여

이슈나 개선 제안은 [Issues](https://github.com/Seokjin-Jang/ClaudePython/issues)에 남겨 주세요.
