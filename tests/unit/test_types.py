"""!
@brief child_lock.types 단위 테스트.
"""

import dataclasses

import pytest

from child_lock.types import Lock, Outputs, ReasonCode, Side


def test_outputs_get_returns_value_of_requested_side():
    """!
    @brief 좌우를 뒤바꿔 돌려주는 결함을 잡는다.
    @req SWR-009
    """
    out = Outputs(left=Lock.LOCK, right=Lock.RELEASE)
    assert out.get(Side.LEFT) is Lock.LOCK
    assert out.get(Side.RIGHT) is Lock.RELEASE


def test_outputs_get_rejects_all_side():
    """!
    @brief 'all'은 한쪽 출력이 아니므로 조회를 거절하는지 확인한다.
    """
    with pytest.raises(ValueError):
        Outputs(left=Lock.LOCK, right=Lock.LOCK).get(Side.ALL)


def test_outputs_is_immutable():
    """!
    @brief QM 모듈이 결정 결과를 바꿀 수 없는지 확인한다 (SWA P-04).
    """
    out = Outputs(left=Lock.LOCK, right=Lock.LOCK)
    with pytest.raises(dataclasses.FrozenInstanceError):
        out.left = Lock.RELEASE  # type: ignore[misc]


def test_reason_codes_match_requirement_list():
    """!
    @brief 이유 코드 누락·오타를 잡는다 (SWR-SPEC-001 6절 17종).
    """
    expected = {
        "IGNITION_OFF",
        "CRASH_CONFIRMED",
        "CRASH_PENDING",
        "SENSOR_FAULT",
        "INPUT_INVALID",
        "INPUT_STALE",
        "FIRE",
        "OVERTEMPERATURE",
        "ADULT_PRESENT",
        "APPROACH_RISK",
        "APPROACH_OVERRIDE_REQUESTED",
        "ISOFIX",
        "AUTO_LOCK_SPEED",
        "DRIVER_COMMAND",
        "DRIVER_REQUEST_REJECTED",
        "DRIVER_REQUEST_INVALID",
        "NO_CHANGE",
    }
    assert {c.value for c in ReasonCode} == expected
