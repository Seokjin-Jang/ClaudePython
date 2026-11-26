"""!
@brief 의존 방향 검사: ASIL B 모듈은 QM 모듈을 import하지 않는다.

SWA-001 P-03, 5절(간섭 배제), 6절(정적 분석 계획).
"""

import ast
from pathlib import Path

import child_lock

ASIL_B = {
    "types",
    "validator",
    "input_monitor",
    "approach_guard",
    "arbiter",
    "controller",
}
QM = {"driver_request", "event_log", "status", "web", "replay"}


def qm_imports(source):
    """!
    @brief 소스가 import하는 child_lock QM 모듈 이름을 모은다.
    @param source 파이썬 소스
    @return QM 모듈 이름 집합
    """
    found = set()
    for node in ast.walk(ast.parse(source)):
        names = []
        if isinstance(node, ast.ImportFrom) and node.module:
            names = [node.module] + [
                f"{node.module}.{a.name}" for a in node.names
            ]
        elif isinstance(node, ast.Import):
            names = [a.name for a in node.names]
        for name in names:
            parts = name.split(".")
            if parts[0] == "child_lock" and len(parts) > 1:
                found |= {parts[1]} & QM
    return found


def test_checker_detects_violation():
    """!
    @brief 검사 함수가 실제 위반을 잡을 수 있는지 먼저 확인한다.
    """
    assert qm_imports("from child_lock import event_log") == {"event_log"}
    assert qm_imports("import child_lock.status") == {"status"}
    assert qm_imports("from child_lock.web.server import App") == {"web"}
    assert qm_imports("from child_lock.types import Lock") == set()
    assert qm_imports("import json") == set()


def test_asil_b_modules_do_not_import_qm_modules():
    """!
    @brief ASIL B 모듈 6개에 QM import가 없는지 확인한다.
    @req SWR-019
    """
    root = Path(child_lock.__file__).parent
    violations = {
        name: qm_imports((root / f"{name}.py").read_text(encoding="utf-8"))
        for name in ASIL_B
    }
    assert {k: v for k, v in violations.items() if v} == {}
