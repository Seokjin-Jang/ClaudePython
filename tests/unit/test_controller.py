"""!
@brief child_lock.controller 단위 테스트 (SWR-007, 013, 016, 020, 021).
"""

from child_lock.controller import ChildLockController
from child_lock.types import (
    Action,
    DriverRequest,
    InputValidity,
    Lock,
    Outputs,
    ReasonCode,
    Side,
    Source,
    State,
)

L, R = Lock.LOCK, Lock.RELEASE


def _vehicle(t, **overrides):
    """!
    @brief 정상 원시 차량 입력을 만든다.
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


def _unlock(side=Side.ALL):
    """!
    @brief unlock 요청을 만든다.
    """
    return DriverRequest(side, Action.UNLOCK, Source.AVN)


def test_initial_state_has_no_decision_and_first_cycle_without_data():
    """!
    @brief 입력 없이 평가하면 직전(초기) RELEASE 유지·STALE인지 확인한다.
    @req SWR-013
    """
    ctrl = ChildLockController()
    assert ctrl.last_decision is None
    d = ctrl.evaluate(0.0)
    assert (d.outputs, d.input_validity, d.state) == (
        Outputs(R, R),
        InputValidity.STALE,
        State.DEGRADED,
    )
    assert ctrl.last_decision == d


def test_crash_latch_holds_release_until_ignition_off():
    """!
    @brief 충돌 확정 후 NONE이 와도 해제 유지, IGN OFF 후 래치가 풀리는지 본다.
    @req SWR-007, SWR-020
    """
    ctrl = ChildLockController()
    ctrl.evaluate(0.0, _vehicle(0.0, vehicle_speed_kph=50.0))
    d = ctrl.evaluate(
        0.05, _vehicle(0.05, crash_status="CONFIRMED", vehicle_speed_kph=50.0)
    )
    assert (d.outputs, d.reason_code) == (
        Outputs(R, R),
        ReasonCode.CRASH_CONFIRMED,
    )
    d = ctrl.evaluate(0.10, _vehicle(0.10, vehicle_speed_kph=50.0))
    assert d.reason_code is ReasonCode.CRASH_CONFIRMED
    ctrl.evaluate(0.15, _vehicle(0.15, ignition_on=False))
    d = ctrl.evaluate(0.20, _vehicle(0.20, vehicle_speed_kph=50.0))
    assert (d.outputs, d.reason_code) == (
        Outputs(L, L),
        ReasonCode.AUTO_LOCK_SPEED,
    )


def test_invalid_input_keeps_previous_snapshot_and_outputs():
    """!
    @brief 무효 입력 주기에 직전 출력 유지, 다음 정상 주기에 복귀하는지 본다.
    @req SWR-013
    """
    ctrl = ChildLockController()
    ctrl.evaluate(0.0, _vehicle(0.0, vehicle_speed_kph=10.0))
    d = ctrl.evaluate(0.05, _vehicle(0.05, vehicle_speed_kph=300.1))
    assert (d.outputs, d.input_validity, d.reason_code) == (
        Outputs(L, L),
        InputValidity.INVALID,
        ReasonCode.INPUT_INVALID,
    )
    d = ctrl.evaluate(0.10)
    assert d.input_validity is InputValidity.VALID


def test_input_becomes_stale_after_200ms_without_update():
    """!
    @brief 갱신 없이 0.25 s가 지나면 DEGRADED가 되는지 확인한다.
    @req SWR-013
    """
    ctrl = ChildLockController()
    ctrl.evaluate(0.0, _vehicle(0.0))
    assert ctrl.evaluate(0.20).input_validity is InputValidity.VALID
    d = ctrl.evaluate(0.25)
    assert (d.input_validity, d.state) == (
        InputValidity.STALE,
        State.DEGRADED,
    )


def test_override_flow_through_guard_state():
    """!
    @brief 억제 후 10 s 이내 재입력이 override 보조 코드로 남는지 확인한다.
    @req SWR-005, SWR-006
    """
    ctrl = ChildLockController()
    risk = {"rear_right_approach_risk": True}
    d = ctrl.evaluate(1.0, _vehicle(1.0, **risk), _unlock(Side.RIGHT))
    assert d.notices == (ReasonCode.DRIVER_REQUEST_REJECTED,)
    d = ctrl.evaluate(5.0, _vehicle(5.0, **risk), _unlock(Side.RIGHT))
    assert d.notices == (ReasonCode.APPROACH_OVERRIDE_REQUESTED,)
    assert d.outputs.right is L


def test_ignition_off_resets_guard_record():
    """!
    @brief IGN OFF 후 이전 억제 기록으로 override가 나는 결함을 잡는다.
    @req SWR-020
    """
    ctrl = ChildLockController()
    risk = {"rear_right_approach_risk": True}
    ctrl.evaluate(1.0, _vehicle(1.0, **risk), _unlock(Side.RIGHT))
    ctrl.evaluate(2.0, _vehicle(2.0, ignition_on=False, **risk))
    d = ctrl.evaluate(3.0, _vehicle(3.0, **risk), _unlock(Side.RIGHT))
    assert d.notices == (ReasonCode.DRIVER_REQUEST_REJECTED,)


def test_record_called_after_decision_with_now():
    """!
    @brief 기록 콜백이 판정 결과와 평가 시각으로 호출되는지 확인한다.
    @req SWR-010
    """
    calls = []
    ctrl = ChildLockController(record=lambda d, t: calls.append((d, t)))
    d = ctrl.evaluate(0.5, _vehicle(0.5))
    assert calls == [(d, 0.5)]


def test_record_failure_does_not_change_decision():
    """!
    @brief 기록 콜백 예외가 이미 갱신된 판정을 되돌리지 않는지 확인한다.
    @req SWR-016
    """

    def broken(_d, _t):
        """!
        @brief 항상 실패하는 기록 함수.
        """
        raise RuntimeError("log failure")

    ctrl = ChildLockController(record=broken)
    try:
        ctrl.evaluate(0.0, _vehicle(0.0, vehicle_speed_kph=10.0))
    except RuntimeError:
        pass
    assert ctrl.last_decision.outputs == Outputs(L, L)


def test_same_inputs_give_same_decisions():
    """!
    @brief 같은 입력 순서면 같은 결정이 나오는지 확인한다.
    @req SWR-016
    """
    steps = [
        (0.0, _vehicle(0.0), None),
        (0.05, _vehicle(0.05), _unlock()),
        (0.30, None, None),
        (0.35, _vehicle(0.35, isofix_left=True), None),
    ]

    def run():
        """!
        @brief 새 컨트롤러로 steps를 재생한다.
        @return 결정 목록
        """
        ctrl = ChildLockController()
        return [ctrl.evaluate(t, v, r) for t, v, r in steps]

    assert run() == run()
