# llm_instance.py
import logging
from langchain.chat_models import init_chat_model
from typing import Optional
from app.config import settings

# Set up logger for this module
logger = logging.getLogger(__name__)


def get_llm(model_name: str | None = None, model_provider: str | None = None, api_key: Optional[str] = None):
    """Create an LLM instance with the specified model and provider."""
    try:
        # Prepare kwargs for the LLM initialization
        llm_kwargs = {}
        
        # Add API key if provided
        if api_key:
            if model_provider == "google_genai":
                llm_kwargs["google_api_key"] = api_key
            elif model_provider == "openai":
                llm_kwargs["openai_api_key"] = api_key
            elif model_provider == "anthropic":
                llm_kwargs["anthropic_api_key"] = api_key
        
        logger.info(f"Initializing LLM: {model_name} with provider: {model_provider}")
        if model_name is None:
            model_name = settings.LLM_MODEL_NAME
        if model_provider is None:
            model_provider = settings.LLM_MODEL_PROVIDER
        llm = init_chat_model(model_name, model_provider=model_provider, **llm_kwargs)
        return llm
    except Exception as e:
        logger.error(f"Failed to initialize LLM {model_name or settings.LLM_MODEL_NAME} with provider {model_provider or settings.LLM_MODEL_PROVIDER}: {e}")
        raise


# Lazy initialization - only create the LLM when first accessed
_llm_instance: Optional[object] = None


def get_configured_llm():
    """Get the configured LLM instance, creating it if it doesn't exist yet."""
    global _llm_instance
    if _llm_instance is None:
        # Get API key based on provider
        api_key = None
        if settings.LLM_MODEL_PROVIDER == "google_genai":
            api_key = settings.GOOGLE_API_KEY
        elif settings.LLM_MODEL_PROVIDER == "openai":
            api_key = settings.OPENAI_API_KEY
        elif settings.LLM_MODEL_PROVIDER == "anthropic":
            api_key = settings.ANTHROPIC_API_KEY
        
        if not api_key:
            logger.warning(f"No API key found for provider {settings.LLM_MODEL_PROVIDER}")
        
        _llm_instance = get_llm(
            model_name=settings.LLM_MODEL_NAME,
            model_provider=settings.LLM_MODEL_PROVIDER,
            api_key=api_key
        )
    return _llm_instance


# Backward compatibility
def get_gemini_llm():
    """Get the configured LLM instance (backward compatibility)."""
    return get_configured_llm()