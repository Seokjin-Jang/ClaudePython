"""!
@brief 통합 시험 공용 도우미: 원시 입력 생성과 HTTP 클라이언트.
"""

import json
import urllib.error
import urllib.request
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src"


def vehicle(t, **overrides):
    """!
    @brief 정차·IGN ON·이상 없음 원시 차량 입력을 만든다.
    @param t timestamp_s
    @param overrides 바꿀 필드
    @return dict
    """
    raw = {
        "timestamp_s": t,
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
    raw.update(overrides)
    return raw


class Client:
    """!
    @brief 시험 대상 서버에 요청을 보내는 HTTP 클라이언트.
    """

    def __init__(self, base):
        """!
        @param base 서버 기본 URL
        """
        self.base = base

    def request(self, method, path, body=None):
        """!
        @brief 요청을 보내고 (상태 코드, 파싱된 본문)을 돌려준다.
        @param method HTTP 메서드
        @param path 경로
        @param body JSON으로 보낼 객체 또는 원시 bytes
        @return (int, object | bytes)
        """
        data = body
        if body is not None and not isinstance(body, bytes):
            data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(self.base + path, data=data, method=method)
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                raw = resp.read()
                code = resp.status
        except urllib.error.HTTPError as err:
            raw, code = err.read(), err.code
        try:
            return code, json.loads(raw)
        except ValueError:
            return code, raw

    def step(self, now_s, vehicle_raw=None, command=None):
        """!
        @brief /api/step으로 평가 주기 1회를 실행한다.
        @return 상태 응답 dict
        """
        body = {"now_s": now_s}
        if vehicle_raw is not None:
            body["vehicle"] = vehicle_raw
        if command is not None:
            body["command"] = command
        code, status = self.request("POST", "/api/step", body)
        assert code == 200, status
        return status
