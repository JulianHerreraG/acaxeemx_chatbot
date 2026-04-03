from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    firebase_credentials_path: str
    openai_api_key: str
    anthropic_api_key: str
    app_env: str = "development"
    log_level: str = "INFO"
    port: int = 8000

    class Config:
        env_file = ".env"

settings = Settings()