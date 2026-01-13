# app/config.py
from pydantic import Field
from pydantic_settings import BaseSettings
import pathlib
from dotenv import load_dotenv

# Explicitly load the .env file
env_path = pathlib.Path(__file__).parent / ".env"
load_dotenv(env_path)

class Settings(BaseSettings):
    app_name: str = Field("SaaS Bot Conciergerie - Backend", env="APP_NAME")
    debug: bool = Field(False, env="DEBUG")
    log_level: str = Field("INFO", env="LOG_LEVEL")
    host: str = Field("127.0.0.1", env="HOST")
    port: int = Field(8000, env="PORT")
    jwt_secret_key: str = Field(env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field("HS256", env="JWT_ALGORITHM")
    jwt_expiration_hours: int = Field(24, env="JWT_EXPIRATION_HOURS")

    # Admin token for sensitive endpoints
    admin_token: str = Field(env="ADMIN_TOKEN")
    production: bool = Field(False, env="PRODUCTION")
    db_prod_url: str = Field(env="DB_PROD_URL")

    # Database
    db_host: str = Field("", env="DB_HOST")
    db_port: int = Field(5432, env="DB_PORT")
    db_name: str = Field("", env="DB_NAME")
    db_user: str = Field("", env="DB_USER")
    db_password: str = Field("", env="DB_PASSWORD")

    # Frontend URL for links in emails
    frontend_url: str = Field("", env="FRONTEND_URL")

    # Upload settings
    upload_dir: str = Field("uploads", env="UPLOAD_DIR")
    max_upload_size_mb: int = Field(10, env="MAX_UPLOAD_SIZE_MB")

    # LLM API keys
    anthropic_api_key: str = Field("", env="ANTHROPIC_API_KEY")
    openai_api_key: str = Field("", env="OPENAI_API_KEY")

    # Encryption key for API keys storage
    encryption_master_key: str = Field(env="ENCRYPTION_MASTER_KEY")

    # OAuth 2.1 settings for MCP servers
    api_url: str = Field("http://localhost:8000", env="API_URL")
    oauth_client_id: str = Field("mcp-client", env="OAUTH_CLIENT_ID")
    oauth_metadata_cache_ttl: int = Field(3600, env="OAUTH_METADATA_CACHE_TTL")  # Default: 1 hour (3600s)

    # RAG Configuration
    embedding_model: str = Field("text-embedding-3-large", env="EMBEDDING_MODEL")
    embedding_dim: int = Field(3072, env="EMBEDDING_DIM")
    chunk_size: int = Field(1000, env="CHUNK_SIZE")
    chunk_overlap: int = Field(200, env="CHUNK_OVERLAP")

    class Config:
        env_file = pathlib.Path(__file__).parent / "config/.env"
        env_file_encoding = "utf-8"

settings = Settings()