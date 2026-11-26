"""!
@brief 결정 이벤트 저장소 (QM, SWR-010, 011, 012).

메모리(deque)에만 최근 100건을 보존한다. 파일·DB에 쓰지 않으므로
프로세스를 다시 시작하면 비어 있다 (SWR-012). 이벤트는 허용된 7개
필드만 가진다 (SWR-011). controller에는 record 메서드를 콜백으로
주입한다 (SWA-001 AD-03).
"""

from collections import deque

# 보존 건수 (OEM-NFR-002, SWR-010)
EVENT_CAPACITY = 100


class EventLog:
    """!
    @brief 최근 결정 이벤트 링 버퍼.
    """

    def __init__(self, capacity=EVENT_CAPACITY):
        """!
        @brief 빈 저장소를 만든다.
        @param capacity 보존 건수
        """
        self._events = deque(maxlen=capacity)
        self._next_id = 1

    def _append(self, decision, now_s, code):
        """!
        @brief 이벤트 1건을 추가한다.
        @param decision 결정
        @param now_s 평가 시각 [s]
        @param code 이 이벤트의 이유 코드
        """
        self._events.append(
            {
                "event_id": self._next_id,
                "timestamp_s": now_s,
                "lock_left": decision.outputs.left.value,
                "lock_right": decision.outputs.right.value,
                "state": decision.state.value,
                "reason_code": code.value,
                "input_validity": decision.input_validity.value,
            }
        )
        self._next_id += 1

    def record(self, decision, now_s):
        """!
        @brief 결정 이벤트 1건과 보조 코드마다 1건을 기록한다.
        @param decision 결정
        @param now_s 평가 시각 [s]
        @req SWR-010
        """
        self._append(decision, now_s, decision.reason_code)
        for code in decision.notices:
            self._append(decision, now_s, code)

    def items(self):
        """!
        @brief 보존 중인 이벤트를 오래된 순으로 복사해 돌려준다.
        @return list[dict]
        @req SWR-011
        """
        return [dict(event) for event in self._events]
