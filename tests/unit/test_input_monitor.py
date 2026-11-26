"""!
@brief child_lock.input_monitor 단위 테스트 (SWR-013).
"""

import pytest

from child_lock.input_monitor import is_stale


@pytest.mark.parametrize(
    ("snapshot_ts", "now_s", "expected"),
    [
        (1.0, 1.2, False),  # 정확히 0.200 s: 지연 아님
        (1.1, 1.3, False),  # 부동소수 오차로 0.2000000000000002가 되는 쌍
        (0.1, 0.3, False),
        (1.0, 1.200001, True),  # 0.200001 s
        (1.0, 1.25, True),  # 다음 주기
        (2.0, 1.0, False),  # 미래 시각 (음수 경과)
    ],
)
def test_stale_only_when_age_exceeds_200ms(snapshot_ts, now_s, expected):
    """!
    @brief 0.200 s 경계와 부동소수 오차 때문에 잘못 판정하는 결함을 잡는다.
    @req SWR-013
    """
    assert is_stale(snapshot_ts, now_s) is expected
