// 품질 게이트 파이프라인 (CLAUDE.md "소스코드 품질" 기준)
// 실행 환경: Jenkins Built-In Node (Windows 11). PR 빌드는 GitHub Branch
// Source 멀티브랜치 잡으로 실행하고 결과를 GitHub PR 상태 검사로 보고한다.
// Python 실행 명령은 Jenkins 환경 변수 PYTHON_CMD로 바꿀 수 있다
// (기본값: Python 런처 "py -3.12").
// bat 블록은 중간 명령이 실패해도 계속 진행하므로 명령마다
// "|| exit /b 1"로 실패를 전파한다.
pipeline {
    agent any
    options {
        timestamps()
        disableConcurrentBuilds()
    }
    environment {
        PYTHONUTF8 = '1'
        PYTHONIOENCODING = 'utf-8'
        PY = "${env.PYTHON_CMD ?: 'py -3.12'}"
        VENV_PY = '.venv\\Scripts\\python.exe'
    }
    stages {
        stage('환경 준비') {
            steps {
                bat '''
                    %PY% --version || exit /b 1
                    %PY% -m venv .venv || exit /b 1
                    %VENV_PY% -m pip install -q -r requirements-dev.txt || exit /b 1
                '''
            }
        }
        stage('정적 분석') {
            steps {
                bat '''
                    %VENV_PY% -m ruff check src tools tests || exit /b 1
                    %VENV_PY% -m ruff format --check src tools tests || exit /b 1
                '''
            }
        }
        stage('단위 테스트 / Branch 커버리지 100%') {
            steps {
                bat '''
                    %VENV_PY% -m pytest tests --ignore=tests/integration ^
                        --cov=src --cov=tools --cov-branch ^
                        --cov-fail-under=100 ^
                        --junitxml=reports/unit.xml || exit /b 1
                '''
            }
        }
        stage('함수 길이 / 주석률') {
            steps {
                bat '''
                    %VENV_PY% tools\\check_function_length.py src tools tests || exit /b 1
                    %VENV_PY% tools\\check_comment_ratio.py src tools tests || exit /b 1
                '''
            }
        }
        stage('통합 테스트') {
            when { expression { fileExists('tests/integration') } }
            steps {
                bat '''
                    %VENV_PY% -m pytest tests/integration ^
                        --junitxml=reports/integration.xml || exit /b 1
                '''
            }
        }
    }
    post {
        always {
            junit allowEmptyResults: true, testResults: 'reports/*.xml'
        }
    }
}
