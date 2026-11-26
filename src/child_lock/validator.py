"""!
@brief 차량 입력 형식·범위 검증 (ASIL B, SWR-013).

필드 명세 표를 순서대로 검사하고 첫 실패에서 Rejection을 돌려준다.
판단 함수는 예외를 던지지 않는다 (SWD-001 D-05).
"""

import math

from child_lock.types import CrashStatus, Gear, Rejection, VehicleSnapshot

# 차속 유효 범위 (OEM-IF-001, SWR-013)
SPEED_MIN_KPH = 0.0
SPEED_MAX_KPH = 300.0

# 불리언 차량 입력 (OEM-IF-003, 007, 008, 009)
BOOL_FIELDS = (
    "rear_left_approach_risk",
    "rear_right_approach_risk",
    "fire_detected",
    "overtemperature_detected",
    "adult_present",
    "isofix_left",
    "isofix_right",
    "ignition_on",
    "sensor_fault",
)


def _is_number(value):
    """!
    @brief bool이 아닌 유한한 int/float인지 확인한다 (D-04).
    @param value 검사할 값
    @return 숫자이면 True
    """
    if type(value) not in (int, float):
        return False
    return math.isfinite(value)


def _check_speed(value):
    """!
    @brief 차속 형식·범위를 검사한다.
    @param value 차속 원시 값
    @return 오류 사유 또는 None
    """
    if not _is_number(value):
        return "not a number"
    if not SPEED_MIN_KPH <= value <= SPEED_MAX_KPH:
        return "out of range"
    return None


def _check_timestamp(value):
    """!
    @brief 시각 형식·범위를 검사한다 (0 이상).
    @param value 시각 원시 값
    @return 오류 사유 또는 None
    """
    if not _is_number(value):
        return "not a number"
    if value < 0:
        return "out of range"
    return None


def _enum_checker(enum_type):
    """!
    @brief 열거 값 검사 함수를 만든다.
    @param enum_type 대상 Enum 클래스
    @return 값 → 오류 사유 또는 None 함수
    """
    allowed = {member.value for member in enum_type}

    def check(value):
        """!
        @brief 문자열이고 정의된 열거 값인지 검사한다.
        @param value 원시 값
        @return 오류 사유 또는 None
        """
        if isinstance(value, str) and value in allowed:
            return None
        return "undefined value"

    return check


def _check_bool(value):
    """!
    @brief 정확히 bool 형인지 검사한다 (D-03).
    @param value 원시 값
    @return 오류 사유 또는 None
    """
    return None if type(value) is bool else "not a bool"


# (필드명, 검사 함수) — 검사 순서이자 오류 보고 순서
_FIELDS = (
    ("timestamp_s", _check_timestamp),
    ("vehicle_speed_kph", _check_speed),
    ("gear", _enum_checker(Gear)),
    ("crash_status", _enum_checker(CrashStatus)),
    *((name, _check_bool) for name in BOOL_FIELDS),
)


def validate_vehicle(raw):
    """!
    @brief 원시 차량 입력을 검증해 스냅샷으로 바꾼다.
    @param raw JSON에서 읽은 객체
    @return VehicleSnapshot 또는 첫 오류의 Rejection
    @req SWR-013
    """
    if not isinstance(raw, dict):
        return Rejection("<root>", "not an object")
    for name, check in _FIELDS:
        if name not in raw:
            return Rejection(name, "missing")
        reason = check(raw[name])
        if reason is not None:
            return Rejection(name, reason)
    values = {name: raw[name] for name, _ in _FIELDS}
    values["gear"] = Gear(values["gear"])
    values["crash_status"] = CrashStatus(values["crash_status"])
    return VehicleSnapshot(**values)
