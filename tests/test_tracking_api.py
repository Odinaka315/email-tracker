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


def test_convert_text_to_html():
    from app.services.email_service import convert_text_to_html

    # 1. Plain text with paragraphs and single line breaks
    text = "Hello Alice,\n\nHow are you doing?\nHere is line 2.\n\nBest,\nBob"
    html_out = convert_text_to_html(text)
    assert "<!DOCTYPE html>" in html_out
    assert "<p style=" in html_out
    assert "Hello Alice," in html_out
    assert "How are you doing?<br/>Here is line 2." in html_out
    assert "Best,<br/>Bob" in html_out

    # 2. HTML escaping of special characters
    special_text = "Check if 5 < 10 & 20 > 15 with 'quotes' and \"double\""
    html_out_2 = convert_text_to_html(special_text)
    assert "5 &lt; 10 &amp; 20 &gt; 15" in html_out_2
    assert "&quot;double&quot;" in html_out_2

    # 3. Automatic link detection with click tracking
    link_text = "Visit our docs at https://example.com/docs."
    html_out_3 = convert_text_to_html(link_text, token="trk_test_123", base_url="http://localhost:8000")
    assert "/api/v1/track/click/trk_test_123?url=https%3A%2F%2Fexample.com%2Fdocs" in html_out_3
    # Check that trailing period is outside the anchor tag
    assert 'https://example.com/docs</a>.' in html_out_3

    # 4. If already full HTML document, preserve it
    doc = "<html><body>Already HTML</body></html>"
    assert convert_text_to_html(doc) == doc


@pytest.mark.asyncio
async def test_email_track_with_plain_text():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        plain_body = "Hello John,\n\nWe have updated your invoice.\nVisit https://example.com/invoice to view it."
        create_resp = await client.post(
            "/api/v1/emails/track",
            json={
                "recipient_email": "john@example.com",
                "subject": "Invoice Updated",
                "body": plain_body,
            },
        )
        assert create_resp.status_code == 201
        data = create_resp.json()
        assert data["recipient_email"] == "john@example.com"
        assert "<img src=" in data["injected_html"]
        assert "Hello John," in data["injected_html"]
        assert "/api/v1/track/click/" in data["injected_html"]


@pytest.mark.asyncio
async def test_send_tracked_email_with_plain_text():
    from unittest.mock import patch, AsyncMock

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with patch("app.api.v1.emails.send_email_via_brevo", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = {"messageId": "msg_123"}

            resp = await client.post(
                "/api/v1/emails/send",
                data={
                    "recipient_email": "jane@example.com",
                    "subject": "Welcome to our service",
                    "body": "Hi Jane,\n\nWelcome aboard!\n\nCheers,\nSupport",
                },
            )
            assert resp.status_code == 201
            data = resp.json()
            assert data["recipient_email"] == "jane@example.com"
            assert data["status"] == "SENT"
            assert "<img src=" in data["injected_html"]

            mock_send.assert_awaited_once()
            call_kwargs = mock_send.await_args.kwargs
            assert call_kwargs["recipient_email"] == "jane@example.com"
            assert call_kwargs["subject"] == "Welcome to our service"
            assert "<img src=" in call_kwargs["html_content"]
            assert call_kwargs["text_content"] == "Hi Jane,\n\nWelcome aboard!\n\nCheers,\nSupport"


@pytest.mark.asyncio
async def test_send_tracked_email_missing_body():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/emails/send",
            data={
                "recipient_email": "jane@example.com",
                "subject": "Welcome",
            },
        )
        assert resp.status_code == 422
