"""
Factory for creating browser-use compatible LLM instances.

This factory creates the appropriate LLM instance based on configuration,
using browser-use's built-in providers (ChatOllama, ChatGoogle, etc.).
"""

import logging
from typing import Optional, Any
from app.config import settings

logger = logging.getLogger(__name__)


def create_browser_llm(
    provider: Optional[str] = None,
    model_name: Optional[str] = None,
    **kwargs
) -> Any:
    """
    Create a browser-use compatible LLM instance based on configuration.
    
    Args:
        provider: LLM provider ("ollama" or "gemini")
        model_name: Model name to use
        **kwargs: Additional arguments for the LLM instance
        
    Returns:
        Browser-use compatible LLM instance
        
    Raises:
        ValueError: If provider is not supported
        ImportError: If required dependencies are not available
    """
    # Use configuration defaults if not provided
    provider = provider or settings.BROWSER_LLM_PROVIDER
    model_name = model_name or _get_default_model_name(provider)
    
    logger.info(f"Creating browser LLM: provider={provider}, model={model_name}")
    
    if provider.lower() == "ollama":
        return _create_ollama_llm(model_name, **kwargs)
    elif provider.lower() == "gemini":
        return _create_gemini_llm(model_name, **kwargs)
    else:
        raise ValueError(f"Unsupported browser LLM provider: {provider}. Supported providers: ollama, gemini")


def _get_default_model_name(provider: str) -> str:
    """Get the default model name for a provider."""
    # Use BROWSER_MODEL_NAME for all providers
    # If it's still the default Ollama model and provider is Gemini, fall back to email model
    if provider.lower() == "gemini" and settings.BROWSER_MODEL_NAME == "tinyllama:1.1b":
        return settings.LLM_MODEL_NAME or "gemini-2.5-flash"
    return settings.BROWSER_MODEL_NAME


def _create_ollama_llm(model_name: str, **kwargs) -> Any:
    """Create an Ollama LLM instance for browser-use."""
    try:
        from browser_use.llm import ChatOllama
        
        # Default host for our managed Ollama API
        host = kwargs.pop("host", "http://localhost:8000")
        
        return ChatOllama(
            model=model_name,
            host=host,
            **kwargs
        )
    except ImportError as e:
        logger.error(f"Failed to import ChatOllama: {e}")
        raise ImportError("ChatOllama is required for Ollama support. Make sure browser-use is properly installed.")


def _create_gemini_llm(model_name: str, **kwargs) -> Any:
    """Create a Gemini LLM instance for browser-use."""
    try:
        from browser_use.llm import ChatGoogle
        
        # Get API key from settings
        api_key = kwargs.pop("api_key", settings.GOOGLE_API_KEY)
        if not api_key:
            raise ValueError("GOOGLE_API_KEY is required for Gemini support")
        
        return ChatGoogle(
            model=model_name,
            api_key=api_key,
            **kwargs
        )
    except ImportError as e:
        logger.error(f"Failed to import ChatGoogle: {e}")
        raise ImportError("ChatGoogle is required for Gemini support. Make sure browser-use is properly installed.")
    except Exception as e:
        logger.error(f"Failed to create Gemini LLM: {e}")
        raise


def get_configured_browser_llm(**kwargs) -> Any:
    """
    Get a browser LLM instance using the current configuration.
    
    Args:
        **kwargs: Additional arguments for the LLM instance
        
    Returns:
        Browser-use compatible LLM instance
    """
    return create_browser_llm(**kwargs)


# Convenience functions for specific providers
def create_ollama_browser_llm(model_name: Optional[str] = None, **kwargs) -> Any:
    """Create an Ollama LLM instance for browser-use."""
    return create_browser_llm(provider="ollama", model_name=model_name, **kwargs)


def create_gemini_browser_llm(model_name: Optional[str] = None, **kwargs) -> Any:
    """Create a Gemini LLM instance for browser-use."""
    return create_browser_llm(provider="gemini", model_name=model_name, **kwargs)
