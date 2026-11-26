"""!
@brief child_lock.arbiter 단위 테스트 (SWR-001, 003, 004, 007~009, 017~021).
"""

import pytest
from conftest import snapshot

from child_lock.approach_guard import EMPTY_RESULT, GuardResult
from child_lock.arbiter import Context, decide
from child_lock.types import (
    Action,
    CrashStatus,
    DriverRequest,
    InputValidity,
    InvalidRequest,
    Lock,
    Outputs,
    ReasonCode,
    Side,
    Source,
    State,
)

L, R = Lock.LOCK, Lock.RELEASE
BOTH_RELEASED = Outputs(R, R)
BOTH_LOCKED = Outputs(L, L)


def _ctx(snap, **kw):
    """!
    @brief 판정 입력을 만든다. 기본값: VALID, 직전 양쪽 RELEASE.
    @param snap VehicleSnapshot 또는 None
    @param kw Context 필드 덮어쓰기
    @return Context
    """
    values = {
        "snapshot": snap,
        "validity": InputValidity.VALID,
        "previous": BOTH_RELEASED,
        "crash_latched": False,
        "request": None,
        "guard": EMPTY_RESULT,
    }
    values.update(kw)
    return Context(**values)


def _req(side, action):
    """!
    @brief 운전자 요청을 만든다.
    @param side 대상 쪽
    @param action 동작
    @return DriverRequest
    """
    return DriverRequest(side, action, Source.PHYSICAL_BUTTON)


# ---------------------------------------------------------------- 규칙 단독


def test_ignition_off_releases_both_and_sets_off(make_snapshot):
    """!
    @brief IGN OFF 첫 주기에 양쪽 RELEASE, OFF 상태인지 확인한다.
    @req SWR-020
    """
    d = decide(_ctx(make_snapshot(ignition_on=False), previous=BOTH_LOCKED))
    assert (d.outputs, d.state, d.reason_code) == (
        BOTH_RELEASED,
        State.OFF,
        ReasonCode.IGNITION_OFF,
    )


def test_crash_latch_releases_both(make_snapshot):
    """!
    @brief 충돌 래치 시 양쪽 RELEASE인지 확인한다.
    @req SWR-007
    """
    d = decide(_ctx(make_snapshot(), crash_latched=True, previous=BOTH_LOCKED))
    assert (d.outputs, d.reason_code) == (
        BOTH_RELEASED,
        ReasonCode.CRASH_CONFIRMED,
    )


def test_sensor_fault_holds_previous_and_sets_fault(make_snapshot):
    """!
    @brief 센서 고장 시 직전 출력 유지, FAULT 상태인지 확인한다.
    @req SWR-021
    """
    prev = Outputs(L, R)
    d = decide(_ctx(make_snapshot(sensor_fault=True), previous=prev))
    assert (d.outputs, d.state, d.reason_code) == (
        prev,
        State.FAULT,
        ReasonCode.SENSOR_FAULT,
    )


@pytest.mark.parametrize(
    ("validity", "code"),
    [
        (InputValidity.INVALID, ReasonCode.INPUT_INVALID),
        (InputValidity.STALE, ReasonCode.INPUT_STALE),
    ],
)
def test_bad_input_holds_previous_and_degrades(validity, code):
    """!
    @brief 무효·지연 입력에서 직전 출력 유지, DEGRADED인지 확인한다.
    @req SWR-013
    """
    prev = Outputs(R, L)
    d = decide(_ctx(None, validity=validity, previous=prev))
    assert (d.outputs, d.state, d.reason_code, d.input_validity) == (
        prev,
        State.DEGRADED,
        code,
        validity,
    )


@pytest.mark.parametrize(
    ("field", "code"),
    [
        ("fire_detected", ReasonCode.FIRE),
        ("overtemperature_detected", ReasonCode.OVERTEMPERATURE),
        ("adult_present", ReasonCode.ADULT_PRESENT),
    ],
)
def test_emergency_input_releases_both(make_snapshot, field, code):
    """!
    @brief 화재·과온·성인 탑승 각각 단독으로 양쪽 RELEASE인지 확인한다.
    @req SWR-017
    """
    d = decide(_ctx(make_snapshot(**{field: True}), previous=BOTH_LOCKED))
    assert (d.outputs, d.reason_code) == (BOTH_RELEASED, code)


def test_approach_risk_locks_only_that_side(make_snapshot):
    """!
    @brief 오른쪽 접근위험이 오른쪽만 LOCK하는지 확인한다.
    @req SWR-005, SWR-009
    """
    d = decide(_ctx(make_snapshot(rear_right_approach_risk=True)))
    assert (d.outputs, d.reason_code) == (
        Outputs(R, L),
        ReasonCode.APPROACH_RISK,
    )


def test_isofix_locks_only_that_side(make_snapshot):
    """!
    @brief 왼쪽 ISOFIX가 왼쪽만 LOCK하고 오른쪽은 유지하는지 확인한다.
    @req SWR-018, SWR-009
    """
    d = decide(_ctx(make_snapshot(isofix_left=True), previous=Outputs(R, L)))
    assert (d.outputs, d.reason_code) == (Outputs(L, L), ReasonCode.ISOFIX)


