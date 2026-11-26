"""!
@brief 통합 시험 픽스처: 임시 포트에 실제 HTTP 서버를 띄운다.
"""

import threading

import pytest
from it_support import Client

from child_lock.web.server import build


@pytest.fixture
def client():
    """!
    @brief 실제 서버를 띄우고 클라이언트를 제공한 뒤 종료한다.
    @return Client
    """
    server, _ = build(["--host", "127.0.0.1", "--port", "0"])
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield Client(f"http://127.0.0.1:{server.server_address[1]}")
    server.shutdown()
    server.server_close()
