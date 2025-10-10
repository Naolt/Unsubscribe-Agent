"""
FastAPI router for Ollama-compatible API endpoints.

This router provides endpoints that match the native Ollama API format
so that ChatOllama can work with our managed Ollama service.
"""

import logging
from typing import Optional, Union, Mapping, Sequence, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.ollama_service import get_ollama_service
from app.config import settings

logger = logging.getLogger(__name__)

# This router has no prefix so endpoints are at root level
router = APIRouter(tags=["ollama-api"])


class OllamaMessage(BaseModel):
    role: str
    content: Optional[str] = None
    thinking: Optional[str] = None
    images: Optional[Sequence[Any]] = None


class OllamaChatRequest(BaseModel):
    model: str
    messages: Optional[Sequence[OllamaMessage]] = None
    tools: Optional[Sequence[Any]] = None
    stream: bool = False
    think: Optional[bool] = None
    format: Optional[Union[str, dict]] = None
    options: Optional[Union[Mapping[str, Any], dict]] = None
    keep_alive: Optional[Union[float, str]] = None


class OllamaChatResponse(BaseModel):
    model: str
    message: OllamaMessage
    done: bool = True
    total_duration: Optional[int] = None
    load_duration: Optional[int] = None
    prompt_eval_count: Optional[int] = None
    prompt_eval_duration: Optional[int] = None
    eval_count: Optional[int] = None
    eval_duration: Optional[int] = None


@router.post("/api/chat", response_model=OllamaChatResponse)
async def ollama_chat(request: OllamaChatRequest):
    """
    Ollama-compatible chat endpoint that matches the native Ollama API.
    This allows ChatOllama to work with our managed Ollama service.
    """
    try:
        # Print user messages in the message list
        user_messages = [msg.content for msg in (request.messages or []) if msg.role == "user"]
        logger.info(f"Ollama chat request user messages: {user_messages}")
        # Get our Ollama service
        ollama_service = get_ollama_service()
        
        # Ensure Ollama is running
        await ollama_service.ensure_running()
        
        # Convert Ollama messages to our internal format
        internal_messages = []
        for msg in request.messages or []:
            internal_messages.append({
                "role": msg.role,
                "content": msg.content or ""
            })
        
        # Use the model from request or default
        model = request.model or settings.BROWSER_MODEL_NAME
        
        # Call our Ollama service with all parameters
        response = await ollama_service.chat(
            messages=internal_messages,
            model=model,
            stream=request.stream,
            tools=request.tools,
            think=request.think,
            format=request.format,
            options=request.options,
            keep_alive=request.keep_alive
        )
        
        # Get the response content from Ollama's response format
        if isinstance(response, dict):
            if "message" in response and isinstance(response["message"], dict):
                response_content = response["message"].get("content", "")
            else:
                response_content = response.get("content", "") or str(response)
        else:
            response_content = str(response)
        
        # Convert response to Ollama format
        ollama_message = OllamaMessage(
            role="assistant",
            content=response_content
        )

        logger.info(f"Ollama chat response: {ollama_message}")
        
        return OllamaChatResponse(
            model=model,
            message=ollama_message,
            done=True,
            total_duration=1000000000,  # 1 second in nanoseconds
            load_duration=100000000,    # 0.1 second
            prompt_eval_count=len(internal_messages),
            prompt_eval_duration=500000000,  # 0.5 second
            eval_count=len(response_content.split()) if response_content else 0,
            eval_duration=400000000  # 0.4 second
        )
        
    except Exception as e:
        logger.error(f"Error in Ollama chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))
