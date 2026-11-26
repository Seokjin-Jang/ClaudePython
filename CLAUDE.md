# CLAUDE.md

이 파일은 Claude Code(claude.ai/code)가 이 저장소에서 작업할 때 따라야 할 안내를 담고 있습니다.

**이 파일은 반드시 한국어로 작성합니다.** 내용을 추가하거나 고칠 때도 한국어로 쓰고, 명령어·경로·코드 식별자만 원래 표기를 유지합니다.

## 프로젝트 현황

ClaudePython은 AI(Claude)를 활용해 작성한 파이썬 코드 모음입니다. 아직 파이썬 소스 코드, 패키지 목록 파일, 테스트, 린터 설정, CI가 없습니다. 현재 저장소에 있는 것은 `README.md`, 이 파일, 그리고 `.claude/` 아래의 Claude Code 설정(스킬·서브에이전트)입니다. 코드가 추가되면 관례를 짐작해 적지 말고 실제 빌드·테스트·린트 명령과 구조로 이 파일을 갱신합니다.

## Claude Code 설정 (`.claude/`)

- `skills/sw-system-test-case/`: 요구사항(테스트 베이시스)으로부터 A-SPICE·ISO 26262-6을 만족하는 SW 시스템 테스트 케이스를 엑셀로 생성하는 스킬. `scripts/build_workbook.py`가 추적성·커버리지 100%를 검증하고, 페어와이즈는 `scripts/get_pict.py`가 GitHub에서 내려받은 PICT로 만듭니다(`bin/`은 git에서 제외). 시험용 평가 케이스는 `evals/`에 있습니다.
- `agents/system-test-case.md`: 요구사항 분석이 끝난 뒤 시스템 테스트 케이스를 만드는 서브에이전트(Sonnet 5.5). 위 스킬을 사용합니다.
- `skills/test-driven-development/`: obra/superpowers에서 가져온 TDD 스킬(MIT). 원본을 수정하지 않고 그대로 두며, 출처와 커밋은 `SOURCE.md`에 기록돼 있습니다.

## README에서 정한 규칙

- 대상 버전은 Python 3.10 이상입니다.
- 가상 환경은 `.venv`를 씁니다(`python -m venv .venv`, Windows에서는 `.\.venv\Scripts\Activate.ps1`로 활성화).
- 의존성이 생기면 `requirements.txt`에 적습니다(`pip install -r requirements.txt`).
- 스크립트는 `python <파일>.py`로 직접 실행합니다.
- 파일이나 디렉터리를 추가하면 `README.md`의 "프로젝트 구조" 절도 함께 갱신합니다.

## 구현 방식: TDD

이 저장소에서 기능 구현, 버그 수정, 리팩터링, 동작 변경을 할 때는 구현 코드를 쓰기 전에 `test-driven-development` 스킬을 불러와 레드-그린-리팩터 순서를 따릅니다. 실패하는 테스트 작성 → 실행해서 올바른 이유로 실패하는지 확인 → 통과할 최소한의 코드 작성 → 전체 테스트 실행 → 정리. 코드를 작성하는 서브에이전트에도 똑같이 적용됩니다.

- 테스트 도구는 `pytest`입니다(`.venv`에 `pip install pytest`로 설치). 테스트 하나만 실행할 때는 `pytest path/to/test_file.py::test_name`, 전체는 `pytest`.
- 스킬이 허용하는 예외(버리는 시제품, 생성된 코드, 설정 파일)라도 TDD를 건너뛰기 전에 사용자 확인을 받습니다.

## 언어

`CLAUDE.md`, README 같은 문서와 커밋 메시지는 한국어로 씁니다. 코드 식별자는 영어로 씁니다.

## 개발 환경

- 개발 PC는 Windows이고, 셸은 PowerShell 5.1입니다.
  - `python` 명령이 Microsoft Store 바로가기로 연결될 수 있습니다. 그때는 `C:\Users\user\AppData\Local\Programs\Python\Python312\python.exe`를 씁니다.
  - 한글이 들어간 파일을 Python으로 다룰 때는 `PYTHONUTF8=1`을 설정합니다.
- 원격 저장소는 `https://github.com/Seokjin-Jang/ClaudePython.git`, 기본 브랜치는 `main`입니다. Git HTTPS 인증은 `gh`로 처리합니다(`gh auth setup-git`).
- PowerShell에서 여러 줄 커밋 메시지를 here-string으로 넘기면 깨질 수 있으므로, 메시지를 파일로 저장해 `git commit -F <파일>`로 커밋합니다.
