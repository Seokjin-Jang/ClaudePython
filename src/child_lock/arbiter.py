"""!
@brief 출력 우선순위 판정 (ASIL B, SWR-019).

우선순위를 if/elif 사슬이 아니라 순서 있는 규칙 표(RULES)로 표현한다
(SWA-001 AD-01). 쪽(left/right)마다 표를 위에서부터 보며 처음 해당하는
규칙으로 출력을 정한다. 순서를 바꿔야 하면(OEM 질의 Q-01) 표만 고친다.

SWR-004(운전자 해제 허용 조건)는 별도 분기 없이 순위로 보장된다:
주행(8), 접근위험(6), ISOFIX(7)가 운전자 명령(9)보다 위에 있다.
"""

from collections.abc import Callable
from dataclasses import dataclass

from child_lock.types import (
    Action,
    CrashStatus,
    Decision,
    DriverRequest,
    InputValidity,
    InvalidRequest,
    Lock,
    Outputs,
    ReasonCode,
    Side,
    State,
)

# 자동 잠금 차속: 3.0 km/h 이상 (OEM-FR-002, SWR-003)
AUTO_LOCK_SPEED_KPH = 3.0

_SIDES = (Side.LEFT, Side.RIGHT)
_DRIVER_RANK = 9

# 강제 해제 입력과 이유 코드 — 동시 TRUE면 이 순서로 코드 선택 (SWR-017)
_EMERGENCY = (
    ("fire_detected", ReasonCode.FIRE),
    ("overtemperature_detected", ReasonCode.OVERTEMPERATURE),
    ("adult_present", ReasonCode.ADULT_PRESENT),
)
_RISK = {
    Side.LEFT: "rear_left_approach_risk",
    Side.RIGHT: "rear_right_approach_risk",
}
_ISOFIX = {Side.LEFT: "isofix_left", Side.RIGHT: "isofix_right"}


@dataclass(frozen=True)
class Context:
    """!
    @brief 판정 입력. snapshot은 validity가 VALID일 때만 값이 있다.
    """

    snapshot: object
    validity: InputValidity
    previous: Outputs
    crash_latched: bool
    request: DriverRequest | InvalidRequest | None
    guard: object


@dataclass(frozen=True)
class Rule:
    """!
    @brief 우선순위 규칙 하나.

    applies(ctx, side)가 참이면 output(ctx, side)를 적용한다.
    output이 None이면 직전 확정 출력을 유지한다.
    """

    rank: int
    applies: Callable
    output: Callable
    code: Callable


def _const(value):
    """!
    @brief 인자를 무시하고 value를 돌려주는 함수를 만든다.
    @param value 돌려줄 값
    @return 함수
    """
    return lambda *_: value


def _snap_flag(name):
    """!
    @brief 스냅샷 불리언 필드가 참인지 보는 조건 함수를 만든다.
    @param name 필드명
    @return (ctx, side) → bool
    """
    return lambda ctx, _side: bool(ctx.snapshot and getattr(ctx.snapshot, name))


def _side_flag(fields):
    """!
    @brief 쪽별 스냅샷 필드 조건 함수를 만든다.
    @param fields {Side: 필드명}
    @return (ctx, side) → bool
    """
    return lambda ctx, side: bool(
        ctx.snapshot and getattr(ctx.snapshot, fields[side])
    )


def _ignition_off(ctx, _side):
    """!
    @brief 유효 입력에서 IGN OFF인지 판정한다 (rank 1).
    """
    return bool(ctx.snapshot) and not ctx.snapshot.ignition_on


def _emergency_code(ctx):
    """!
    @brief 참인 강제 해제 입력 중 첫 번째의 이유 코드 (rank 5).
    @return ReasonCode 또는 None
    """
    for name, code in _EMERGENCY:
        if ctx.snapshot and getattr(ctx.snapshot, name):
            return code
    return None


def _bad_input_code(ctx):
    """!
    @brief 입력 이상 종류에 맞는 이유 코드 (rank 4).
    """
    if ctx.validity is InputValidity.INVALID:
        return ReasonCode.INPUT_INVALID
    return ReasonCode.INPUT_STALE


def _moving(ctx, _side):
    """!
    @brief 차속이 자동 잠금 기준 이상인지 판정한다 (rank 8).
    """
    snap = ctx.snapshot
    return bool(snap) and snap.vehicle_speed_kph >= AUTO_LOCK_SPEED_KPH


def _targets(request, side):
    """!
    @brief 유효한 운전자 요청이 해당 쪽을 대상으로 하는지 판정한다.
    """
    return isinstance(request, DriverRequest) and request.side in (
        side,
        Side.ALL,
    )


def _requested_lock(ctx, _side):
    """!
    @brief 운전자 요청 동작에 해당하는 출력 (rank 9).
    """
    return Lock.LOCK if ctx.request.action is Action.LOCK else Lock.RELEASE


