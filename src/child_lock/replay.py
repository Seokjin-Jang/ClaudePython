"""!
@brief 입력 벡터 재생과 결과 해시 (QM, SWR-016).

같은 입력 벡터를 새 컨트롤러로 반복 재생해 공개 결과(주기별 상태 +
최종 이벤트)의 SHA-256이 항상 같은지 확인한다 (OEM-NFR-001).

벡터 형식: [{"now_s": float, "vehicle": {...}?, "command": {...}?}, ...]
실행: python -m child_lock.replay vectors.json [--repeat 1000]
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

from child_lock.controller import ChildLockController
from child_lock.driver_request import parse_command
from child_lock.event_log import EventLog
from child_lock.status import to_status


def _replay(vectors):
    """!
    @brief 새 컨트롤러로 벡터를 재생한다.
    @param vectors 입력 벡터 목록
    @return (주기별 상태 목록, EventLog)
    """
    log = EventLog()
    ctrl = ChildLockController(record=log.record)
    statuses = []
    for step in vectors:
        command = step.get("command")
        request = parse_command(command) if command is not None else None
        decision = ctrl.evaluate(step["now_s"], step.get("vehicle"), request)
        statuses.append(to_status(decision))
    return statuses, log


def run(vectors):
    """!
    @brief 벡터를 재생해 주기별 상태 응답을 돌려준다.
    @param vectors 입력 벡터 목록
    @return list[dict]
    @req SWR-016
    """
    return _replay(vectors)[0]


def digest(vectors):
    """!
    @brief 재생 공개 결과의 SHA-256을 계산한다.
    @param vectors 입력 벡터 목록
    @return 16진 해시 문자열 (64자)
    @req SWR-016
    """
    statuses, log = _replay(vectors)
    payload = json.dumps(
        {"statuses": statuses, "events": log.items()},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def main(argv=None):
    """!
    @brief 명령줄 진입점. 반복 재생 해시가 모두 같은지 확인한다.
    @param argv 명령줄 인자
    @return 모두 같으면 0 (해시 출력), 다르면 1
    @req SWR-016
    """
    parser = argparse.ArgumentParser(description="입력 벡터 결정론 재생")
    parser.add_argument("vectors", help="입력 벡터 JSON 파일")
    parser.add_argument("--repeat", type=int, default=1, help="반복 횟수")
    args = parser.parse_args(argv)
    vectors = json.loads(Path(args.vectors).read_text(encoding="utf-8"))
    digests = {digest(vectors) for _ in range(args.repeat)}
    if len(digests) != 1:
        print(f"결정론 위반: 서로 다른 해시 {len(digests)}개")
        return 1
    print(digests.pop())
    return 0


# 스크립트 직접 실행 진입점: main()은 테스트로 검증하므로 제외
if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
