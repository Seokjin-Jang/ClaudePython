"""!
@brief 시스템 시험 실행기 (SWE.6).

docs/06_system_test/stc_cases.json의 각 테스트 케이스에 있는
automation 단계를 새 SW 인스턴스(실제 HTTP 서버)에 순서대로 보내고,
단계마다 기대 결과를 확인한다. 케이스 ID가 pytest 시험 ID가 된다.
automation이 null인 케이스는 수동 시험이므로 여기서 제외한다.
"""

import json
import threading
import time
import urllib.request
from pathlib import Path

import pytest

from child_lock.web.server import build

CASES_FILE = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "06_system_test"
    / "stc_cases.json"
)

# automation의 vehicle에 적지 않은 필드의 기본값 (사양 공통 사전 조건)
DEFAULT_VEHICLE = {
    "vehicle_speed_kph": 0.0,
    "gear": "P",
    "crash_status": "NONE",
    "rear_left_approach_risk": False,
    "rear_right_approach_risk": False,
    "fire_detected": False,
    "overtemperature_detected": False,
    "adult_present": False,
    "isofix_left": False,
    "isofix_right": False,
    "ignition_on": True,
    "sensor_fault": False,
}


def _automated_cases():
    """!
    @brief 자동 실행 가능한 케이스를 읽는다.
    @return [(케이스 ID, automation 단계 목록)]
    """
    if not CASES_FILE.exists():
        return []
    data = json.loads(CASES_FILE.read_text(encoding="utf-8"))
    return [
        (case["id"], case["automation"])
        for case in data["test_cases"]
        if case.get("automation")
    ]


def _vehicle_for(step):
    """!
    @brief 단계의 차량 입력을 만든다.

    vehicle_raw가 있으면 그대로, vehicle이 null이면 입력 없음,
    그 밖에는 기본값에 vehicle을 덮어쓴다 (timestamp_s 기본 = now_s).
    @param step automation 단계
    @return 원시 차량 입력 dict 또는 None
    """
    if "vehicle_raw" in step:
        return step["vehicle_raw"]
    if "vehicle" in step and step["vehicle"] is None:
        return None
    vehicle = dict(DEFAULT_VEHICLE, timestamp_s=step["now_s"])
    vehicle.update(step.get("vehicle") or {})
    return vehicle


def _call(base, method, path, body=None):
    """!
    @brief 서버에 요청하고 JSON 응답을 돌려준다.
    """
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(base + path, data=data, method=method)
    with urllib.request.urlopen(req, timeout=5) as resp:
        return json.loads(resp.read())


EVENT_KEYS = {
    "event_id",
    "timestamp_s",
    "lock_left",
    "lock_right",
    "state",
    "reason_code",
    "input_validity",
}
STATUS_KEYS = {
    "lock_left",
    "lock_right",
    "state",
    "input_validity",
    "reason_code",
    "priority_reason",
}


def _diff(label, actual, expected):
    """!
    @brief dict의 기대 필드와 실제 값을 비교한다.
    @return 불일치 설명 목록
    """
    return [
        f"{label}.{key}: 기대 {want}, 실제 {actual.get(key)}"
        for key, want in (expected or {}).items()
        if actual.get(key) != want
    ]


def _event_checks(events, spec):
    """!
    @brief expect_events 사양으로 이벤트 목록을 검사한다.
    @param events GET /api/events 결과
    @param spec expect_events 객체
    @return 불일치 설명 목록
    """
    ids = [e["event_id"] for e in events]
    exact = spec.get("all_keys_exact")
    # all_keys_exact는 true/false 또는 기대 키 목록으로 줄 수 있다
    keys = set(exact) if isinstance(exact, list) else EVENT_KEYS
    if isinstance(exact, list):
        spec = dict(spec, all_keys_exact=True)
    checks = {
        "count": len(events),
        "first_event_id": ids[0] if ids else None,
        "last_event_id": ids[-1] if ids else None,
        "ids_ascending": all(
            ids[i + 1] - ids[i] == 1 for i in range(len(ids) - 1)
        ),
        "all_keys_exact": all(set(e) == keys for e in events),
    }
    problems = _diff(
        "events", checks, {k: v for k, v in spec.items() if k in checks}
    )
    tail = spec.get("tail_reason_codes")
    if tail is not None:
        actual = [e["reason_code"] for e in events[-len(tail) :]]
        if actual != tail:
            problems.append(f"events.tail: 기대 {tail}, 실제 {actual}")
    return problems


