"""!
@brief child_lock.status 단위 테스트 (SWR-014).
"""

from child_lock.status import to_status
from child_lock.types import (
    Decision,
    InputValidity,
    Lock,
    Outputs,
    ReasonCode,
    State,
)


def test_status_has_six_fields_and_priority_reason_mirrors_reason():
    """!
    @brief 상태 응답 6필드와 priority_reason = reason_code 매핑을 확인한다.
    @req SWR-014
    """
    d = Decision(
        Outputs(Lock.RELEASE, Lock.LOCK),
        State.DEGRADED,
        ReasonCode.INPUT_STALE,
        InputValidity.STALE,
    )
    assert to_status(d) == {
        "lock_left": "RELEASE",
        "lock_right": "LOCK",
        "state": "DEGRADED",
        "input_validity": "STALE",
        "reason_code": "INPUT_STALE",
        "priority_reason": "INPUT_STALE",
    }


def test_status_before_first_evaluation():
    """!
    @brief 평가 전 조회 시 정의된 초기 응답을 돌려주는지 확인한다.
    @req SWR-014
    """
    assert to_status(None) == {
        "lock_left": "RELEASE",
        "lock_right": "RELEASE",
        "state": "OFF",
        "input_validity": "STALE",
        "reason_code": "NO_CHANGE",
        "priority_reason": "NO_CHANGE",
    }
