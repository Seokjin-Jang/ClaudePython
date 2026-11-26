// 품질 게이트 파이프라인 (CLAUDE.md "소스코드 품질" 기준)
// 전제: Linux 에이전트에 python3.12가 설치돼 있음. PR 빌드는 GitHub Branch
// Source(멀티브랜치) 잡으로 실행하고 결과를 GitHub PR 상태 검사로 보고한다.
pipeline {
    agent any
    options {
        timestamps()
        disableConcurrentBuilds()
    }
    stages {
        stage('환경 준비') {
            steps {
                sh '''
                    python3.12 -m venv .venv
                    . .venv/bin/activate
                    pip install -q -r requirements-dev.txt
                '''
            }
        }
        stage('정적 분석') {
            steps {
                sh '''
                    . .venv/bin/activate
                    ruff check src tools tests
                    ruff format --check src tools tests
                '''
            }
        }
        stage('단위 테스트 / Branch 커버리지 100%') {
            steps {
                sh '''
                    . .venv/bin/activate
                    pytest tests --ignore=tests/integration \
                        --cov=src --cov=tools --cov-branch \
                        --cov-fail-under=100 \
                        --junitxml=reports/unit.xml
                '''
            }
        }
        stage('함수 길이 / 주석률') {
            steps {
                sh '''
                    . .venv/bin/activate
                    python tools/check_function_length.py src tools tests
                    python tools/check_comment_ratio.py src tools tests
                '''
            }
        }
        stage('통합 테스트') {
            when { expression { fileExists('tests/integration') } }
            steps {
                sh '''
                    . .venv/bin/activate
                    pytest tests/integration --junitxml=reports/integration.xml
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
