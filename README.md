# Email Open Alert Backend 🚀

A high-performance FastAPI backend for tracking email opens, link clicks, device telemetry, and broadcasting instant real-time alerts via **WebSockets** and **Redis Pub/Sub**.

---

## 🏗️ Architecture & Features

- **Invisible 1x1 GIF Tracking Pixel**: Serves a 43-byte transparent GIF with strict cache-busting headers (`no-store`, `no-cache`, `max-age=0`).
- **Telemetry Extraction**: Parses client User-Agent and IP to identify device type (Mobile/Desktop/Tablet), email client (Gmail, Apple Mail, Outlook), and detect privacy proxies (Apple Mail Privacy Protection, Google Image Proxy).
- **Real-Time Alert Dispatch**:
  - **WebSockets**: Live event stream for dashboards and mobile clients (`/ws/alerts/{sender_id}`).
  - **Redis Pub/Sub**: Distributed event bus for multi-worker scaling.
- **Link Click Tracking**: Redirect proxy for tracking links clicked inside emails (`/api/v1/track/click/{token}?url=...`).
- **SQLAlchemy (Async)**: Compatible with **PostgreSQL** (`asyncpg`) and SQLite (for local dev).

---

## 🛠️ Quick Start

### 1. Activate Virtual Environment
```bash
# Windows
.\venv\Scripts\activate

# Linux / macOS
source venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure `.env`
Copy `.env.example` to `.env` and configure your settings:
```ini
# PostgreSQL (Production / Local DB):
DATABASE_URL="postgresql+asyncpg://user:password@localhost:5432/email_alerts_db"

# Or SQLite (Development fallback):
# DATABASE_URL="sqlite+aiosqlite:///./email_alerts.db"

# Redis (Set REDIS_ENABLED=True for distributed Redis Pub/Sub):
REDIS_URL="redis://localhost:6379/0"
REDIS_ENABLED=False
```

### 4. Start the Server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Interactive API documentation will be available at:
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 📡 API Endpoints

### 1. Track an Email
**`POST /api/v1/emails/track`**
```json
{
  "recipient_email": "jane@acme.com",
  "subject": "Proposal Discussion",
  "sender_id": "user_42",
  "html_body": "<html><body><p>Hi Jane, please see the proposal.</p></body></html>",
  "meta_data": {"campaign": "q4_enterprise"}
}
```
**Response:**
```json
{
  "id": "c1f7...",
  "sender_id": "user_42",
  "tracking_token": "trk_abc123...",
  "recipient_email": "jane@acme.com",
  "status": "SENT",
  "tracking_pixel_url": "http://localhost:8000/api/v1/track/open/trk_abc123....gif",
  "injected_html": "<html><body><p>Hi Jane, please see the proposal.</p><img src=\"http://localhost:8000/api/v1/track/open/trk_abc123....gif\" ... />\n</body></html>"
}
```

### 2. Tracking Pixel Endpoint
**`GET /api/v1/track/open/{tracking_token}.gif`**
- Returns 1x1 transparent GIF with `Cache-Control: no-cache, no-store`.
- Asynchronously logs the open event and triggers real-time alerts.

### 3. Real-Time Alert WebSocket
**`WS /ws/alerts/{sender_id}`** (or `WS /ws/alerts` for all alerts)
- Emits real-time event when pixel is opened:
```json
{
  "event": "EMAIL_OPENED",
  "tracked_email_id": "c1f7...",
  "tracking_token": "trk_abc123...",
  "sender_id": "user_42",
  "recipient_email": "jane@acme.com",
  "subject": "Proposal Discussion",
  "open_count": 1,
  "is_first_open": true,
  "opened_at": "2026-09-07T10:50:00Z",
  "client_info": {
    "device_type": "MOBILE",
    "client_name": "Apple Mail",
    "os_name": "iOS 17.4",
    "is_proxy": false
  }
}
```

---

## 🧪 Testing

Run automated tests:
```bash
pytest -v
```

### Live CLI Demo
1. Terminal 1 (Start server):
   ```bash
   uvicorn app.main:app --reload
   ```
2. Terminal 2 (Listen to real-time WebSocket alerts):
   ```bash
   python scripts/listen_ws.py default_sender
   ```
3. Terminal 3 (Simulate email send & open):
   ```bash
   python scripts/simulate_send_and_open.py
   ```