def _check_events(base, step, before_last_id):
    """!
    @brief 단계의 이벤트 관련 기대 결과를 검사한다.
    @param before_last_id 단계 실행 전 마지막 event_id
    @return 불일치 설명 목록
    """
    keys = ("expect_events_contain", "expect_events", "expect_new_events_lack")
    if not any(step.get(k) for k in keys):
        return []
    events = _call(base, "GET", "/api/events")
    codes = [e["reason_code"] for e in events]
    problems = [
        f"이벤트 {c} 없음"
        for c in step.get("expect_events_contain") or []
        if c not in codes
    ]
    if step.get("expect_events"):
        problems += _event_checks(events, step["expect_events"])
    new = [e["reason_code"] for e in events if e["event_id"] > before_last_id]
    problems += [
        f"새 이벤트에 {c} 있음"
        for c in step.get("expect_new_events_lack") or []
        if c in new
    ]
    return problems


def _check_status(base, step):
    """!
    @brief GET /api/status 관련 기대 결과를 검사한다.
    @return 불일치 설명 목록
    """
    if not (step.get("expect_status") or step.get("expect_status_keys_exact")):
        return []
    status = _call(base, "GET", "/api/status")
    problems = _diff("status", status, step.get("expect_status"))
    if step.get("expect_status_keys_exact") and set(status) != STATUS_KEYS:
        problems.append(f"status 키: {sorted(status)}")
    return problems


def _last_event_id(base):
    """!
    @brief 현재 마지막 event_id (없으면 0).
    """
    events = _call(base, "GET", "/api/events")
    return events[-1]["event_id"] if events else 0


def _run_step(base, step):
    """!
    @brief 단계 하나를 실행하고 기대 결과와의 차이를 돌려준다.
    @param base 서버 기본 URL
    @param step automation 단계
    @return 불일치 설명 목록 (비어 있으면 합격)
    """
    body = {"now_s": step["now_s"]}
    vehicle = _vehicle_for(step)
    if vehicle is not None:
        body["vehicle"] = vehicle
    if step.get("command"):
        body["command"] = step["command"]
    last_id = _last_event_id(base)
    started = time.perf_counter()
    status = _call(base, "POST", "/api/step", body)
    elapsed_ms = (time.perf_counter() - started) * 1000
    problems = _diff("step", status, step.get("expect"))
    limit = step.get("max_response_ms")
    if limit is not None and elapsed_ms > limit:
        problems.append(f"응답 {elapsed_ms:.1f} ms > {limit} ms")
    problems += _check_events(base, step, last_id)
    problems += _check_status(base, step)
    return problems


@pytest.mark.parametrize(
    ("case_id", "steps"),
    _automated_cases(),
    ids=[c[0] for c in _automated_cases()],
)
def test_system_case(case_id, steps):
    """!
    @brief 시스템 시험 케이스 하나를 새 SW 인스턴스에서 실행한다.
    @param case_id 테스트 케이스 ID
    @param steps automation 단계 목록
    """
    server, _ = build(["--host", "127.0.0.1", "--port", "0"])
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        for index, step in enumerate(steps, 1):
            problems = _run_step(base, step)
            assert not problems, f"{case_id} 단계 {index}: {problems}"
    finally:
        server.shutdown()
        server.server_close()
