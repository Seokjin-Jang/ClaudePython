"""!
@brief 통합 시험: 프로세스 재기동, 결정론 재생, 평가 시간.
"""

import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from it_support import SRC, vehicle

from child_lock.controller import ChildLockController

VECTORS = Path(__file__).resolve().parents[1] / "vectors" / "uc_all.json"


def _free_port():
    """!
    @brief 사용 가능한 임시 포트를 얻는다.
    @return int
    """
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _start_server(port, cwd):
    """!
    @brief 별도 프로세스로 서버를 띄우고 응답할 때까지 기다린다.
    @param port 포트
    @param cwd 작업 폴더
    @return subprocess.Popen
    """
    env = dict(os.environ, PYTHONPATH=str(SRC))
    proc = subprocess.Popen(
        [sys.executable, "-m", "child_lock.web.server", "--port", str(port)],
        cwd=cwd,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/api/status")
            return proc
        except OSError:
            time.sleep(0.1)
    proc.kill()
    raise RuntimeError("server did not start")


def _post_step(port, body):
    """!
    @brief 별도 프로세스 서버에 /api/step을 보낸다.
    """
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/api/step",
        data=json.dumps(body).encode("utf-8"),
        method="POST",
    )
    urllib.request.urlopen(req, timeout=5).close()


def _events(port):
    """!
    @brief 별도 프로세스 서버의 이벤트 목록을 읽는다.
    """
    url = f"http://127.0.0.1:{port}/api/events"
    with urllib.request.urlopen(url, timeout=5) as resp:
        return json.loads(resp.read())


def test_it08_events_are_volatile_and_no_files_written(tmp_path):
    """!
    @brief IT-08 재기동 후 이벤트 0건, 작업 폴더에 파일이 생기지 않는다.
    @req SWR-012
    """
    port = _free_port()
    proc = _start_server(port, tmp_path)
    try:
        for i in range(3):
            _post_step(port, {"now_s": i * 0.05, "vehicle": vehicle(i * 0.05)})
        assert len(_events(port)) == 3
    finally:
        proc.terminate()
        proc.wait(timeout=10)
    proc = _start_server(port, tmp_path)
    try:
        assert _events(port) == []
    finally:
        proc.terminate()
        proc.wait(timeout=10)
    assert list(tmp_path.iterdir()) == []


def test_it09_replay_1000_times_gives_one_digest():
    """!
    @brief IT-09 UC 전체 입력 벡터를 1,000회 재생해 해시가 하나다.
    @req SWR-016
    """
    env = dict(os.environ, PYTHONPATH=str(SRC))
    result = subprocess.run(
        [sys.executable, "-m", "child_lock.replay", str(VECTORS)]
        + ["--repeat", "1000"],
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert len(result.stdout.strip()) == 64


def test_it10_one_evaluation_is_far_below_cycle():
    """!
    @brief IT-10 평가 1회 평균이 1 ms 미만이다 (주기 50 ms, SWA-001 5절).
    @req SWR-016
    """
    ctrl = ChildLockController()
    count = 2000
    start = time.perf_counter()
    for i in range(count):
        t = i * 0.05
        ctrl.evaluate(t, vehicle(t, vehicle_speed_kph=float(i % 10)))
    mean_ms = (time.perf_counter() - start) / count * 1000
    assert mean_ms < 1.0, f"{mean_ms:.3f} ms"
