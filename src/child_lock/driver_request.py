"""!
@brief 운전자 명령 해석 (QM, SWR-002).

호출자(web.server, replay)가 이 모듈로 명령을 해석해 불변 결과만
controller에 넘긴다 (SWA-001 AD-05). ASIL B 모듈은 이 모듈을
import하지 않는다.
"""

from child_lock.types import Action, DriverRequest, InvalidRequest, Side, Source

# (필드명, 열거형) — OEM-IF-004
_FIELDS = (("side", Side), ("action", Action), ("source", Source))


def parse_command(raw):
    """!
    @brief 원시 운전자 명령을 해석한다.
    @param raw JSON에서 읽은 객체
    @return DriverRequest 또는 사유가 담긴 InvalidRequest
    @req SWR-002
    """
    if not isinstance(raw, dict):
        return InvalidRequest("not an object")
    values = {}
    for name, enum_type in _FIELDS:
        allowed = {member.value: member for member in enum_type}
        value = raw.get(name)
        if not isinstance(value, str) or value not in allowed:
            return InvalidRequest(f"{name}: invalid or missing")
        values[name] = allowed[value]
    return DriverRequest(**values)
