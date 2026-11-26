"""!
@brief 통합 시험: HTTP → 해석 → 제어기 → 기록 → 상태 조회 전체 흐름.

시험 사양: docs/05_integration_test/IT-001_통합시험사양및결과.md
"""

from it_support import vehicle

STATUS_KEYS = {
    "lock_left",
    "lock_right",
    "state",
    "input_validity",
    "reason_code",
    "priority_reason",
}
EVENT_KEYS = {
    "event_id",
    "timestamp_s",
    "lock_left",
    "lock_right",
    "state",
    "reason_code",
    "input_validity",
}


def _cmd(side, action, source="avn"):
    """!
    @brief 원시 운전자 명령을 만든다.
    """
    return {"side": side, "action": action, "source": source}


def test_it01_status_interface_matches_last_step(client):
    """!
    @brief IT-01 상태 조회 6필드가 마지막 평가 결과와 일치한다 (IF-006).
    @req SWR-014
    """
    step = client.step(0.0, vehicle(0.0, vehicle_speed_kph=10.0))
    code, status = client.request("GET", "/api/status")
    assert code == 200
    assert set(status) == STATUS_KEYS
    assert status == step
    assert status["priority_reason"] == status["reason_code"]


def test_it02_driver_command_all_sources_end_to_end(client):
    """!
    @brief IT-02 운전자 명령 4경로가 HTTP 경유로 같은 결과를 낸다 (IF-004).
    @req SWR-001, SWR-002
    """
    t = 0.0
    for source in ("physical_button", "avn", "voice", "mobile_app"):
        locked = client.step(t, vehicle(t), _cmd("left", "lock", source))
        t += 0.05
        released = client.step(t, vehicle(t), _cmd("left", "unlock", source))
        t += 0.05
        assert (locked["lock_left"], released["lock_left"]) == (
            "LOCK",
            "RELEASE",
        )


def test_it03_approach_override_flow_and_event_trace(client):
    """!
    @brief IT-03 접근위험 억제 → 10 s 내 재입력 → 이벤트 기록 흐름 (UC-03).
    @req SWR-005, SWR-006, SWR-010
    """
    risk = {"rear_right_approach_risk": True}
    client.step(1.0, vehicle(1.0, **risk), _cmd("right", "unlock"))
    status = client.step(5.0, vehicle(5.0, **risk), _cmd("right", "unlock"))
    assert status["lock_right"] == "LOCK"
    _, events = client.request("GET", "/api/events")
    codes = [e["reason_code"] for e in events]
    assert codes == [
        "APPROACH_RISK",
        "DRIVER_REQUEST_REJECTED",
        "APPROACH_RISK",
        "APPROACH_OVERRIDE_REQUESTED",
    ]
    assert all(set(e) == EVENT_KEYS for e in events)


def test_it04_crash_release_survives_until_ignition_cycle(client):
    """!
    @brief IT-04 충돌 확정 해제가 IGN 재시작 전까지 유지된다 (UC-04).
    @req SWR-007, SWR-020
    """
    moving = {"vehicle_speed_kph": 40.0, "isofix_left": True}
    assert client.step(0.0, vehicle(0.0, **moving))["lock_left"] == "LOCK"
    crash = vehicle(0.05, crash_status="CONFIRMED", **moving)
    status = client.step(0.05, crash)
    assert (status["lock_left"], status["lock_right"]) == ("RELEASE", "RELEASE")
    assert client.step(0.10, vehicle(0.10, **moving))["reason_code"] == (
        "CRASH_CONFIRMED"
    )
    client.step(0.15, vehicle(0.15, ignition_on=False))
    assert client.step(0.20, vehicle(0.20, **moving))["lock_left"] == "LOCK"


def test_it05_invalid_and_stale_inputs_degrade_then_recover(client):
    """!
    @brief IT-05 무효·지연 입력 시 DEGRADED, 정상 입력 시 NORMAL 복귀 (UC-07).
    @req SWR-013
    """
    client.step(0.0, vehicle(0.0, vehicle_speed_kph=10.0))
    bad = client.step(0.05, vehicle(0.05, vehicle_speed_kph="fast"))
    assert (bad["state"], bad["reason_code"], bad["lock_left"]) == (
        "DEGRADED",
        "INPUT_INVALID",
        "LOCK",
    )
    stale = client.step(0.30)
    assert (stale["state"], stale["reason_code"]) == ("DEGRADED", "INPUT_STALE")
    ok = client.step(0.35, vehicle(0.35))
    assert ok["state"] == "NORMAL"


def test_it06_malformed_http_requests_are_rejected(client):
    """!
    @brief IT-06 잘못된 HTTP 요청이 제어 상태를 바꾸지 않는다.
    @req SWR-015
    """
    before = client.request("GET", "/api/status")[1]
    assert client.request("POST", "/api/step", b"{oops")[0] == 400
    assert client.request("POST", "/api/step", {"now_s": "x"})[0] == 400
    assert client.request("GET", "/api/unknown")[0] == 404
    assert client.request("GET", "/api/status")[1] == before


def test_it07_simulator_page_is_served(client):
    """!
    @brief IT-07 시뮬레이터 페이지가 API 경로를 사용하도록 제공된다.
    @req SWR-015
    """
    code, body = client.request("GET", "/")
    assert code == 200
    page = body.decode("utf-8")
    assert all(p in page for p in ("/api/step", "/api/status", "/api/events"))
