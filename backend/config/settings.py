from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    model_path: str = "models/squire_int8.onnx"
    encoder_model: str = "microsoft/mdeberta-v3-base"
    max_length: int = 64
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5434/squire"
    create_tables_on_startup: bool = False
    vector_distance_threshold: float = 0.50

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_session_ttl: int = 300  # seconds (5 minutes)
    
    # n8n
    n8n_webhook_url: str = "http://localhost:5678/webhook"

settings = Settings()