@pytest.mark.parametrize(
    ("speed", "expected", "code"),
    [
        (2.9, BOTH_RELEASED, ReasonCode.NO_CHANGE),
        (3.0, BOTH_LOCKED, ReasonCode.AUTO_LOCK_SPEED),
    ],
)
def test_auto_lock_at_3kph_boundary(make_snapshot, speed, expected, code):
    """!
    @brief 3.0 km/h 경계(이상)에서 자동 잠금되는지 확인한다.
    @req SWR-003
    """
    d = decide(_ctx(make_snapshot(vehicle_speed_kph=speed)))
    assert (d.outputs, d.reason_code, d.state) == (
        expected,
        code,
        State.NORMAL,
    )


@pytest.mark.parametrize(
    ("side", "action", "prev", "expected"),
    [
        (Side.LEFT, Action.LOCK, BOTH_RELEASED, Outputs(L, R)),
        (Side.RIGHT, Action.LOCK, BOTH_RELEASED, Outputs(R, L)),
        (Side.ALL, Action.LOCK, BOTH_RELEASED, BOTH_LOCKED),
        (Side.LEFT, Action.UNLOCK, BOTH_LOCKED, Outputs(R, L)),
        (Side.RIGHT, Action.UNLOCK, BOTH_LOCKED, Outputs(L, R)),
        (Side.ALL, Action.UNLOCK, BOTH_LOCKED, BOTH_RELEASED),
    ],
)
def test_driver_command_applies_to_selected_side(
    make_snapshot, side, action, prev, expected
):
    """!
    @brief side 3종 × action 2종이 선택한 쪽에만 반영되는지 확인한다.
    @req SWR-001
    """
    d = decide(_ctx(make_snapshot(), previous=prev, request=_req(side, action)))
    assert (d.outputs, d.reason_code, d.notices) == (
        expected,
        ReasonCode.DRIVER_COMMAND,
        (),
    )


def test_no_rule_keeps_previous(make_snapshot):
    """!
    @brief 해당 규칙이 없으면 직전 출력을 유지하는지 확인한다.
    @req SWR-019
    """
    prev = Outputs(L, R)
    d = decide(_ctx(make_snapshot(), previous=prev))
    assert (d.outputs, d.reason_code) == (prev, ReasonCode.NO_CHANGE)


# ------------------------------------------------- SWR-004 해제 허용 조건


@pytest.mark.parametrize(
    "overrides",
    [
        {"vehicle_speed_kph": 3.0},
        {"rear_left_approach_risk": True},
        {"isofix_left": True},
    ],
)
def test_unlock_rejected_when_condition_violated(make_snapshot, overrides):
    """!
    @brief 주행 중·접근위험·ISOFIX 각각에서 해제가 거절되는지 확인한다.
    @req SWR-004
    """
    d = decide(
        _ctx(
            make_snapshot(**overrides),
            previous=BOTH_LOCKED,
            request=_req(Side.LEFT, Action.UNLOCK),
        )
    )
    assert d.outputs.left is L
    assert ReasonCode.DRIVER_REQUEST_REJECTED in d.notices


# --------------------------------------------- SWR-019 인접 순위 9쌍


# 인접 순위 두 조건을 동시에 준 사례: (이름, Context 인자, 기대 출력, 기대 코드)
s = snapshot
fire = {"fire_detected": True}
PAIR_CASES = [
    (
        "1>2",
        {"snap": s(ignition_on=False), "crash_latched": True},
        BOTH_RELEASED,
        ReasonCode.IGNITION_OFF,
    ),
    (
        "2>3",
        {
            "snap": s(sensor_fault=True),
            "crash_latched": True,
            "previous": BOTH_LOCKED,
        },
        BOTH_RELEASED,
        ReasonCode.CRASH_CONFIRMED,
    ),
    (
        "3>4",
        {"snap": s(sensor_fault=True), "previous": BOTH_LOCKED},
        BOTH_LOCKED,
        ReasonCode.SENSOR_FAULT,
    ),
    (
        "4>5",
        {
            "snap": None,
            "validity": InputValidity.STALE,
            "previous": BOTH_LOCKED,
        },
        BOTH_LOCKED,
        ReasonCode.INPUT_STALE,
    ),
    (
        "5>6",
        {
            "snap": s(rear_left_approach_risk=True, **fire),
            "previous": BOTH_LOCKED,
        },
        BOTH_RELEASED,
        ReasonCode.FIRE,
    ),
    (
        "6>7",
        {"snap": s(rear_left_approach_risk=True, isofix_left=True)},
        Outputs(L, R),
        ReasonCode.APPROACH_RISK,
    ),
    (
        "7>8",
        {"snap": s(isofix_right=True, vehicle_speed_kph=50.0)},
        BOTH_LOCKED,
        ReasonCode.ISOFIX,
    ),
    (
        "8>9",
        {
            "snap": s(vehicle_speed_kph=50.0),
            "request": _req(Side.ALL, Action.UNLOCK),
        },
        BOTH_LOCKED,
        ReasonCode.AUTO_LOCK_SPEED,
    ),
    (
        "9>10",
        {"snap": s(), "request": _req(Side.RIGHT, Action.LOCK)},
        Outputs(R, L),
        ReasonCode.DRIVER_COMMAND,
    ),
]


