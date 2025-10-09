"""
Main FastAPI application for the Unsubscribe Agent.

This application provides automated email unsubscription services using browser automation
and domain discovery capabilities.
"""

from fastapi import FastAPI
from app.config import settings  # ensures .env is loaded at startup

# Import routers
from app.routers.core_router import router as core_router
from app.routers.email_router import router as email_router
from app.routers.domain_router import router as domain_router
from app.routers.ollama_router import router as ollama_router
from app.routers.test_router import router as test_router

app = FastAPI(
    title="Unsubscribe Agent API",
    description="""
    ## Automated Email Unsubscription Service
    
    This API automatically processes forwarded emails and unsubscribes from marketing emails using browser automation.
    
    ### How it works:
    1. **Forward emails** to this service via the `/email/webhook` endpoint
    2. **AI analysis** extracts unsubscribe links and methods
    3. **Browser automation** performs the actual unsubscription
    4. **Background processing** handles everything asynchronously
    
    ### Key Features:
    - **Email Processing**: Handles Gumloop Gmail Reader format
    - **Domain Discovery**: Crawls domains to find unsubscribe pages
    - **Local AI Models**: Uses Ollama for privacy-focused AI processing
    - **Browser Automation**: Automated unsubscription via browser
    - **Task Management**: Track processing status and results
    
    ### Quick Start:
    
    **1. Process an email:**
    ```bash
    curl -X POST "http://localhost:8000/email/webhook" \\
      -H "Content-Type: application/json" \\
      -d '{"subjects": "Newsletter", "sender_addresses": "news@example.com", "recipient_addresses": "user@example.com", "email_bodies": "<html>...</html>"}'
    ```
    
    **2. Check task status:**
    ```bash
    curl http://localhost:8000/email/task/{task_id}
    ```
    
    **3. Discover domain unsubscribe pages:**
    ```bash
    curl -X POST "http://localhost:8000/discover/domain" \\
      -H "Content-Type: application/json" \\
      -d '{"domain": "example.com", "max_pages": 10}'
    ```
    
    **4. Use local AI models:**
    ```bash
    curl -X POST "http://localhost:8000/ollama/chat" \\
      -H "Content-Type: application/json" \\
      -d '{"messages": [{"role": "user", "content": "Hello!"}]}'
    ```
    """,
    version="0.1.0"
)

# Include all routers
# app.include_router(core_router)
app.include_router(email_router)
app.include_router(domain_router)
app.include_router(ollama_router)
app.include_router(test_router)