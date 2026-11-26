"""!
@brief child_lock.event_log 단위 테스트 (SWR-010, 011, 012).
"""

from child_lock.event_log import EventLog
from child_lock.types import (
    Decision,
    InputValidity,
    Lock,
    Outputs,
    ReasonCode,
    State,
)

KEYS = {
    "event_id",
    "timestamp_s",
    "lock_left",
    "lock_right",
    "state",
    "reason_code",
    "input_validity",
}


def _decision(code=ReasonCode.NO_CHANGE, notices=()):
    """!
    @brief 기록용 결정을 만든다.
    @param code 주 이유 코드
    @param notices 보조 코드
    @return Decision
    """
    return Decision(
        Outputs(Lock.LOCK, Lock.RELEASE),
        State.NORMAL,
        code,
        InputValidity.VALID,
        notices,
    )


def test_event_has_exactly_allowed_fields_as_strings():
    """!
    @brief 허용 7필드만 있고 값이 문자열로 직렬화되는지 확인한다.
    @req SWR-011
    """
    log = EventLog()
    log.record(_decision(), 1.5)
    assert log.items() == [
        {
            "event_id": 1,
            "timestamp_s": 1.5,
            "lock_left": "LOCK",
            "lock_right": "RELEASE",
            "state": "NORMAL",
            "reason_code": "NO_CHANGE",
            "input_validity": "VALID",
        }
    ]


def test_only_latest_100_events_are_kept_in_order():
    """!
    @brief 101건 후 event_id 2~101만 순서대로 남는지 확인한다.
    @req SWR-010
    """
    log = EventLog()
    for i in range(101):
        log.record(_decision(), float(i))
    ids = [e["event_id"] for e in log.items()]
    assert ids == list(range(2, 102))


def test_notices_follow_decision_event():
    """!
    @brief 보조 코드가 결정 이벤트 뒤에 코드마다 1건씩 기록되는지 본다.
    @req SWR-010
    """
    log = EventLog()
    log.record(
        _decision(
            ReasonCode.APPROACH_RISK,
            (ReasonCode.CRASH_PENDING, ReasonCode.DRIVER_REQUEST_REJECTED),
        ),
        2.0,
    )
    events = log.items()
    assert [e["reason_code"] for e in events] == [
        "APPROACH_RISK",
        "CRASH_PENDING",
        "DRIVER_REQUEST_REJECTED",
    ]
    assert [e["event_id"] for e in events] == [1, 2, 3]
    assert all(set(e) == KEYS for e in events)


def test_items_returns_copies():
    """!
    @brief 조회 결과를 바꿔도 내부 기록이 바뀌지 않는지 확인한다.
    @req SWR-011
    """
    log = EventLog()
    log.record(_decision(), 0.0)
    log.items()[0]["reason_code"] = "TAMPERED"
    assert log.items()[0]["reason_code"] == "NO_CHANGE"


def test_new_log_is_empty():
    """!
    @brief 새로 만든 저장소(재기동 상당)는 비어 있는지 확인한다.
    @req SWR-012
    """
    assert EventLog().items() == []
