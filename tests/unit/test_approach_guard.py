"""!
@brief child_lock.approach_guard 단위 테스트 (SWR-005, 006, 009).
"""

from child_lock.approach_guard import INITIAL_STATE, GuardState, apply
from child_lock.types import Action, DriverRequest, Side, Source


def _unlock(side):
    """!
    @brief 운전자 unlock 요청을 만든다.
    @param side 대상 쪽
    @return DriverRequest
    """
    return DriverRequest(side, Action.UNLOCK, Source.AVN)


def _right_risk(make_snapshot, t):
    """!
    @brief 오른쪽 접근위험 TRUE 스냅샷을 만든다.
    @param make_snapshot 스냅샷 도우미
    @param t 시각 [s]
    @return VehicleSnapshot
    """
    return make_snapshot(timestamp_s=t, rear_right_approach_risk=True)


def test_first_unlock_under_risk_is_rejected_and_remembered(make_snapshot):
    """!
    @brief 접근위험 중 첫 해제 요청을 거절하고 시각을 기록하는지 확인한다.
    @req SWR-005
    """
    state, result = apply(
        INITIAL_STATE, _right_risk(make_snapshot, 1.0), _unlock(Side.RIGHT)
    )
    assert result.rejected == {Side.RIGHT}
    assert result.override == frozenset()
    assert state == GuardState(left=None, right=1_000_000)


def test_reinput_within_10s_is_override(make_snapshot):
    """!
    @brief 10.0 s 경계(이하)의 재입력을 override로 처리하는지 확인한다.
    @req SWR-006
    """
    state, _ = apply(
        INITIAL_STATE, _right_risk(make_snapshot, 1.0), _unlock(Side.RIGHT)
    )
    state, result = apply(
        state, _right_risk(make_snapshot, 11.0), _unlock(Side.RIGHT)
    )
    assert result.override == {Side.RIGHT}
    assert result.rejected == frozenset()
    assert state.right is None


def test_reinput_after_10s_is_new_rejection(make_snapshot):
    """!
    @brief 10.05 s 재입력은 override가 아니라 새 억제로 시작하는지 확인한다.
    @req SWR-006
    """
    state, _ = apply(
        INITIAL_STATE, _right_risk(make_snapshot, 1.0), _unlock(Side.RIGHT)
    )
    state, result = apply(
        state, _right_risk(make_snapshot, 11.05), _unlock(Side.RIGHT)
    )
    assert result.rejected == {Side.RIGHT}
    assert result.override == frozenset()
    assert state.right == 11_050_000


def test_record_is_cleared_when_risk_ends(make_snapshot):
    """!
    @brief 위험 해제 후 오래된 억제 기록으로 override가 나는 결함을 잡는다.
    @req SWR-006
    """
    state, _ = apply(
        INITIAL_STATE, _right_risk(make_snapshot, 1.0), _unlock(Side.RIGHT)
    )
    state, _ = apply(state, make_snapshot(timestamp_s=2.0), None)
    assert state.right is None


def test_all_side_unlock_affects_only_sides_at_risk(make_snapshot):
    """!
    @brief side=all 요청이 위험한 쪽에만 억제되고 반대쪽엔 영향 없는지 본다.
    @req SWR-009
    """
    state, result = apply(
        INITIAL_STATE, _right_risk(make_snapshot, 1.0), _unlock(Side.ALL)
    )
    assert result.rejected == {Side.RIGHT}
    assert state.left is None


def test_lock_request_and_no_request_do_not_suppress(make_snapshot):
    """!
    @brief lock 요청이나 요청 없음은 억제 기록을 만들지 않는지 확인한다.
    @req SWR-005
    """
    lock = DriverRequest(Side.RIGHT, Action.LOCK, Source.AVN)
    for request in (lock, None):
        state, result = apply(
            INITIAL_STATE, _right_risk(make_snapshot, 1.0), request
        )
        assert result.rejected == frozenset()
        assert state == INITIAL_STATE


def test_left_risk_does_not_suppress_right_request(make_snapshot):
    """!
    @brief 왼쪽 위험이 오른쪽 해제 요청을 억제하는 결함을 잡는다.
    @req SWR-009
    """
    snap = make_snapshot(timestamp_s=1.0, rear_left_approach_risk=True)
    _, result = apply(INITIAL_STATE, snap, _unlock(Side.RIGHT))
    assert result.rejected == frozenset()
