# CLAUDE.md

이 파일은 Claude Code(claude.ai/code)가 이 저장소에서 작업할 때 따라야 할 안내를 담고 있습니다.

**이 파일은 반드시 한국어로 작성합니다.** 내용을 추가하거나 고칠 때도 한국어로 쓰고, 명령어·경로·코드 식별자만 원래 표기를 유지합니다.

## 프로젝트 현황

ClaudePython에서는 OEM-A의 전자식 차일드락 제어 SW(교육용 가상 프로젝트 VJ-ECL-2026)를 PC/SIL 참조 구현으로 개발합니다. 개발 계획과 결정 사항은 `docs/00_plan/개발계획서.md`에 있습니다.

- OEM 입력 문서는 `OEM/`에 두지만 **git에 올리지 않습니다**(`.gitignore`). 문서에 교육 과정 밖 공개·배포 금지 조건이 있고 이 저장소는 공개 저장소이기 때문입니다.
- 패키지는 `src/child_lock/`, Web 시뮬레이터는 Python 표준 라이브러리(`http.server`)로만 만듭니다. 외부 런타임 의존성을 추가하지 않습니다.

## 개발 환경

- **Python 3.12**를 사용합니다. OEM 사양서의 실행 환경(Python 3.12 PC/SIL)에 맞춘 것입니다. `pyproject.toml`에 `requires-python = ">=3.12"`로 적혀 있습니다.
- 가상 환경은 `.venv`에 만들고 개발 도구는 `pip install -r requirements-dev.txt`로 설치합니다.
  - Windows에서 `python` 명령이 Microsoft Store 바로가기로 연결되면 `C:\Users\user\AppData\Local\Programs\Python\Python312\python.exe -m venv .venv`로 만듭니다.
  - 이후 명령은 `.\.venv\Scripts\python.exe`, `.\.venv\Scripts\ruff.exe`처럼 가상 환경 안의 실행 파일로 실행합니다.
- **단위 테스트**: `pytest` + `pytest-cov`. **정적 분석**: `ruff`. 설정은 모두 `pyproject.toml`에 있습니다.
- **디렉터리 구조**:
  - `src/child_lock/`: 소스 코드
  - `tests/unit/`: 단위 테스트
  - `tests/integration/`: 통합 테스트
  - `tests/system/`: 시스템 시험 실행기 (`docs/06_system_test/stc_cases.json`의 `automation` 단계를 실제 HTTP 서버에 실행)
  - `tests/vectors/`: Use Case 입력 벡터 (결정론 재생)
  - `tests/tools/`: 품질 검사 스크립트의 테스트
  - `docs/`: A-SPICE 산출물(아래 "개발 절차" 참고)
  - `tools/`: 품질 검사 스크립트(`check_function_length.py`, `check_comment_ratio.py`, 공용 `line_kinds.py`)

## 개발 절차

A-SPICE 절차를 따릅니다. 단계 순서와 각 단계의 산출물 위치는 다음과 같습니다.

| 단계 | A-SPICE | 산출물 위치 |
|---|---|---|
| 1. 요구사항 분석 | SWE.1 | `docs/01_requirements/` |
| 2. 아키텍처 설계 | SWE.2 | `docs/02_architecture/` |
| 3. 상세 설계 | SWE.3 | `docs/03_detailed_design/` |
| 4. 구현 | SWE.3 | `src/` |
| 5. 단위 테스트 | SWE.4 | `tests/unit/`, 결과는 `docs/04_unit_test/` |
| 6. 통합 테스트 | SWE.5 | `tests/integration/`, 사양·결과는 `docs/05_integration_test/` |
| 7. 시스템 테스트 | SWE.6 | `docs/06_system_test/` |

