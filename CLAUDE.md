# CLAUDE.md

이 파일은 Claude Code(claude.ai/code)가 이 저장소에서 작업할 때 따라야 할 안내를 담고 있습니다.

**이 파일은 반드시 한국어로 작성합니다.** 내용을 추가하거나 고칠 때도 한국어로 쓰고, 명령어·경로·코드 식별자만 원래 표기를 유지합니다.

## 프로젝트 현황

ClaudePython은 AI(Claude)를 활용해 작성한 파이썬 코드 모음입니다. 아직 파이썬 소스 코드, `pyproject.toml`, 테스트, `Jenkinsfile`이 없습니다. 현재 저장소에 있는 것은 `README.md`, 이 파일, 그리고 `.claude/` 아래의 Claude Code 설정(스킬·서브에이전트)입니다. 아래 규칙에서 "만든다"고 적은 설정 파일은 첫 코드를 추가할 때 함께 만듭니다.

## 개발 환경

- **Python 3.14**를 사용합니다. `pyproject.toml`에 `requires-python = ">=3.14"`로 적고, 가상 환경은 `.venv`에 만듭니다.
- **단위 테스트**: `pytest` + `pytest-cov`.
- **정적 분석**: `ruff` (`ruff check`, `ruff format --check`). 설정은 `pyproject.toml`의 `[tool.ruff]`에 둡니다.
- **디렉터리 구조**:
  - `src/<패키지>/`: 소스 코드
  - `tests/unit/`: 단위 테스트
  - `tests/integration/`: 통합 테스트
  - `docs/`: A-SPICE 산출물(아래 "개발 절차" 참고)
  - `tools/`: 품질 검사 스크립트

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
| 단위 테스트 성공률 | 100% | `pytest tests/unit` — 실패 0건. `skip`/`xfail`은 사용자 승인 없이 쓰지 않음 |
| Branch 커버리지 | **반드시** 100% | `pytest tests/unit --cov=src --cov-branch --cov-fail-under=100` |
| 순환 복잡도 | 함수당 **반드시** 10 이하 | ruff `C901` 규칙, `max-complexity = 10` |
| 함수 길이 | 순수 코드 50줄 이하 | `tools/check_function_length.py` (빈 줄, 주석, docstring 제외) |
| 주석률 | 파일별 20% 이상 | `tools/check_comment_ratio.py` — (주석 줄 + docstring 줄) ÷ (코드 줄 + 주석 줄 + docstring 줄), 빈 줄 제외 |
| 명명 규칙 | Google Python Style Guide | ruff `N`(pep8-naming) 규칙 + 리뷰 |
| 정적 분석 | 경고 0건 | `ruff check src tests`, `ruff format --check src tests` |

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
- `tools/check_function_length.py`, `tools/check_comment_ratio.py`는 아직 없습니다. 첫 코드를 추가할 때 TDD로 함께 만듭니다.

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

- Jenkins 서버: `172.16.7.128`
- 파이프라인은 저장소 루트의 `Jenkinsfile`로 정의합니다. PR이 열리거나 갱신될 때마다 실행되고, 결과를 GitHub PR 상태 검사로 보고합니다.
- 파이프라인 단계: Python 3.14 가상 환경 준비 → `ruff check` / `ruff format --check` → 단위 테스트와 Branch 커버리지 100% 검사 → 함수 길이·주석률 검사 → 통합 테스트. 한 단계라도 실패하면 PR 검사가 실패합니다.
- **미구성 상태**: `Jenkinsfile`, Jenkins와 GitHub 연동, `main` 브랜치 보호 규칙은 아직 설정되지 않았습니다. 설정하기 전까지는 PR을 열기 전에 위 명령을 로컬에서 직접 실행해 결과를 PR 본문에 적습니다.

## 기타

- 모든 산출물(문서, 주석, 커밋 메시지, PR, 테스트 사양)은 한국어로 씁니다. 코드 식별자는 위 명명 규칙에 따라 영어로 씁니다.
- 의미 없는 사과를 하지 않습니다.
- 반말을 쓰지 않습니다.
