"""!
@brief child_lock.replay 단위 테스트 (SWR-016).
"""

import json

from child_lock.replay import digest, main, run

VEHICLE = {
    "timestamp_s": 0.0,
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

VECTORS = [
    {"now_s": 0.0, "vehicle": VEHICLE},
    {
        "now_s": 0.05,
        "command": {"side": "left", "action": "lock", "source": "avn"},
    },
    {"now_s": 0.10, "command": {"side": "nope"}},
]


def test_run_returns_status_per_step():
    """!
    @brief 입력 벡터마다 상태 응답 1건을 돌려주는지 확인한다.
    @req SWR-016
    """
    statuses = run(VECTORS)
    assert [s["lock_left"] for s in statuses] == ["RELEASE", "LOCK", "LOCK"]
    assert statuses[1]["reason_code"] == "DRIVER_COMMAND"


def test_digest_is_stable_and_sensitive_to_input():
    """!
    @brief 같은 입력이면 같은 해시, 다른 입력이면 다른 해시인지 확인한다.
    @req SWR-016
    """
    assert digest(VECTORS) == digest(VECTORS)
    changed = VECTORS[:2] + [{"now_s": 0.10}]
    assert digest(changed) != digest(VECTORS)
    assert len(digest(VECTORS)) == 64


def test_main_repeats_and_reports_single_digest(tmp_path, capsys):
    """!
    @brief 반복 재생 해시가 모두 같으면 종료 코드 0과 해시를 출력하는지 본다.
    @req SWR-016
    """
    path = tmp_path / "v.json"
    path.write_text(json.dumps(VECTORS), encoding="utf-8")
    assert main([str(path), "--repeat", "5"]) == 0
    assert capsys.readouterr().out.strip() == digest(VECTORS)


def test_main_fails_when_digests_differ(tmp_path, monkeypatch):
    """!
    @brief 반복 중 해시가 달라지면 종료 코드 1인지 확인한다.
    @req SWR-016
    """
    path = tmp_path / "v.json"
    path.write_text(json.dumps(VECTORS), encoding="utf-8")
    values = iter(["a", "b"])
    monkeypatch.setattr("child_lock.replay.digest", lambda _v: next(values))
    assert main([str(path), "--repeat", "2"]) == 1
