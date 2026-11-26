"""!
@brief Web 시뮬레이터 서버 (QM, SWR-014, 015).

표준 라이브러리 http.server만 쓴다 (DEC-02). 요청 처리 로직은 HTTP와
분리된 App.handle에 두어 단위 시험한다. 컨트롤러 접근은 Lock으로
직렬화한다.

실행: python -m child_lock.web.server --port 8000 [--tick]
"""

import argparse
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from child_lock.controller import ChildLockController
from child_lock.driver_request import parse_command
from child_lock.event_log import EventLog
from child_lock.status import to_status

# 주기 tick 간격 = 평가 주기 (가정 A-01)
CYCLE_S = 0.05
_INDEX = Path(__file__).with_name("static") / "index.html"
_JSON = "application/json; charset=utf-8"


def _json_response(obj, code=200):
    """!
    @brief 객체를 JSON 응답으로 만든다. 직렬화 실패는 500.
    @param obj 응답 객체
    @param code 성공 시 상태 코드
    @return (상태 코드, 형식, 본문)
    @req SWR-014
    """
    try:
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    except (TypeError, ValueError):
        return 500, _JSON, b'{"error":"serialization failed"}'
    return code, _JSON, body


def _error(code, message):
    """!
    @brief 오류 응답을 만든다.
    """
    return _json_response({"error": message}, code)


class App:
    """!
    @brief HTTP와 분리된 시뮬레이터 요청 처리기.
    """

    def __init__(self, clock=time.monotonic, status_fn=to_status):
        """!
        @brief 컨트롤러와 이벤트 저장소를 만든다.
        @param clock 단조 시계 함수 (시험 시 교체)
        @param status_fn 상태 응답 생성 함수 (시험 시 교체)
        """
        self._clock = clock
        self._start = clock()
        self._status_fn = status_fn
        self._log = EventLog()
        self._ctrl = ChildLockController(record=self._log.record)
        self._lock = threading.Lock()

    def now(self):
        """!
        @brief 서버 시작 후 경과 시간 [s].
        """
        return self._clock() - self._start

    def tick(self):
        """!
        @brief 서버 시계로 평가 주기 1회를 실행한다 (지연 감지용).
        """
        with self._lock:
            self._ctrl.evaluate(self.now())

    def _status(self):
        """!
        @brief 현재 상태 응답.
        """
        return _json_response(self._status_fn(self._ctrl.last_decision))

    def _step(self, body):
        """!
        @brief 입력 주입 후 평가하고 상태를 돌려준다.
        @param body 요청 본문 bytes
        @return 응답 튜플
        @req SWR-015
        """
        try:
            data = json.loads(body.decode("utf-8") or "{}")
        except (UnicodeDecodeError, ValueError):
            return _error(400, "body is not JSON")
        if not isinstance(data, dict):
            return _error(400, "body must be an object")
        now_s = data.get("now_s", self.now())
        if type(now_s) not in (int, float):
            return _error(400, "now_s must be a number")
        command = data.get("command")
        request = parse_command(command) if command is not None else None
        with self._lock:
            self._ctrl.evaluate(now_s, data.get("vehicle"), request)
            return self._status()

    def handle(self, method, path, body):
        """!
        @brief 요청 하나를 처리한다.
        @param method HTTP 메서드
        @param path 경로
        @param body 요청 본문 bytes
        @return (상태 코드, Content-Type, 본문 bytes)
        @req SWR-014, SWR-015
        """
        if (method, path) == ("GET", "/"):
            return 200, "text/html; charset=utf-8", _INDEX.read_bytes()
        if (method, path) == ("GET", "/api/status"):
            with self._lock:
                return self._status()
        if (method, path) == ("GET", "/api/events"):
            return _json_response(self._log.items())
        if (method, path) == ("POST", "/api/step"):
            return self._step(body)
        return _error(404, "not found")


class Ticker:
    """!
    @brief 일정 간격으로 App.tick을 호출하는 백그라운드 스레드.
    """

    def __init__(self, app, interval_s=CYCLE_S):
        """!
        @param app 대상 App
        @param interval_s 호출 간격 [s]
        """
        self._app = app
        self._interval = interval_s
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _run(self):
        """!
        @brief stop될 때까지 주기적으로 tick한다.
        """
        while not self._stop.wait(self._interval):
            self._app.tick()

    def start(self):
        """!
        @brief 스레드를 시작한다.
        """
        self._thread.start()

    def stop(self):
        """!
        @brief 스레드를 멈추고 끝날 때까지 기다린다.
        """
        self._stop.set()
        self._thread.join(timeout=5)


def _handler_for(app):
    """!
    @brief App에 요청을 넘기는 HTTP 핸들러 클래스를 만든다.
    @param app App
    @return BaseHTTPRequestHandler 하위 클래스
    """

    class Handler(BaseHTTPRequestHandler):
        """!
        @brief HTTP 요청을 App.handle로 넘긴다.
        """

        def _reply(self, method):
            """!
            @brief 본문을 읽고 App 응답을 보낸다.
            """
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length) if length else b""
            code, ctype, payload = app.handle(method, self.path, body)
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self):  # noqa: N802 - http.server 규약 이름
            """!
            @brief GET 처리.
            """
            self._reply("GET")

        def do_POST(self):  # noqa: N802 - http.server 규약 이름
            """!
            @brief POST 처리.
            """
            self._reply("POST")

        def log_message(self, *_args):
            """!
            @brief 요청 로그를 남기지 않는다 (개인정보 최소화, SWR-011).
            """

    return Handler


def build(argv):
    """!
    @brief 명령줄 인자로 서버(와 선택적 Ticker)를 만든다.
    @param argv 명령줄 인자
    @return (ThreadingHTTPServer, Ticker 또는 None)
    """
    parser = argparse.ArgumentParser(description="차일드락 Web 시뮬레이터")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--tick", action="store_true", help="50 ms 주기 평가")
    args = parser.parse_args(argv)
    app = App()
    server = ThreadingHTTPServer((args.host, args.port), _handler_for(app))
    ticker = Ticker(app) if args.tick else None
    if ticker:
        ticker.start()
    return server, ticker


# 스크립트 직접 실행 진입점: 서버 생성은 build()로 시험하고, 여기서는
# 종료될 때까지 요청을 기다리기만 하므로 제외
if __name__ == "__main__":  # pragma: no cover
    httpd, _ = build(None)
    print(f"http://{httpd.server_address[0]}:{httpd.server_address[1]}/")
    httpd.serve_forever()
