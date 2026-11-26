"""!
@brief 단위 테스트 공용 도우미.
"""

import pytest

from child_lock.types import CrashStatus, Gear, VehicleSnapshot


def snapshot(**overrides):
    """!
    @brief 정차·IGN ON·이상 없음 상태의 스냅샷을 만든다.
    @param overrides 바꿀 필드
    @return VehicleSnapshot
    """
    values = {
        "timestamp_s": 0.0,
        "vehicle_speed_kph": 0.0,
        "gear": Gear.P,
        "crash_status": CrashStatus.NONE,
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
    values.update(overrides)
    return VehicleSnapshot(**values)


@pytest.fixture
def make_snapshot():
    """!
    @brief snapshot 도우미를 픽스처로 제공한다.
    @return snapshot 함수
    """
    return snapshot
