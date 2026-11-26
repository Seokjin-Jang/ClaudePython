"""!
@brief 차일드락 SW의 열거형과 불변 데이터 구조 (ASIL B).

모듈 사이에서는 이 파일의 불변 객체만 주고받는다 (SWA-001 P-04).
열거형 값은 OEM 인터페이스(OEM-IF-001~009) 문자열을 그대로 쓴다.
"""

from dataclasses import dataclass
from enum import Enum


class Lock(Enum):
    """!
    @brief 한쪽 차일드락 논리 출력 (OEM-IF-005).
    """

    LOCK = "LOCK"
    RELEASE = "RELEASE"


class State(Enum):
    """!
    @brief SW 상태 (SWA-001 3.2 상태 기계).
    """

    OFF = "OFF"
    NORMAL = "NORMAL"
    DEGRADED = "DEGRADED"
    FAULT = "FAULT"


class InputValidity(Enum):
    """!
    @brief 이번 평가 주기 입력의 유효성 (SWR-013).
    """

    VALID = "VALID"
    INVALID = "INVALID"
    STALE = "STALE"


class ReasonCode(Enum):
    """!
    @brief 출력 결정 이유 코드 (SWR-SPEC-001 6절).
    """

    IGNITION_OFF = "IGNITION_OFF"
    CRASH_CONFIRMED = "CRASH_CONFIRMED"
    CRASH_PENDING = "CRASH_PENDING"
    SENSOR_FAULT = "SENSOR_FAULT"
    INPUT_INVALID = "INPUT_INVALID"
    INPUT_STALE = "INPUT_STALE"
    FIRE = "FIRE"
    OVERTEMPERATURE = "OVERTEMPERATURE"
    ADULT_PRESENT = "ADULT_PRESENT"
    APPROACH_RISK = "APPROACH_RISK"
    APPROACH_OVERRIDE_REQUESTED = "APPROACH_OVERRIDE_REQUESTED"
    ISOFIX = "ISOFIX"
    AUTO_LOCK_SPEED = "AUTO_LOCK_SPEED"
    DRIVER_COMMAND = "DRIVER_COMMAND"
    DRIVER_REQUEST_REJECTED = "DRIVER_REQUEST_REJECTED"
    DRIVER_REQUEST_INVALID = "DRIVER_REQUEST_INVALID"
    NO_CHANGE = "NO_CHANGE"


class Side(Enum):
    """!
    @brief 운전자 명령 대상 (OEM-IF-004). 출력 쪽은 LEFT, RIGHT만 쓴다.
    """

    LEFT = "left"
    RIGHT = "right"
    ALL = "all"


class Action(Enum):
    """!
    @brief 운전자 명령 동작 (OEM-IF-004).
    """

    LOCK = "lock"
    UNLOCK = "unlock"


class Source(Enum):
    """!
    @brief 운전자 명령 경로 (OEM-IF-004, SWR-002).
    """

    PHYSICAL_BUTTON = "physical_button"
    AVN = "avn"
    VOICE = "voice"
    MOBILE_APP = "mobile_app"


class CrashStatus(Enum):
    """!
    @brief 충돌 상태 (OEM-IF-002).
    """

    NONE = "NONE"
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"


class Gear(Enum):
    """!
    @brief 기어 (OEM-IF-001). 검증만 하고 판단에 쓰지 않는다 (가정 A-06).
    """

    P = "P"
    N = "N"
    D = "D"
    R = "R"


@dataclass(frozen=True)
class VehicleSnapshot:
    """!
    @brief 검증을 통과한 차량 입력 스냅샷 (OEM-IF-001~003, 007~009).
    """

    timestamp_s: float
    vehicle_speed_kph: float
    gear: Gear
    crash_status: CrashStatus
    rear_left_approach_risk: bool
    rear_right_approach_risk: bool
    fire_detected: bool
    overtemperature_detected: bool
    adult_present: bool
    isofix_left: bool
    isofix_right: bool
    ignition_on: bool
    sensor_fault: bool


@dataclass(frozen=True)
class DriverRequest:
    """!
    @brief 해석이 끝난 유효한 운전자 명령 (OEM-IF-004).
    """

    side: Side
    action: Action
    source: Source


@dataclass(frozen=True)
class InvalidRequest:
    """!
    @brief 형식이 잘못된 운전자 명령 (SWR-002).
    """

    reason: str


@dataclass(frozen=True)
class Rejection:
    """!
    @brief 차량 입력 검증 실패 정보 (SWR-013).
    """

    field: str
    reason: str


@dataclass(frozen=True)
class Outputs:
    """!
    @brief 좌우 차일드락 출력 쌍 (OEM-IF-005).
    """

    left: Lock
    right: Lock

    def get(self, side: Side) -> Lock:
        """!
        @brief 한쪽 출력을 돌려준다.
        @param side Side.LEFT 또는 Side.RIGHT
        @return 해당 쪽 출력
        @raises ValueError side가 Side.ALL인 경우
        """
        if side is Side.LEFT:
            return self.left
        if side is Side.RIGHT:
            return self.right
        raise ValueError("Outputs.get requires LEFT or RIGHT")


@dataclass(frozen=True)
class Decision:
    """!
    @brief 한 평가 주기의 결정 결과.

    notices는 보조 이유 코드를 발생 순서대로 담는다 (SWR-010).
    """

    outputs: Outputs
    state: State
    reason_code: ReasonCode
    input_validity: InputValidity
    notices: tuple[ReasonCode, ...] = ()
