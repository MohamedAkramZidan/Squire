from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    model_path: str = "models/squire_int8.onnx"
    encoder_model: str = "microsoft/mdeberta-v3-base"
    max_length: int = 64

settings = Settings()