@pytest.mark.parametrize(
    ("name", "kw", "expected", "code"),
    PAIR_CASES,
    ids=[c[0] for c in PAIR_CASES],
)
def test_higher_rank_wins(name, kw, expected, code):
    """!
    @brief 인접한 두 순위 조건이 함께 있으면 위 순위 결과가 나오는지 본다.
    @req SWR-019
    """
    kw = dict(kw)
    d = decide(_ctx(kw.pop("snap"), **kw))
    assert (d.outputs, d.reason_code) == (expected, code)


# ------------------------------------------------------- 보조 이유 코드


def test_crash_pending_is_notice_without_output_change(make_snapshot):
    """!
    @brief PENDING이 출력을 바꾸지 않고 보조 코드만 남기는지 확인한다.
    @req SWR-008
    """
    prev = Outputs(L, R)
    snap = make_snapshot(crash_status=CrashStatus.PENDING)
    d = decide(_ctx(snap, previous=prev))
    assert (d.outputs, d.reason_code, d.notices) == (
        prev,
        ReasonCode.NO_CHANGE,
        (ReasonCode.CRASH_PENDING,),
    )


def test_override_is_notice_and_output_stays_locked(make_snapshot):
    """!
    @brief override가 기록되지만 위험 동안 LOCK이 유지되는지 확인한다.
    @req SWR-006
    """
    guard = GuardResult(rejected=frozenset(), override=frozenset({Side.RIGHT}))
    d = decide(
        _ctx(
            make_snapshot(rear_right_approach_risk=True),
            request=_req(Side.RIGHT, Action.UNLOCK),
            guard=guard,
        )
    )
    assert d.outputs.right is L
    assert d.notices == (ReasonCode.APPROACH_OVERRIDE_REQUESTED,)


def test_guard_rejection_is_notice(make_snapshot):
    """!
    @brief 접근위험 억제가 거절 보조 코드로 남는지 확인한다.
    @req SWR-005
    """
    guard = GuardResult(rejected=frozenset({Side.RIGHT}), override=frozenset())
    d = decide(
        _ctx(
            make_snapshot(rear_right_approach_risk=True),
            request=_req(Side.RIGHT, Action.UNLOCK),
            guard=guard,
        )
    )
    assert d.notices == (ReasonCode.DRIVER_REQUEST_REJECTED,)


def test_lock_request_matching_forced_lock_is_not_rejection(make_snapshot):
    """!
    @brief 결과가 요청과 같으면 거절로 기록하지 않는지 확인한다.
    @req SWR-004
    """
    d = decide(
        _ctx(
            make_snapshot(vehicle_speed_kph=10.0),
            request=_req(Side.ALL, Action.LOCK),
        )
    )
    assert d.notices == ()


def test_invalid_request_is_notice(make_snapshot):
    """!
    @brief 형식 오류 명령이 출력에 반영되지 않고 보조 코드로 남는지 본다.
    @req SWR-002
    """
    d = decide(_ctx(make_snapshot(), request=InvalidRequest("bad")))
    assert (d.outputs, d.notices) == (
        BOTH_RELEASED,
        (ReasonCode.DRIVER_REQUEST_INVALID,),
    )


def test_notices_keep_defined_order(make_snapshot):
    """!
    @brief 보조 코드가 여러 개일 때 정의된 순서를 지키는지 확인한다.
    @req SWR-010
    """
    snap = make_snapshot(
        crash_status=CrashStatus.PENDING, rear_right_approach_risk=True
    )
    guard = GuardResult(
        rejected=frozenset({Side.RIGHT}), override=frozenset({Side.LEFT})
    )
    d = decide(_ctx(snap, request=_req(Side.RIGHT, Action.UNLOCK), guard=guard))
    assert d.notices == (
        ReasonCode.CRASH_PENDING,
        ReasonCode.APPROACH_OVERRIDE_REQUESTED,
        ReasonCode.DRIVER_REQUEST_REJECTED,
    )


def test_state_is_degraded_when_latched_but_input_bad():
    """!
    @brief 충돌 래치 중 입력 이상이면 해제 유지·DEGRADED인지 확인한다.
    @req SWR-007, SWR-013
    """
    d = decide(
        _ctx(
            None,
            validity=InputValidity.STALE,
            crash_latched=True,
            previous=BOTH_LOCKED,
        )
    )
    assert (d.outputs, d.state, d.reason_code) == (
        BOTH_RELEASED,
        State.DEGRADED,
        ReasonCode.CRASH_CONFIRMED,
    )
