# llm_instance.py
from langchain.chat_models import init_chat_model
from typing import Optional
    

def get_llm(model_name: str, model_provider: str):
    llm = init_chat_model(model_name, model_provider=model_provider)
    return llm


# Lazy initialization - only create the LLM when first accessed
_gemini_llm: Optional[object] = None


def get_gemini_llm():
    """Get the Gemini LLM instance, creating it if it doesn't exist yet."""
    global _gemini_llm
    if _gemini_llm is None:
        _gemini_llm = get_llm(model_name="gemini-2.5-flash", model_provider="google_genai")
    return _gemini_llm