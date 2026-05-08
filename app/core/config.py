from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional, List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Application
    app_name: str = "Agentic AI Fraud Investigator"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = "development"
    
    # Database
    database_url: str = Field(
        default="postgresql://postgres:password@localhost:5432/fraud_investigator",
        env="DATABASE_URL"
    )
    
    # Redis
    redis_url: str = Field(
        default="redis://localhost:6379",
        env="REDIS_URL"
    )
    
    # LLM Configuration
    openai_api_key: Optional[str] = Field(None, env="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(None, env="ANTHROPIC_API_KEY")
    cerebras_api_key: Optional[str] = Field(None, env="CEREBRAS_API_KEY")
    gemini_api_key: Optional[str] = Field(None, env="GEMINI_API_KEY")
    openai_model: str = "gpt-4-turbo-preview"
    anthropic_model: str = "claude-3-opus-20240229"
    cerebras_model: str = "llama3.1-8b"
    gemini_model: str = "gemini-1.5-flash"
    
    # Security
    secret_key: str = Field(
        default="your-secret-key-here",
        env="SECRET_KEY"
    )
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Fraud Detection Settings
    risk_score_threshold: float = 0.7
    transaction_amount_threshold: float = 10000.0
    max_investigation_time_hours: int = 24
    
    # Monitoring
    enable_sentry: bool = False
    sentry_dsn: Optional[str] = Field(None, env="SENTRY_DSN")
    
    # LangSmith Configuration
    langsmith_enabled: bool = False
    langsmith_api_key: Optional[str] = Field(None, env="LANGSMITH_API_KEY")
    langsmith_project: str = Field(default="fraud-investigator", env="LANGSMITH_PROJECT")
    langsmith_endpoint: Optional[str] = Field(None, env="LANGSMITH_ENDPOINT")
    langsmith_tracing: bool = Field(default=True, env="LANGSMITH_TRACING")
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"
    
    # API Configuration
    api_v1_prefix: str = "/api/v1"
    cors_origins: List[str] = ["*"]
    
    # Server Configuration
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    
    # Celery Configuration
    celery_broker_url: str = Field(
        default="redis://localhost:6379/0",
        env="CELERY_BROKER_URL"
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/0",
        env="CELERY_RESULT_BACKEND"
    )


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings."""
    return settings


# Database configuration
class DatabaseConfig:
    url = settings.database_url
    echo = settings.debug
    pool_size = 10
    max_overflow = 20


# Redis configuration
class RedisConfig:
    url = settings.redis_url
    decode_responses = True
    socket_connect_timeout = 5
    socket_timeout = 5


# LLM configuration
class LLMConfig:
    openai_api_key = settings.openai_api_key
    anthropic_api_key = settings.anthropic_api_key
    cerebras_api_key = settings.cerebras_api_key
    gemini_api_key = settings.gemini_api_key
    openai_model = settings.openai_model
    anthropic_model = settings.anthropic_model
    cerebras_model = settings.cerebras_model
    gemini_model = settings.gemini_model
    temperature = 0.1
    max_tokens = 4000


# Security configuration
class SecurityConfig:
    secret_key = settings.secret_key
    algorithm = settings.algorithm
    access_token_expire_minutes = settings.access_token_expire_minutes


# LangSmith configuration
class LangSmithConfig:
    enabled = settings.langsmith_enabled
    api_key = settings.langsmith_api_key
    project = settings.langsmith_project
    endpoint = settings.langsmith_endpoint
    tracing = settings.langsmith_tracing