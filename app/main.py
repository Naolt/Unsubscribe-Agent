from fastapi import FastAPI
from app.config import settings  # ensures .env is loaded at startup
from app.handlers import email_handler

app = FastAPI(title="Unsubscribe Agent API")

@app.get("/")
async def root():
    return {"status": "running"}


mock_payload = {
  "email_id": "12345",
  "from": "newsletter@shoppingworld.com",
  "to": "naol@example.com",
  "subject": "Your Weekly Deals Are Here!",
  "headers": {
    "Message-ID": "<abc123@shoppingworld.com>",
    "Date": "Mon, 16 Sep 2025 14:22:01 +0000",
    "List-Unsubscribe": "<mailto:unsubscribe@shoppingworld.com?subject=unsubscribe>, <https://shoppingworld.com/unsubscribe?uid=12345>"
  },
  "body_preview": "Check out our latest offers and discounts...",
  "unsubscribe_links": [
    "mailto:unsubscribe@shoppingworld.com?subject=unsubscribe",
    "https://shoppingworld.com/unsubscribe?uid=12345"
  ]
}


@app.post("/webhook")
async def webhook(email_data: dict):
    # Pass raw email to handler
    result = await email_handler.process_email(email_data)
    return {"result": result}
