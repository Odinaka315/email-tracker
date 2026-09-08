"""
Simulation script: Registers an email for tracking, then simulates a recipient opening it.
Run:
    python scripts/simulate_send_and_open.py
"""
import httpx
import time

BASE_URL = "http://localhost:8000"


def run_simulation():
    print("\n🚀 Starting Email Open Tracking Simulation...")

    with httpx.Client(base_url=BASE_URL) as client:
        # Step 1: Create tracked email
        print("\n1️⃣ Registering tracked email...")
        payload = {
            "recipient_email": "jane.doe@acme-corp.com",
            "subject": "Q4 Partnership Proposal & Contract",
            "sender_id": "default_sender",
            "html_body": "<html><body><h2>Hi Jane</h2><p>Please review our proposal attached.</p></body></html>",
            "meta_data": {"lead_score": 95, "campaign": "enterprise_outreach"},
        }
        resp = client.post("/api/v1/emails/track", json=payload)
        if resp.status_code != 201:
            print(f"❌ Failed to create email: {resp.text}")
            return

        email_data = resp.json()
        token = email_data["tracking_token"]
        pixel_url = email_data["tracking_pixel_url"]
        print(f"   ✅ Tracked Email ID: {email_data['id']}")
        print(f"   ✅ Tracking Token  : {token}")
        print(f"   ✅ Tracking Pixel  : {pixel_url}")
        print(f"   ✅ Injected HTML preview:")
        print(f"      {email_data['injected_html']}")

        # Wait a moment
        print("\n⏳ Waiting 2 seconds before recipient opens email...")
        time.sleep(2)

        # Step 2: Simulate Recipient Opening the Email
        print(f"\n2️⃣ Recipient opens email on an iPhone (fetching pixel: {pixel_url})...")
        open_resp = client.get(
            f"/api/v1/track/open/{token}.gif",
            headers={
                "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
            },
        )
        print(f"   ✅ Pixel Response Status: {open_resp.status_code} {open_resp.headers.get('content-type')}")
        print(f"   ✅ GIF Payload Size: {len(open_resp.content)} bytes")
        print(f"   ✅ Cache Headers: {open_resp.headers.get('cache-control')}")

        # Step 3: Fetch updated status
        time.sleep(1)
        print("\n3️⃣ Fetching updated status from backend...")
        detail_resp = client.get(f"/api/v1/emails/{email_data['id']}")
        detail = detail_resp.json()
        print(f"   ✅ Status     : {detail['status']}")
        print(f"   ✅ Open Count : {detail['open_count']}")
        print(f"   ✅ First Open : {detail['first_opened_at']}")
        if detail.get("open_events"):
            event = detail["open_events"][0]
            print(f"   ✅ Open Event : Device={event['device_type']}, Client={event['client_name']}, OS={event['os_name']}")

        print("\n✨ Simulation finished successfully!")


if __name__ == "__main__":
    run_simulation()
