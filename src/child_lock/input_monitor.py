"""!
@brief 입력 지연 감시 (ASIL B, SWR-013).

시간 비교는 마이크로초 정수로 한다 (SWD-001 D-01). 부동소수 뺄셈
오차 때문에 0.200 s가 0.2000000000000002로 계산돼 지연으로 잘못
판정되는 것을 막기 위해서다.
"""

# 지연 판정 한계: 0.200 s 초과 (OEM-SR-003, SWR-013)
STALE_LIMIT_US = 200_000


def age_us(earlier_s, later_s):
    """!
    @brief 두 시각의 차이를 마이크로초 정수로 돌려준다.
    @param earlier_s 이전 시각 [s]
    @param later_s 이후 시각 [s]
    @return later_s - earlier_s [us], 반올림
    """
    return round((later_s - earlier_s) * 1_000_000)


def is_stale(snapshot_ts, now_s):
    """!
    @brief 스냅샷이 지연됐는지 판정한다.
    @param snapshot_ts 스냅샷 시각 timestamp_s [s]
    @param now_s 평가 시각 [s]
    @return 경과 시간이 0.200 s를 넘으면 True
    @req SWR-013
    """
    return age_us(snapshot_ts, now_s) > STALE_LIMIT_US
