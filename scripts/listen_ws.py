"""
Interactive terminal client to listen to real-time email open alerts via WebSockets.
Run:
    python scripts/listen_ws.py [optional_sender_id]
"""
import asyncio
import json
import sys
import websockets


async def listen(sender_id: str = "default_sender"):
    uri = f"ws://localhost:8000/ws/alerts/{sender_id}"
    print(f"\n📡 Connecting to real-time WebSocket alert stream at: {uri}")
    try:
        async with websockets.connect(uri) as websocket:
            print(f"✅ Connected! Waiting for email open events for sender: '{sender_id}'...\n")
            while True:
                msg = await websocket.recv()
                data = json.loads(msg)
                event_type = data.get("event")
                if event_type == "CONNECTED":
                    print(f"ℹ️  [SERVER]: {data.get('message')}")
                elif event_type == "EMAIL_OPENED":
                    print("=" * 60)
                    print(f"🚨 [EMAIL OPENED ALERT]!")
                    print(f"   Recipient : {data.get('recipient_email')}")
                    print(f"   Subject   : {data.get('subject')}")
                    print(f"   Open Count: #{data.get('open_count')} (First Open: {data.get('is_first_open')})")
                    print(f"   Opened At : {data.get('opened_at')}")
                    client_info = data.get("client_info", {})
                    print(f"   Device    : {client_info.get('device_type')}")
                    print(f"   Client    : {client_info.get('client_name')}")
                    print(f"   OS        : {client_info.get('os_name')}")
                    print(f"   IP        : {client_info.get('ip_address')}")
                    if client_info.get("is_proxy"):
                        print(f"   Proxy Type: {client_info.get('proxy_type')}")
                    print("=" * 60 + "\n")
                else:
                    print(f"📩 [MESSAGE]: {data}")
    except ConnectionRefusedError:
        print("❌ Could not connect to FastAPI server. Is it running on http://localhost:8000?")
    except KeyboardInterrupt:
        print("\n👋 Disconnected.")


if __name__ == "__main__":
    sender = sys.argv[1] if len(sys.argv) > 1 else "default_sender"
    asyncio.run(listen(sender))
