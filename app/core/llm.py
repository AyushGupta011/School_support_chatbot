import os
from langchain_core.language_models.chat_models import BaseChatModel
from app.core.config import settings

def _create_provider(provider_name: str, fallback_model: str = None) -> BaseChatModel | None:
    provider = provider_name.lower()
    model_name = settings.llm_model if fallback_model is None else fallback_model
    
    groq_key = (
        (settings.groq_api_key.get_secret_value() if settings.groq_api_key else None)
        or os.environ.get("GROQ_API_KEY")
    )
    google_key = (
        (settings.google_api_key.get_secret_value() if settings.google_api_key else None)
        or os.environ.get("GOOGLE_API_KEY")
        or os.environ.get("GEMINI_API_KEY")
    )
    openai_key = (
        (settings.openai_api_key.get_secret_value() if settings.openai_api_key else None)
        or os.environ.get("OPENAI_API_KEY")
    )
    nvidia_key = (
        (settings.nvidia_api_key.get_secret_value() if settings.nvidia_api_key else None)
        or os.environ.get("NVIDIA_API_KEY")
    )

    try:
        if (provider == "gemini" or provider == "google") and google_key:
            from langchain_google_genai import ChatGoogleGenerativeAI
            m = model_name if fallback_model is None else "gemini-2.5-flash"
            if "1.5" in m or "2.0" in m or "3.7" in m:
                m = "gemini-2.5-flash"
            return ChatGoogleGenerativeAI(model=m, google_api_key=google_key, temperature=0, streaming=True)
            
        elif provider == "groq" and groq_key:
            from langchain_groq import ChatGroq
            m = model_name if fallback_model is None else "qwen/qwen3.8-27b"
            if "oss-20b" in m.lower() or "oss-120b" in m.lower() or "llama-3.1-8b-instant" in m.lower():
                m = "qwen/qwen3.8-27b"
            return ChatGroq(model=m, groq_api_key=groq_key, max_tokens=600, temperature=0, streaming=True)
            
        elif provider == "nvidia" and nvidia_key:
            try:
                from langchain_nvidia_ai_endpoints import ChatNVIDIA
                m = model_name if fallback_model is None else "meta/llama-3.1-70b-instruct"
                return ChatNVIDIA(model=m, api_key=nvidia_key, temperature=0, streaming=True)
            except ImportError:
                pass
            
        elif provider == "openai" and openai_key and openai_key != "your_openai_api_key":
            from langchain_openai import ChatOpenAI
            m = model_name if fallback_model is None else "gpt-4o-mini"
            return ChatOpenAI(model=m, api_key=openai_key, temperature=0, streaming=True)
    except Exception as e:
        import logging
        logging.warning(f"Failed to initialize LLM provider {provider}: {e}")
        
    return None

def get_llm():
    primary_provider = settings.llm_provider.lower()
    
    providers_with_defaults = {
        "groq": "qwen/qwen3.8-27b",
        "gemini": "gemini-2.5-flash",
        "openai": "gpt-4o-mini",
        "nvidia": "meta/llama-3.1-70b-instruct"
    }
    
    primary_llm = _create_provider(primary_provider, None)
    
    # Build list of available fallback LLMs based on available API keys
    fallbacks = []
    for p, default_m in providers_with_defaults.items():
        if p != primary_provider:
            fallback_llm = _create_provider(p, default_m)
            if fallback_llm:
                fallbacks.append(fallback_llm)
                
    if not primary_llm:
        if fallbacks:
            primary_llm = fallbacks.pop(0)
        else:
            # Absolute dummy fallback if no keys at all are configured
            from langchain_openai import ChatOpenAI
            class DummyLLM:
                def invoke(self, *args, **kwargs):
                    class Res: content = "No API keys configured. Please configure your LLM provider API key in .env."
                    return Res()
                async def ainvoke(self, *args, **kwargs):
                    return self.invoke(*args, **kwargs)
                def bind_tools(self, *args, **kwargs): return self
                def with_structured_output(self, schema, *args, **kwargs):
                    class DummyStruct:
                        def invoke(self, *a, **k):
                            if hasattr(schema, "__fields__") or hasattr(schema, "model_fields"):
                                try:
                                    return schema(intent="knowledge", confidence=0.8)
                                except Exception:
                                    pass
                            class Res:
                                intent = "knowledge"
                                confidence = 0.8
                            return Res()
                        async def ainvoke(self, *a, **k):
                            return self.invoke(*a, **k)
                    return DummyStruct()
                def with_fallbacks(self, *args, **kwargs): return self
            return DummyLLM()
            
    # Simply return the primary LLM to avoid Pydantic v2 ValueError with monkey-patching RunnableWithFallbacks
    return primary_llm
