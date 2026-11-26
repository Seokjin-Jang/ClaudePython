"""!
@brief 평가 주기 실행과 상태 보관 (ASIL B).

판단은 순수 함수(validator, input_monitor, approach_guard, arbiter)가
하고, 상태 변경은 이 클래스 한 곳에서만 한다 (SWA-001 P-01). 시각은
호출자가 now_s로 넘긴다 (P-02). 이벤트 기록은 생성 시 주입받은 함수로
판정·상태 갱신이 끝난 뒤 호출한다 (AD-03) — 이 모듈은 QM 모듈을
import하지 않는다.
"""

from child_lock import approach_guard
from child_lock.arbiter import Context, decide
from child_lock.input_monitor import is_stale
from child_lock.types import (
    CrashStatus,
    InputValidity,
    Lock,
    Outputs,
    Rejection,
)
from child_lock.validator import validate_vehicle


class ChildLockController:
    """!
    @brief 전자식 차일드락 제어기. evaluate 1회가 평가 주기 1회다.
    """

    def __init__(self, record=None):
        """!
        @brief 초기 상태(출력 RELEASE/RELEASE, 래치 없음)로 만든다.
        @param record 결정 기록 함수 (decision, now_s) 또는 None
        """
        self._record = record
        self._snapshot = None
        self._crash_latched = False
        self._guard = approach_guard.INITIAL_STATE
        self._last = None
        self._outputs = Outputs(Lock.RELEASE, Lock.RELEASE)

    @property
    def last_decision(self):
        """!
        @brief 마지막 결정 (평가 전이면 None).
        @return Decision 또는 None
        """
        return self._last

    def _validity(self, now_s, rejected):
        """!
        @brief 이번 주기 입력 유효성을 판정한다.
        @param now_s 평가 시각 [s]
        @param rejected 이번 주기 입력이 검증에 실패했는지
        @return InputValidity
        @req SWR-013
        """
        if rejected:
            return InputValidity.INVALID
        if self._snapshot is None:
            return InputValidity.STALE
        if is_stale(self._snapshot.timestamp_s, now_s):
            return InputValidity.STALE
        return InputValidity.VALID

    def _update_latches(self, snapshot, request):
        """!
        @brief 충돌 래치와 접근위험 가드 상태를 갱신한다.
        @param snapshot 유효한 VehicleSnapshot
        @param request 운전자 요청 또는 None
        @return 이번 주기 GuardResult
        @req SWR-006, SWR-007, SWR-020
        """
        if not snapshot.ignition_on:
            self._crash_latched = False
            self._guard = approach_guard.INITIAL_STATE
        elif snapshot.crash_status is CrashStatus.CONFIRMED:
            self._crash_latched = True
        self._guard, result = approach_guard.apply(
            self._guard, snapshot, request
        )
        return result

    def evaluate(self, now_s, vehicle_raw=None, request=None):
        """!
        @brief 평가 주기 1회를 실행한다.
        @param now_s 평가 시각 [s]
        @param vehicle_raw 원시 차량 입력 (없으면 마지막 스냅샷 사용)
        @param request DriverRequest, InvalidRequest 또는 None
        @return Decision
        @req SWR-013, SWR-016, SWR-019
        """
        rejected = False
        if vehicle_raw is not None:
            result = validate_vehicle(vehicle_raw)
            rejected = isinstance(result, Rejection)
            if not rejected:
                self._snapshot = result
        validity = self._validity(now_s, rejected)
        snapshot = self._snapshot if validity is InputValidity.VALID else None
        guard = approach_guard.EMPTY_RESULT
        if snapshot is not None:
            guard = self._update_latches(snapshot, request)
        decision = decide(
            Context(
                snapshot,
                validity,
                self._outputs,
                self._crash_latched,
                request,
                guard,
            )
        )
        self._outputs = decision.outputs
        self._last = decision
        if self._record is not None:
            self._record(decision, now_s)
        return decision
