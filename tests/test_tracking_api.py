import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_email_tracking_flow():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Register email for tracking
        raw_html = "<html><body><h1>Hello World</h1><p>Important update</p></body></html>"
        create_resp = await client.post(
            "/api/v1/emails/track",
            json={
                "recipient_email": "client@example.com",
                "subject": "Proposal for Q3",
                "sender_id": "sender_123",
                "html_body": raw_html,
                "meta_data": {"campaign": "q3_launch"},
            },
        )
        assert create_resp.status_code == 201
        data = create_resp.json()
        assert "id" in data
        assert data["recipient_email"] == "client@example.com"
        assert data["status"] == "SENT"
        assert data["open_count"] == 0
        token = data["tracking_token"]
        assert token.startswith("trk_")
        assert "tracking_pixel_url" in data
        assert "<img src=" in data["injected_html"]
        email_id = data["id"]

        # 2. Simulate recipient opening the email (fetch pixel)
        open_resp = await client.get(
            f"/api/v1/track/open/{token}.gif",
            headers={"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15"},
        )
        assert open_resp.status_code == 200
        assert open_resp.headers["content-type"] == "image/gif"
        assert "no-store" in open_resp.headers["cache-control"]
        assert len(open_resp.content) == 43  # 43-byte transparent GIF

        # 3. Verify email status updated
        detail_resp = await client.get(f"/api/v1/emails/{email_id}")
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        assert detail["status"] == "OPENED"
        assert detail["open_count"] == 1
        assert detail["first_opened_at"] is not None
        assert len(detail["open_events"]) == 1
        assert detail["open_events"][0]["device_type"] == "MOBILE"

        # 4. Test link click tracking
        target_url = "https://example.com/pricing"
        click_resp = await client.get(
            f"/api/v1/track/click/{token}",
            params={"url": target_url},
            follow_redirects=False,
        )
        assert click_resp.status_code == 307
        assert click_resp.headers["location"] == target_url

        # Verify click count updated
        detail_resp_2 = await client.get(f"/api/v1/emails/{email_id}")
        assert detail_resp_2.json()["click_count"] == 1

        # 5. Check statistics
        stats_resp = await client.get("/api/v1/stats/overview")
        assert stats_resp.status_code == 200
        stats = stats_resp.json()
        assert stats["total_emails_tracked"] >= 1
        assert stats["total_emails_opened"] >= 1
        assert stats["total_link_clicks"] >= 1
