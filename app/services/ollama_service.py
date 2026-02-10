"""
Ollama API wrapper service for on-demand local model access.

This service manages Ollama lifecycle and provides HTTP endpoints
for local model communication without keeping Ollama running constantly.
"""

import asyncio
import logging
import subprocess
import time
from typing import Optional, Dict, Any, List, Union
from pathlib import Path
import aiohttp
import json
from app.config import settings

logger = logging.getLogger(__name__)


class OllamaService:
    """Service for managing Ollama lifecycle and API communication"""
    
    def __init__(self, 
                 ollama_path: str = "ollama",
                 base_url: str = "http://localhost:11434",
                 default_model: Optional[str] = None,
                 timeout: int = 30,
                 idle_timeout: int = 300):  # 5 minutes
        self.ollama_path = ollama_path
        self.base_url = base_url
        self.default_model = default_model or settings.BROWSER_MODEL_NAME
        self.timeout = timeout
        self.idle_timeout = idle_timeout
        
        self._process: Optional[subprocess.Popen] = None
        self._last_used = 0
        self._session: Optional[aiohttp.ClientSession] = None
        
        logger.info(f"OllamaService initialized with model: {default_model}")
    
    async def __aenter__(self):
        """Async context manager entry"""
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self._session:
            await self._session.close()
        await self.stop()
    
    async def start(self) -> bool:
        """Start Ollama server if not already running"""
        try:
            # Check if already running
            if await self._is_running():
                logger.info("Ollama is already running")
                return True
            
            logger.info("Starting Ollama server...")
            
            # Start Ollama server
            self._process = subprocess.Popen(
                [self.ollama_path, "serve"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Check if process started successfully
            if self._process.poll() is not None:
                # Process has already terminated
                stdout, stderr = self._process.communicate()
                logger.error(f"Ollama process failed to start. stdout: {stdout}, stderr: {stderr}")
                return False
            
            # Wait for server to be ready (simplified approach)
            import time
            time.sleep(3)  # Give it time to start
            
            # Test if it's running using requests (like our simple test)
            try:
                import requests
                response = requests.get(f"{self.base_url}/api/tags", timeout=5)
                if response.status_code == 200:
                    logger.info("Ollama server started successfully")
                    self._last_used = time.time()
                    return True
            except:
                pass
            
            logger.error("Failed to start Ollama server - not responding")
            return False
            
        except Exception as e:
            logger.error(f"Error starting Ollama: {e}")
            return False
    
    async def stop(self) -> bool:
        """Stop Ollama server"""
        try:
            if self._process:
                logger.info("Stopping Ollama server...")
                self._process.terminate()
                self._process.wait(timeout=10)
                self._process = None
                logger.info("Ollama server stopped")
            return True
        except Exception as e:
            logger.error(f"Error stopping Ollama: {e}")
            return False
    
    async def _is_running(self) -> bool:
        """Check if Ollama server is running"""
        try:
            # Create a temporary session for the check
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=5)
            ) as temp_session:
                async with temp_session.get(f"{self.base_url}/api/tags") as response:
                    return response.status == 200
        except:
            return False
    
    async def ensure_running(self) -> bool:
        """Ensure Ollama is running, start if needed"""
        if await self._is_running():
            self._last_used = time.time()
            return True
        
        return await self.start()
    
    async def chat(self, 
                   messages: List[Dict[str, str]], 
                   model: Optional[str] = None,
                   stream: bool = False,
                   tools: Optional[List[Dict[str, Any]]] = None,
                   think: Optional[bool] = None,
                   format: Optional[Union[str, dict]] = None,
                   options: Optional[Dict[str, Any]] = None,
                   keep_alive: Optional[Union[float, str]] = None) -> Dict[str, Any]:
        """
        Send chat request to Ollama
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model name (defaults to self.default_model)
            stream: Whether to stream the response
            tools: List of tools for function calling
            think: Enable thinking mode
            format: Output format (e.g., 'json' or JSON schema)
            options: Model options (temperature, top_p, etc.)
            keep_alive: Keep model in memory for specified duration
            
        Returns:
            Response from Ollama API
        """
        if not await self.ensure_running():
            raise RuntimeError("Failed to start Ollama server")
        
        # Ensure session is created
        if not self._session:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            )
        
        model = model or self.default_model
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream
        }
        
        # Add optional parameters if provided
        if tools is not None:
            payload["tools"] = tools
        if think is not None:
            payload["think"] = think
        if format is not None:
            payload["format"] = format
        if options is not None:
            payload["options"] = options
        if keep_alive is not None:
            payload["keep_alive"] = keep_alive
        
        try:
            async with self._session.post(
                f"{self.base_url}/api/chat",
                json=payload
            ) as response:
                if response.status != 200:
                    raise RuntimeError(f"Ollama API error: {response.status}")
                
                if stream:
                    # Handle streaming response
                    result = {"content": ""}
                    async for line in response.content:
                        if line:
                            try:
                                data = json.loads(line.decode())
                                if "message" in data and "content" in data["message"]:
                                    result["content"] += data["message"]["content"]
                            except json.JSONDecodeError:
                                continue
                    return result
                else:
                    return await response.json()
                    
        except Exception as e:
            logger.error(f"Error calling Ollama API: {e}")
            raise
    
    async def generate(self, 
                      prompt: str, 
                      model: Optional[str] = None,
                      stream: bool = False) -> str:
        """
        Generate text from a prompt
        
        Args:
            prompt: Input prompt
            model: Model name (defaults to self.default_model)
            stream: Whether to stream the response
            
        Returns:
            Generated text
        """
        if not await self.ensure_running():
            raise RuntimeError("Failed to start Ollama server")
        
        # Ensure session is created
        if not self._session:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            )
        
        model = model or self.default_model
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": stream
        }
        
        try:
            async with self._session.post(
                f"{self.base_url}/api/generate",
                json=payload
            ) as response:
                if response.status != 200:
                    raise RuntimeError(f"Ollama API error: {response.status}")
                
                if stream:
                    # Handle streaming response
                    result = ""
                    async for line in response.content:
                        if line:
                            try:
                                data = json.loads(line.decode())
                                if "response" in data:
                                    result += data["response"]
                            except json.JSONDecodeError:
                                continue
                    return result
                else:
                    data = await response.json()
                    return data.get("response", "")
                    
        except Exception as e:
            logger.error(f"Error calling Ollama generate API: {e}")
            raise
    
    async def list_models(self) -> List[str]:
        """List available models"""
        if not await self.ensure_running():
            raise RuntimeError("Failed to start Ollama server")
        
        # Ensure session is created
        if not self._session:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            )
        
        try:
            async with self._session.get(f"{self.base_url}/api/tags") as response:
                if response.status != 200:
                    raise RuntimeError(f"Ollama API error: {response.status}")
                
                data = await response.json()
                return [model["name"] for model in data.get("models", [])]
                
        except Exception as e:
            logger.error(f"Error listing models: {e}")
            raise
    
    async def pull_model(self, model: str) -> bool:
        """Pull/download a model"""
        if not await self.ensure_running():
            raise RuntimeError("Failed to start Ollama server")
        
        try:
            payload = {"name": model}
            async with self._session.post(
                f"{self.base_url}/api/pull",
                json=payload
            ) as response:
                return response.status == 200
                
        except Exception as e:
            logger.error(f"Error pulling model {model}: {e}")
            return False
    
    def should_auto_stop(self) -> bool:
        """Check if Ollama should be auto-stopped due to inactivity"""
        if not self._process:
            return False
        
        idle_time = time.time() - self._last_used
        return idle_time > self.idle_timeout
    
    async def auto_stop_if_idle(self):
        """Auto-stop Ollama if it's been idle too long"""
        if self.should_auto_stop():
            logger.info("Auto-stopping Ollama due to inactivity")
            await self.stop()


# Global instance - lazy initialization
ollama_service = None

def get_ollama_service():
    """Get or create the global Ollama service instance"""
    global ollama_service
    if ollama_service is None:
        ollama_service = OllamaService()
    return ollama_service
