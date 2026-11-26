"""!
@brief 상태 조회 응답 생성 (QM, SWR-014, OEM-IF-006).
"""

from child_lock.types import ReasonCode

# 평가 전 조회 시 응답 (SWD-001 10절)
_INITIAL = {
    "lock_left": "RELEASE",
    "lock_right": "RELEASE",
    "state": "OFF",
    "input_validity": "STALE",
    "reason_code": ReasonCode.NO_CHANGE.value,
    "priority_reason": ReasonCode.NO_CHANGE.value,
}


def to_status(decision):
    """!
    @brief 결정을 상태 조회 응답으로 바꾼다.
    @param decision Decision 또는 None(평가 전)
    @return 6개 필드 dict. priority_reason은 reason_code와 같다
    @req SWR-014
    """
    if decision is None:
        return dict(_INITIAL)
    return {
        "lock_left": decision.outputs.left.value,
        "lock_right": decision.outputs.right.value,
        "state": decision.state.value,
        "input_validity": decision.input_validity.value,
        "reason_code": decision.reason_code.value,
        "priority_reason": decision.reason_code.value,
    }
