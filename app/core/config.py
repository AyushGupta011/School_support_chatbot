from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/school_chatbot"
    redis_url: str = "redis://localhost:6379/0"
    
    jwt_secret: SecretStr = SecretStr("default_secret")
    jwt_expiry_minutes: int = 60
    
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o"
    embedding_model: str = "text-embedding-3-small"
    reranker_choice: str = "cohere"
    
    langchain_tracing_v2: bool = False
    langchain_api_key: SecretStr | None = None
    langchain_endpoint: str = "https://api.smith.langchain.com"
    langchain_project: str = "school_chatbot_dev"
    langchain_eval_project: str = "school_chatbot_eval"
    
    cache_similarity_threshold: float = 0.9
    retrieval_top_k: int = 5
    confidence_threshold: float = 0.75
    eval_thresholds: float = 0.8

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