- 앞 단계 산출물이 없으면 다음 단계를 시작하지 않습니다. 예를 들어 요구사항 문서 없이 코드를 쓰지 않습니다. 요청이 단계를 건너뛰는 것이면 사용자에게 먼저 확인합니다.
- **추적성**: 요구사항에는 ID(예: `SWR-001`)를 붙이고, 설계 문서, 소스 주석(`@req SWR-001`), 테스트(`@req SWR-001`)에서 그 ID를 참조합니다. 모든 요구사항이 설계와 테스트로 연결돼야 합니다.
- **구현은 TDD로 합니다.** 구현 코드를 쓰기 전에 `test-driven-development` 스킬을 불러와 그 순서를 따릅니다. 코드를 작성하는 서브에이전트에도 똑같이 적용합니다.
- **시스템 테스트 케이스**는 `system-test-case` 서브에이전트(`sw-system-test-case` 스킬)로 만듭니다.

## 소스코드 품질

아래 기준은 PR을 merge하기 위한 필수 조건입니다. 측정 명령은 Jenkins도 같은 명령을 씁니다.

| 항목 | 기준 | 측정 방법 |
|---|---|---|
| 단위 테스트 성공률 | 100% | `pytest tests --ignore=tests/integration --ignore=tests/system` — 실패 0건. `skip`/`xfail`은 사용자 승인 없이 쓰지 않음 |
| Branch 커버리지 | **반드시** 100% | `pytest tests --ignore=tests/integration --ignore=tests/system --cov=src --cov=tools --cov-branch --cov-fail-under=100` |
| 순환 복잡도 | 함수당 **반드시** 10 이하 | ruff `C901` 규칙, `max-complexity = 10` |
| 함수 길이 | 순수 코드 50줄 이하 | `python tools/check_function_length.py src tools tests` (빈 줄, 주석, docstring 제외) |
| 주석률 | 파일별 20% 이상 (테스트 파일 포함) | `python tools/check_comment_ratio.py src tools tests` — (주석 줄 + docstring 줄) ÷ (코드 줄 + 주석 줄 + docstring 줄), 빈 줄 제외 |
| 명명 규칙 | Google Python Style Guide | ruff `N`(pep8-naming) 규칙 + 리뷰 |
| 정적 분석 | 경고 0건 | `ruff check src tools tests`, `ruff format --check src tools tests` |

- 테스트 하나만 실행: `pytest tests/unit/test_x.py::test_name`

- 커버리지가 100%에 못 미치면 테스트를 추가해 100%를 달성할 때까지 반복합니다. 커버리지를 맞추려고 `# pragma: no cover`로 코드를 제외하지 않습니다. 정말 테스트할 수 없는 코드(예: `if __name__ == "__main__":`)만 사유를 주석으로 남기고 제외합니다.
- **명명 규칙**(Google Python Style Guide): 모듈·패키지 `lower_with_under`, 클래스·예외 `CapWords`, 함수·메서드·변수 `lower_with_under`, 상수 `CAPS_WITH_UNDER`, 내부용 이름은 앞에 `_`. 한 줄은 80자 이하.
- **주석은 Doxygen 스타일**로 씁니다. 함수·클래스 docstring은 `"""!`로 시작하고 `@brief`, `@param`, `@return`, `@raises`를 씁니다. 주석 내용은 한국어로 씁니다. docstring 형식은 Google 스타일이 아니라 이 Doxygen 규칙을 따릅니다.

  ```python
  def clamp(value: int, low: int, high: int) -> int:
      """!
      @brief 값을 [low, high] 범위로 제한한다.
      @param value 입력 값
      @param low 하한
      @param high 상한
      @return 제한된 값
      @req SWR-001
      """
  ```

## Git 브랜치 규칙 (GitHub Flow)

