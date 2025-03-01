import os
from pydantic import BaseSettings, PostgresDsn

class Settings(BaseSettings):
    API_VERSION: str = "v1"
    PROJECT_NAME: str = "Kyren"
    
    # Database settings
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    POSTGRES_SERVER: str = os.getenv("POSTGRES_SERVER", "db")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "kyren")
    
    DATABASE_URI: PostgresDsn = PostgresDsn.build(
        scheme="postgresql",
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        host=POSTGRES_SERVER,
        port=POSTGRES_PORT,
        path=f"/{POSTGRES_DB}",
    )
    
    # Bale API settings
    BALE_TOKEN: str = os.getenv("BALE_TOKEN", "")
    BALE_API_URL: str = os.getenv("BALE_API_URL", "https://tapi.bale.ai")
    
    # Security settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    
    # CORS settings
    CORS_ORIGINS: list = ["*"]  # In production, specify actual origins

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()