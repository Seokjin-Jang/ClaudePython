"""!
@brief child_lock.driver_request 단위 테스트 (SWR-002).
"""

import pytest

from child_lock.driver_request import parse_command
from child_lock.types import Action, DriverRequest, InvalidRequest, Side, Source


@pytest.mark.parametrize("source", [s.value for s in Source])
def test_each_supported_source_is_parsed(source):
    """!
    @brief 지원 경로 4종이 모두 같은 규칙으로 해석되는지 확인한다.
    @req SWR-002
    """
    raw = {"side": "all", "action": "unlock", "source": source}
    assert parse_command(raw) == DriverRequest(
        Side.ALL, Action.UNLOCK, Source(source)
    )


@pytest.mark.parametrize(
    "raw",
    [
        None,
        "left",
        {"side": "left", "action": "unlock"},
        {"side": "middle", "action": "lock", "source": "avn"},
        {"side": "left", "action": "open", "source": "avn"},
        {"side": "left", "action": "lock", "source": "sms"},
        {"side": "LEFT", "action": "lock", "source": "avn"},
    ],
)
def test_malformed_command_is_invalid(raw):
    """!
    @brief 누락·미등록 값·대소문자 오류 명령이 유효로 통과하는 결함을 잡는다.
    @req SWR-002
    """
    assert isinstance(parse_command(raw), InvalidRequest)