- `main`은 항상 품질 기준을 통과한 상태를 유지합니다. `main`에 직접 커밋하거나 push하지 않습니다.
- 모든 작업은 최신 `main`에서 브랜치를 만들어 진행합니다. 브랜치 하나에는 한 가지 목적의 작업만 담습니다.
- 브랜치 이름은 `<유형>/<짧은-설명>` 형식으로, 영어 소문자와 하이픈만 씁니다. 요구사항 ID가 있으면 포함합니다.

  | 유형 | 용도 | 예 |
  |---|---|---|
  | `feature/` | 기능 추가 | `feature/swr-001-speed-limit` |
  | `fix/` | 버그 수정 | `fix/overflow-in-timer` |
  | `refactor/` | 동작 변경 없는 구조 개선 | `refactor/split-parser` |
  | `test/` | 테스트만 추가·수정 | `test/boundary-cases` |
  | `docs/` | 문서·산출물만 변경 | `docs/architecture-v1` |
  | `chore/` | 설정, 빌드, CI | `chore/jenkinsfile` |

- 커밋 메시지는 한국어로, 첫 줄에 50자 이내 요약, 한 줄 띄우고 본문에 변경 이유를 씁니다.
- 작업이 끝나면 `main`으로 향하는 PR을 엽니다. PR 제목과 본문은 한국어로 쓰고, 본문에 관련 요구사항 ID와 품질 측정 결과를 적습니다.
- **merge 조건**: Jenkins 품질 검사가 통과해야 합니다. GitHub의 `main` 브랜치 보호 규칙으로 검사 실패 시 merge를 막습니다.
- merge는 사용자가 합니다. Claude는 PR을 만들고 고치기까지만 하고 merge하지 않습니다. merge 방식은 Squash merge이고, merge 후 브랜치는 삭제합니다.

## CI (Jenkins)

- Jenkins 서버: `http://172.16.7.128` (Jenkins 2.580.2, 실행 노드는 Built-In Node 1대, Windows 11)
- **Jenkins API 토큰과 GitHub 토큰은 git에 저장하지 않습니다.** 파일, 커밋 메시지, PR 본문, 문서 어디에도 적지 않습니다. Jenkins 안의 비밀 값은 Jenkins Credentials에만 둡니다.
- 파이프라인은 저장소 루트의 `Jenkinsfile`로 정의합니다. PR이 열리거나 갱신될 때마다 실행되고, 결과를 GitHub PR 상태 검사로 보고합니다.
- 파이프라인 단계: Python 3.12 가상 환경 준비 → `ruff check` / `ruff format --check` → 단위 테스트와 Branch 커버리지 100% 검사 → 함수 길이·주석률 검사 → 통합 테스트(`tests/integration`이 있을 때). 한 단계라도 실패하면 PR 검사가 실패합니다.
- `Jenkinsfile`은 Windows 노드용(`bat`)입니다. Python은 기본으로 `py -3.12`를 쓰고, Jenkins 환경 변수 `PYTHON_CMD`로 바꿀 수 있습니다. `bat` 블록의 각 명령 끝에는 `|| exit /b 1`을 붙여 실패가 빌드 실패로 이어지게 합니다.
- **Jenkins 잡**: `ClaudePython-PR` (멀티브랜치). GitHub 자격 증명 ID `github-claudepython`. GitHub가 내부망 Jenkins에 웹훅을 보낼 수 없어 **5분마다 저장소를 스캔**합니다. 급하면 Jenkins에서 "Scan Repository Now"를 실행합니다.
- **GitHub 보호 규칙**: `main`은 상태 검사 `continuous-integration/jenkins/pr-merge` 통과가 필수입니다.
- 기존 `ClaudePython` 프리스타일 잡(매시 `main`에서 `dir` 실행)은 사용자 요청으로 그대로 둡니다.
- PR을 열기 전에도 위 품질 명령을 로컬에서 실행해 결과를 PR 본문에 적습니다.
- Jenkins 서비스 계정에서 `py` 런처를 찾지 못해, `Jenkinsfile`이 사용자 범위 Python 경로로 대체합니다. Python 3.12를 시스템 전체로 설치하면 이 대체 경로는 쓰이지 않습니다.

## 기타

- 모든 산출물(문서, 주석, 커밋 메시지, PR, 테스트 사양)은 한국어로 씁니다. 코드 식별자는 위 명명 규칙에 따라 영어로 씁니다.
- 의미 없는 사과를 하지 않습니다.
- 반말을 쓰지 않습니다.
