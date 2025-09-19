# llm_instance.py
from langchain.chat_models import init_chat_model
    

def get_llm(model_name:str , model_provider:str):
    llm = init_chat_model(model_name, model_provider=model_provider)
    return llm


gemini_llm = get_llm(model_name="gemini-2.5-flash", model_provider="google_genai")