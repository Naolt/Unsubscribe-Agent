"""
FastAPI router for Ollama local model endpoints.

Provides HTTP API endpoints for local model communication
without keeping Ollama running constantly.
"""

import logging
from typing import List, Optional, Dict, Any, Union, Mapping, Sequence
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from app.services.ollama_service import get_ollama_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ollama", tags=["ollama"])


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    model: Optional[str] = None
    stream: bool = False


class GenerateRequest(BaseModel):
    prompt: str
    model: Optional[str] = None
    stream: bool = False


class ModelListResponse(BaseModel):
    models: List[str]


class ChatResponse(BaseModel):
    content: str
    model: str


class GenerateResponse(BaseModel):
    response: str
    model: str




@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Send a chat request to the local Ollama model.
    
    This endpoint will:
    1. Start Ollama if not running
    2. Send the chat request
    3. Return the response
    4. Auto-stop Ollama after idle timeout
    """
    try:
        logger.info(f"Chat request with {len(request.messages)} messages")
        
        # Convert Pydantic models to dicts
        messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]
        
        ollama_service = get_ollama_service()
        # Don't use context manager for chat - we want to keep Ollama running for auto-stop
        response = await ollama_service.chat(
            messages=messages,
            model=request.model,
            stream=request.stream
        )
        
        # Extract content from response
        if "message" in response and "content" in response["message"]:
            content = response["message"]["content"]
        elif "content" in response:
            content = response["content"]
        else:
            content = str(response)
        
        # Schedule auto-stop check after successful chat
        await ollama_service.auto_stop_if_idle()
        
        return ChatResponse(
            content=content,
            model=request.model or ollama_service.default_model
        )
            
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest):
    """
    Generate text from a prompt using the local Ollama model.
    
    This endpoint will:
    1. Start Ollama if not running
    2. Generate text from the prompt
    3. Return the generated text
    4. Auto-stop Ollama after idle timeout
    """
    try:
        logger.info(f"Generate request with prompt: {request.prompt[:100]}...")
        
        ollama_service = get_ollama_service()
        # Don't use context manager for generate - we want to keep Ollama running for auto-stop
        response = await ollama_service.generate(
            prompt=request.prompt,
            model=request.model,
            stream=request.stream
        )
        
        # Schedule auto-stop check after successful generation
        await ollama_service.auto_stop_if_idle()
        
        return GenerateResponse(
            response=response,
            model=request.model or ollama_service.default_model
        )
            
    except Exception as e:
        logger.error(f"Error in generate endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models", response_model=ModelListResponse)
async def list_models():
    """List available Ollama models"""
    try:
        ollama_service = get_ollama_service()
        # Don't use context manager for models - we want to keep Ollama running for auto-stop
        models = await ollama_service.list_models()
        
        # Schedule auto-stop check after successful model listing
        await ollama_service.auto_stop_if_idle()
        
        return ModelListResponse(models=models)
            
    except Exception as e:
        logger.error(f"Error listing models: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/models/{model_name}/pull")
async def pull_model(model_name: str):
    """Pull/download a specific model"""
    try:
        logger.info(f"Pulling model: {model_name}")
        
        ollama_service = get_ollama_service()
        async with ollama_service:
            success = await ollama_service.pull_model(model_name)
            
            if success:
                return {"message": f"Model {model_name} pulled successfully"}
            else:
                raise HTTPException(status_code=500, detail=f"Failed to pull model {model_name}")
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error pulling model {model_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/start")
async def start_ollama():
    """Manually start Ollama server"""
    try:
        ollama_service = get_ollama_service()
        # Don't use context manager for start - we want to keep it running
        success = await ollama_service.start()
        
        if success:
            return {"message": "Ollama started successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to start Ollama")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting Ollama: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop")
async def stop_ollama():
    """Manually stop Ollama server"""
    try:
        success = await get_ollama_service().stop()
        
        if success:
            return {"message": "Ollama stopped successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to stop Ollama")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error stopping Ollama: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_status():
    """Get Ollama server status"""
    try:
        ollama_service = get_ollama_service()
        # Don't use context manager for status check - we don't want to stop it
        is_running = await ollama_service._is_running()
        
        return {
            "running": is_running,
            "default_model": ollama_service.default_model,
            "base_url": ollama_service.base_url,
            "idle_timeout": ollama_service.idle_timeout
        }
        
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auto-stop")
async def auto_stop_if_idle():
    """Manually trigger auto-stop if Ollama has been idle"""
    try:
        await get_ollama_service().auto_stop_if_idle()
        return {"message": "Auto-stop check completed"}
        
    except Exception as e:
        logger.error(f"Error in auto-stop: {e}")
        raise HTTPException(status_code=500, detail=str(e))


