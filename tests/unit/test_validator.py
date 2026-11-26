"""!
@brief child_lock.validator 단위 테스트 (SWR-013).
"""

import math

import pytest

from child_lock.types import CrashStatus, Gear, Rejection, VehicleSnapshot
from child_lock.validator import validate_vehicle

BOOL_FIELDS = [
    "rear_left_approach_risk",
    "rear_right_approach_risk",
    "fire_detected",
    "overtemperature_detected",
    "adult_present",
    "isofix_left",
    "isofix_right",
    "ignition_on",
    "sensor_fault",
]


def _raw(**overrides):
    """!
    @brief 모든 필드가 유효한 차량 입력을 만든다.
    @param overrides 바꿀 필드
    @return 원시 입력 dict
    """
    raw = {
        "timestamp_s": 1.0,
        "vehicle_speed_kph": 0.0,
        "gear": "P",
        "crash_status": "NONE",
    }
    raw.update({name: False for name in BOOL_FIELDS})
    raw["ignition_on"] = True
    raw.update(overrides)
    return raw


def test_valid_input_becomes_snapshot():
    """!
    @brief 정상 입력이 열거형으로 변환된 스냅샷이 되는지 확인한다.
    @req SWR-013
    """
    snap = validate_vehicle(_raw(gear="D", crash_status="PENDING"))
    assert isinstance(snap, VehicleSnapshot)
    assert snap.gear is Gear.D
    assert snap.crash_status is CrashStatus.PENDING
    assert snap.ignition_on is True


def test_non_object_is_rejected():
    """!
    @brief dict가 아닌 입력을 평가 전에 거절하는지 확인한다.
    @req SWR-013
    """
    assert validate_vehicle([1, 2]) == Rejection("<root>", "not an object")


@pytest.mark.parametrize(
    "field",
    ["timestamp_s", "vehicle_speed_kph", "gear", "crash_status", *BOOL_FIELDS],
)
def test_missing_field_is_rejected(field):
    """!
    @brief 필수 필드 누락을 놓치는 결함을 잡는다.
    @req SWR-013
    """
    raw = _raw()
    del raw[field]
    assert validate_vehicle(raw) == Rejection(field, "missing")


@pytest.mark.parametrize("value", [0.0, 300.0, 120])
def test_speed_on_boundary_or_integer_is_accepted(value):
    """!
    @brief 범위 경계값(0.0, 300.0)과 정수 차속을 받아들이는지 확인한다.
    @req SWR-013
    """
    assert isinstance(
        validate_vehicle(_raw(vehicle_speed_kph=value)), VehicleSnapshot
    )


@pytest.mark.parametrize(
    "value", [-0.1, 300.1, math.nan, math.inf, "10", True, None]
)
def test_speed_out_of_range_or_wrong_type_is_rejected(value):
    """!
    @brief 범위 밖, NaN·inf, 문자열, bool 차속을 거절하는지 확인한다.
    @req SWR-013
    """
    result = validate_vehicle(_raw(vehicle_speed_kph=value))
    assert isinstance(result, Rejection)
    assert result.field == "vehicle_speed_kph"


@pytest.mark.parametrize("value", [-0.001, math.nan, "1.0", False])
def test_bad_timestamp_is_rejected(value):
    """!
    @brief 음수·NaN·문자열·bool 시각을 거절하는지 확인한다.
    @req SWR-013
    """
    result = validate_vehicle(_raw(timestamp_s=value))
    assert isinstance(result, Rejection)
    assert result.field == "timestamp_s"


@pytest.mark.parametrize("field", BOOL_FIELDS)
@pytest.mark.parametrize("value", [1, 0, "true", None])
def test_non_bool_flag_is_rejected(field, value):
    """!
    @brief 1, 0, 문자열이 불리언으로 통과하는 결함을 잡는다 (D-03).
    @req SWR-013
    """
    result = validate_vehicle(_raw(**{field: value}))
    assert result == Rejection(field, "not a bool")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("gear", "X"),
        ("gear", "p"),
        ("gear", 1),
        ("crash_status", "confirmed"),
        ("crash_status", "UNKNOWN"),
    ],
)
def test_undefined_enum_value_is_rejected(field, value):
    """!
    @brief 미정의·소문자·비문자열 열거 값을 거절하는지 확인한다.
    @req SWR-013
    """
    assert validate_vehicle(_raw(**{field: value})) == Rejection(
        field, "undefined value"
    )


def test_extra_fields_are_ignored():
    """!
    @brief 계약에 없는 추가 필드는 무시하는지 확인한다 (SWD-001 3절).
    """
    assert isinstance(validate_vehicle(_raw(extra=123)), VehicleSnapshot)
