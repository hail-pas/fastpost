from starlette.testclient import TestClient

from fastpost.factory import current_app

client = TestClient(current_app)


def test_chat_simple():
    with client.websocket_connect("/ws/example?client_id=1") as websocket:
        data = websocket.receive_json()
        assert data == {"msg": "Hello WebSocket"}