# SWR-019 우선순위 표 — 위가 우선
RULES = (
    Rule(
        1, _ignition_off, _const(Lock.RELEASE), _const(ReasonCode.IGNITION_OFF)
    ),
    Rule(
        2,
        lambda ctx, _s: ctx.crash_latched,
        _const(Lock.RELEASE),
        _const(ReasonCode.CRASH_CONFIRMED),
    ),
    Rule(
        3,
        _snap_flag("sensor_fault"),
        _const(None),
        _const(ReasonCode.SENSOR_FAULT),
    ),
    Rule(
        4,
        lambda ctx, _s: ctx.validity is not InputValidity.VALID,
        _const(None),
        _bad_input_code,
    ),
    Rule(
        5,
        lambda ctx, _s: _emergency_code(ctx) is not None,
        _const(Lock.RELEASE),
        _emergency_code,
    ),
    Rule(
        6,
        _side_flag(_RISK),
        _const(Lock.LOCK),
        _const(ReasonCode.APPROACH_RISK),
    ),
    Rule(7, _side_flag(_ISOFIX), _const(Lock.LOCK), _const(ReasonCode.ISOFIX)),
    Rule(8, _moving, _const(Lock.LOCK), _const(ReasonCode.AUTO_LOCK_SPEED)),
    Rule(
        _DRIVER_RANK,
        lambda ctx, side: _targets(ctx.request, side),
        _requested_lock,
        _const(ReasonCode.DRIVER_COMMAND),
    ),
    Rule(10, _const(True), _const(None), _const(ReasonCode.NO_CHANGE)),
)


def _first_rule(ctx, side):
    """!
    @brief 해당 쪽에 처음으로 해당하는 규칙을 찾는다.
    @param ctx Context
    @param side Side.LEFT 또는 Side.RIGHT
    @return Rule (rank 10이 항상 해당하므로 반드시 있음)
    """
    return next(rule for rule in RULES if rule.applies(ctx, side))


def _state(ctx):
    """!
    @brief SW 상태를 정한다 (SWA-001 3.2).
    @param ctx Context
    @return State
    """
    if _ignition_off(ctx, None):
        return State.OFF
    if ctx.snapshot and ctx.snapshot.sensor_fault:
        return State.FAULT
    if ctx.validity is not InputValidity.VALID:
        return State.DEGRADED
    return State.NORMAL


def _request_overruled(ctx, per_side, outputs):
    """!
    @brief 운전자 요청이 상위 규칙 때문에 반영되지 않았는지 판정한다.

    결과가 요청과 같으면(예: 주행 중 lock 요청) 거절이 아니다.
    override로 처리된 쪽은 override 코드로 기록하므로 제외한다.
    @return 반영되지 않은 대상 쪽이 있으면 True
    @req SWR-004
    """
    if not isinstance(ctx.request, DriverRequest):
        return False
    wanted = _requested_lock(ctx, None)
    return any(
        _targets(ctx.request, side)
        and side not in ctx.guard.override
        and per_side[side].rank != _DRIVER_RANK
        and outputs.get(side) is not wanted
        for side in _SIDES
    )


def _notices(ctx, per_side, outputs):
    """!
    @brief 보조 이유 코드를 정의된 순서로 모은다 (SWR-010).
    @return tuple[ReasonCode, ...]
    @req SWR-002, SWR-005, SWR-006, SWR-008
    """
    snap = ctx.snapshot
    checks = (
        (
            bool(snap) and snap.crash_status is CrashStatus.PENDING,
            ReasonCode.CRASH_PENDING,
        ),
        (bool(ctx.guard.override), ReasonCode.APPROACH_OVERRIDE_REQUESTED),
        (
            bool(ctx.guard.rejected)
            or _request_overruled(ctx, per_side, outputs),
            ReasonCode.DRIVER_REQUEST_REJECTED,
        ),
        (
            isinstance(ctx.request, InvalidRequest),
            ReasonCode.DRIVER_REQUEST_INVALID,
        ),
    )
    return tuple(code for hit, code in checks if hit)


def decide(ctx):
    """!
    @brief 한 평가 주기의 출력·상태·이유 코드를 결정한다.
    @param ctx Context
    @return Decision
    @req SWR-019
    """
    per_side = {side: _first_rule(ctx, side) for side in _SIDES}
    chosen = {
        side: per_side[side].output(ctx, side) or ctx.previous.get(side)
        for side in _SIDES
    }
    outputs = Outputs(left=chosen[Side.LEFT], right=chosen[Side.RIGHT])
    primary = min(per_side.values(), key=lambda rule: rule.rank)
    return Decision(
        outputs=outputs,
        state=_state(ctx),
        reason_code=primary.code(ctx),
        input_validity=ctx.validity,
        notices=_notices(ctx, per_side, outputs),
    )
