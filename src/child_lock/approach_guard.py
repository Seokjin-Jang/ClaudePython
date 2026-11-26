"""!
@brief 후측방 접근위험 해제 억제와 override 판정 (ASIL B).

접근위험이 TRUE인 쪽의 unlock 요청은 거절하고 첫 억제 시각을 기록한다.
기록 후 10.0 s 이하에 같은 쪽 unlock이 다시 오면 override로 표시한다.
override여도 출력 해제 여부는 arbiter가 정한다 (가정 A-03: LOCK 유지).
요청 시각은 스냅샷 시각을 쓴다 (OEM-IF-004).
"""

from dataclasses import dataclass, replace

from child_lock.input_monitor import age_us
from child_lock.types import Action, Side

# override 인정 구간: 첫 억제 후 10.0 s 이하 (OEM-FR-003, SWR-006)
OVERRIDE_WINDOW_US = 10_000_000

# 쪽 → 해당 쪽 접근위험 스냅샷 필드
_RISK_FIELD = {
    Side.LEFT: "rear_left_approach_risk",
    Side.RIGHT: "rear_right_approach_risk",
}


@dataclass(frozen=True)
class GuardState:
    """!
    @brief 쪽별 첫 억제 시각 [us]. 억제 기록이 없으면 None.
    """

    left: int | None
    right: int | None


@dataclass(frozen=True)
class GuardResult:
    """!
    @brief 이번 주기 억제(rejected)·override 결과. 원소는 Side.
    """

    rejected: frozenset
    override: frozenset


INITIAL_STATE = GuardState(left=None, right=None)
EMPTY_RESULT = GuardResult(rejected=frozenset(), override=frozenset())


def _targets_unlock(request, side):
    """!
    @brief 요청이 해당 쪽에 대한 unlock인지 판정한다.
    @param request DriverRequest 또는 None/InvalidRequest
    @param side Side.LEFT 또는 Side.RIGHT
    @return 해당 쪽 unlock이면 True
    """
    action = getattr(request, "action", None)
    target = getattr(request, "side", None)
    return action is Action.UNLOCK and target in (side, Side.ALL)


def _judge_side(record_us, now_us):
    """!
    @brief 위험 중 unlock 요청 하나를 판정한다.
    @param record_us 첫 억제 시각 [us] 또는 None
    @param now_us 요청 시각 [us]
    @return (override 여부, 새 기록)
    @req SWR-006
    """
    if record_us is not None and now_us - record_us <= OVERRIDE_WINDOW_US:
        return True, None
    return False, now_us


def apply(state, snapshot, request):
    """!
    @brief 한 주기의 접근위험 억제·override를 판정한다.
    @param state 이전 GuardState
    @param snapshot 유효한 VehicleSnapshot
    @param request DriverRequest, InvalidRequest 또는 None
    @return (새 GuardState, GuardResult)
    @req SWR-005, SWR-006, SWR-009
    """
    now_us = age_us(0.0, snapshot.timestamp_s)
    rejected, override = set(), set()
    for side in (Side.LEFT, Side.RIGHT):
        field = side.value
        if not getattr(snapshot, _RISK_FIELD[side]):
            state = replace(state, **{field: None})
        elif _targets_unlock(request, side):
            is_override, record = _judge_side(getattr(state, field), now_us)
            (override if is_override else rejected).add(side)
            state = replace(state, **{field: record})
    return state, GuardResult(frozenset(rejected), frozenset(override))
