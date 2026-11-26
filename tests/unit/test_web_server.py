"""!
@brief child_lock.web.server 단위 테스트 (SWR-014, 015).
"""

import json
import threading
import time
import urllib.request

from child_lock.web.server import App, Ticker, build

VEHICLE = {
    "timestamp_s": 1.0,
    "vehicle_speed_kph": 10.0,
    "gear": "D",
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


class FakeClock:
    """!
    @brief 시험용 고정 시계.
    """

    def __init__(self):
        """!
        @brief 0.0에서 시작한다.
        """
        self.t = 0.0

    def __call__(self):
        """!
        @brief 현재 시각을 돌려준다.
        @return float
        """
        return self.t


def _json(response):
    """!
    @brief handle 결과에서 JSON 본문을 꺼낸다.
    @param response (상태 코드, 형식, 본문)
    @return 파싱된 객체
    """
    return json.loads(response[2].decode("utf-8"))


def _post(app, body):
    """!
    @brief /api/step POST를 보낸다.
    """
    return app.handle("POST", "/api/step", json.dumps(body).encode("utf-8"))


def test_index_page_is_served():
    """!
    @brief 시뮬레이터 페이지를 HTML로 제공하는지 확인한다.
    @req SWR-015
    """
    code, ctype, body = App().handle("GET", "/", b"")
    assert (code, ctype) == (200, "text/html; charset=utf-8")
    assert b"/api/step" in body


def test_step_then_status_reflect_last_decision():
    """!
    @brief 입력 주입 결과가 상태 조회와 일치하는지 확인한다.
    @req SWR-014, SWR-015
    """
    app = App()
    step = _post(app, {"now_s": 1.0, "vehicle": VEHICLE})
    status = app.handle("GET", "/api/status", b"")
    assert step[0] == status[0] == 200
    assert _json(step) == _json(status)
    assert _json(status)["reason_code"] == "AUTO_LOCK_SPEED"


def test_step_uses_server_clock_and_parses_command():
    """!
    @brief now_s가 없으면 서버 시계를 쓰고, 명령을 해석해 넘기는지 본다.
    @req SWR-002, SWR-015
    """
    clock = FakeClock()
    app = App(clock=clock)
    clock.t = 1.0
    stopped = dict(VEHICLE, vehicle_speed_kph=0.0)
    _post(
        app,
        {
            "vehicle": stopped,
            "command": {"side": "left", "action": "lock", "source": "voice"},
        },
    )
    status = _json(app.handle("GET", "/api/status", b""))
    assert (status["lock_left"], status["input_validity"]) == ("LOCK", "VALID")


def test_events_endpoint_lists_recorded_events():
    """!
    @brief 이벤트 조회가 기록된 이벤트를 돌려주는지 확인한다.
    @req SWR-010, SWR-015
    """
    app = App()
    _post(app, {"now_s": 1.0, "vehicle": VEHICLE})
    events = _json(app.handle("GET", "/api/events", b""))
    assert [e["event_id"] for e in events] == [1]


def test_bad_requests_get_400_or_404():
    """!
    @brief 잘못된 본문·시각은 400, 없는 경로는 404인지 확인한다.
    @req SWR-015
    """
    app = App()
    assert app.handle("POST", "/api/step", b"{not json")[0] == 400
    assert app.handle("POST", "/api/step", b"[1]")[0] == 400
    assert _post(app, {"now_s": "soon"})[0] == 400
    assert app.handle("GET", "/nope", b"")[0] == 404
    assert app.handle("DELETE", "/api/status", b"")[0] == 404


def test_status_serialization_failure_returns_500():
    """!
    @brief 직렬화 실패 시 HTTP 500을 돌려주는지 확인한다.
    @req SWR-014
    """
    app = App(status_fn=lambda _d: {"bad": object()})
    assert app.handle("GET", "/api/status", b"")[0] == 500


def test_ticker_evaluates_periodically_and_stops():
    """!
    @brief 주기 tick이 평가를 반복하고 stop 후 멈추는지 확인한다.
    @req SWR-013
    """
    app = App()
    ticker = Ticker(app, interval_s=0.01)
    ticker.start()
    deadline = time.monotonic() + 2.0
    while app.handle("GET", "/api/events", b"")[2] == b"[]":
        if time.monotonic() > deadline:
            break
        time.sleep(0.01)
    ticker.stop()
    assert _json(app.handle("GET", "/api/events", b""))


def test_build_serves_http_on_ephemeral_port():
    """!
    @brief build가 만든 서버가 실제 HTTP 요청에 응답하는지 확인한다.
    @req SWR-014
    """
    server, ticker = build(["--port", "0", "--tick", "--host", "127.0.0.1"])
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        url = f"http://127.0.0.1:{port}/api/status"
        with urllib.request.urlopen(url, timeout=5) as resp:
            assert resp.status == 200
            assert "lock_left" in json.loads(resp.read())
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/step", data=b"{}", method="POST"
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            assert resp.status == 200
    finally:
        ticker.stop()
        server.shutdown()
        server.server_close()


def test_build_without_tick_returns_no_ticker():
    """!
    @brief --tick 없이는 주기 평가를 시작하지 않는지 확인한다 (AD-04).
    """
    server, ticker = build(["--port", "0"])
    server.server_close()
    assert ticker is None
