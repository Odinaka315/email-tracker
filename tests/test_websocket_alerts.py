from starlette.testclient import TestClient
from app.main import app


def test_websocket_realtime_alert():
    # Using TestClient in a synchronous test ensures all ASGI operations,
    # background tasks, WebSockets, and DB sessions share the exact same event loop.
    with TestClient(app) as test_client:
        # 1. Register a tracked email
        create_resp = test_client.post(
            "/api/v1/emails/track",
            json={
                "recipient_email": "realtime_user@example.com",
                "subject": "Urgent Contract",
                "sender_id": "sender_ws_test",
            },
        )
        assert create_resp.status_code == 201
        data = create_resp.json()
        token = data["tracking_token"]

        # 2. Connect WebSocket client
        with test_client.websocket_connect("/ws/alerts/sender_ws_test") as websocket:
            # First message is connection acknowledgment
            connect_msg = websocket.receive_json()
            assert connect_msg["event"] == "CONNECTED"
            assert connect_msg["client_id"] == "sender_ws_test"

            # 3. Trigger email open (fetch pixel)
            open_resp = test_client.get(
                f"/api/v1/track/open/{token}.gif",
                headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"},
            )
            assert open_resp.status_code == 200

            # 4. WebSocket receives the real-time EMAIL_OPENED alert
            alert_msg = websocket.receive_json()
            assert alert_msg["event"] == "EMAIL_OPENED"
            assert alert_msg["recipient_email"] == "realtime_user@example.com"
            assert alert_msg["is_first_open"] is True
            assert alert_msg["open_count"] == 1
            assert alert_msg["client_info"]["device_type"] == "DESKTOP"

