# SBOM — 전자식 차일드락 제어 SW

| 항목 | 내용 |
|---|---|
| 문서 ID | SBOM-001 |
| 대상 베이스라인 | BL-CODE-UT-1.0 / BL-INT-1.0 (초안) |
| 형식 | 사람이 읽는 표 (CycloneDX 등 기계 판독 형식은 범위 밖) |

## 1. 런타임 구성 요소

| 구성 요소 | 버전 | 출처 | 라이선스 | 비고 |
|---|---|---|---|---|
| child_lock | 0.1.0 | 이 저장소 `src/child_lock` | 미지정 (교육용) | 자체 개발 |
| CPython | 3.12.10 | python.org | PSF-2.0 | 실행 환경 (OEM 사양서 3절) |
| Python 표준 라이브러리 | 3.12.10 동봉 | python.org | PSF-2.0 | `http.server`, `json`, `hashlib`, `dataclasses`, `enum`, `threading`, `collections`, `argparse`, `math`, `pathlib`, `time` |

**외부 런타임 패키지: 없음** (`pyproject.toml`의 `dependencies = []`, DEC-02).

## 2. 개발·시험 도구 (배포물에 포함되지 않음)

| 구성 요소 | 버전 | 라이선스 | 용도 |
|---|---|---|---|
| pytest | 9.2.0 | MIT | 단위·통합 시험 |
| pytest-cov | 7.1.0 | MIT | 커버리지 측정 |
| coverage | 7.17.5 | Apache-2.0 | pytest-cov 의존 |
| ruff | 0.17.6 | MIT | 정적 분석·포맷 |

고정 버전은 `requirements-dev.txt`에 있다.
