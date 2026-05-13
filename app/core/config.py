from pathlib import Path
from typing import List, Optional

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# ``config.py`` → ``app/core/`` → repository root is two levels above ``app``.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_DOTENV_FILE = _PROJECT_ROOT / ".env"
# Load cwd ``.env`` first, then repository-root ``.env`` so keys work from either location (root wins on duplicates).
_ENV_FILES: tuple[str, ...] = (
    (".env", str(_DOTENV_FILE)) if _DOTENV_FILE.is_file() else (".env",)
)


def _usable_llm_api_key(value: Optional[str]) -> bool:
    """Reject empty values and obvious ``.env.example`` placeholders (length is not validated)."""
    v = (value or "").strip()
    if not v:
        return False
    low = v.lower()
    if "your_" in low and "here" in low:
        return False
    if low in ("xxx", "changeme", "placeholder", "none", "null"):
        return False
    return True


class Settings(BaseSettings):
    """Runtime configuration loaded from environment and optional `.env` file."""

    model_config = SettingsConfigDict(
        env_file=list(_ENV_FILES),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = Field(default="Agentic AI Fraud Investigator", description="Service name in logs and /health.")
    app_version: str = Field(default="1.0.0", description="Semantic version exposed on /health.")
    debug: bool = Field(default=False, description="Enable verbose diagnostics (never use in production).")
    environment: str = Field(
        default="development",
        description="Deployment stage: development, staging, production, etc.",
    )
    
    # Database
    database_url: str = Field(
        default="postgresql://postgres:password@localhost:5432/fraud_investigator",
        env="DATABASE_URL",
    )
    skip_database_init: bool = Field(
        default=False,
        env="SKIP_DATABASE_INIT",
        description="If true, do not connect to PostgreSQL or run create_all (JSON / in-memory paths only).",
    )
    require_database: bool = Field(
        default=False,
        env="REQUIRE_DATABASE",
        description="If true, startup fails when PostgreSQL is unreachable. If false, log and run without ORM.",
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
    gemini_api_key: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("GEMINI_API_KEY", "GOOGLE_API_KEY"),
        description="Gemini / Google AI Studio key (``GEMINI_API_KEY`` or ``GOOGLE_API_KEY``).",
    )
    openai_model: str = "gpt-4-turbo-preview"
    anthropic_model: str = "claude-3-opus-20240229"
    cerebras_model: str = "llama3.1-8b"
    gemini_model: str = "gemini-2.0-flash"
    
    # Security
    secret_key: str = Field(
        default="your-secret-key-here",
        env="SECRET_KEY"
    )
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    api_key: Optional[str] = Field(
        default=None,
        env="API_KEY",
        description="If set, protected routes require matching X-API-Key. If unset or empty, key checks are disabled (local demos only).",
    )
    
    # Fraud Detection Settings
    risk_score_threshold: float = 0.7
    transaction_amount_threshold: float = 10000.0
    max_investigation_time_hours: int = 24

    # Phase-1 triage narrative (LLM explains deterministic outcome; does not change decisions)
    triage_narrative_enabled: bool = Field(
        default=False,
        env="TRIAGE_NARRATIVE_ENABLED",
        description="When true, POST /v1/triage/assess may call the fast LLM for an initial suspicion note (requires CEREBRAS or GEMINI).",
    )
    triage_narrative_timeout_seconds: float = Field(
        default=25.0,
        env="TRIAGE_NARRATIVE_TIMEOUT_SECONDS",
        ge=2.0,
        le=120.0,
        description="Hard cap for each narrative LLM call during batch triage.",
    )
    
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

    def cerebras_key_usable(self) -> bool:
        return _usable_llm_api_key(self.cerebras_api_key)

    def gemini_key_usable(self) -> bool:
        return _usable_llm_api_key(self.gemini_api_key)

    def llm_narrative_credentials_configured(self) -> bool:
        """True when at least one provider key is present and not an obvious placeholder."""
        return self.cerebras_key_usable() or self.gemini_key_usable()

    def llm_narrative_env_hint(self) -> str:
        """Safe one-line explanation when ``llm_narrative_credentials_configured()`` is false (no secrets)."""
        if self.llm_narrative_credentials_configured():
            return ""
        c = (self.cerebras_api_key or "").strip()
        g = (self.gemini_api_key or "").strip()
        if not c and not g:
            return (
                "No LLM keys loaded. Add ``CEREBRAS_API_KEY`` and/or ``GEMINI_API_KEY`` (or ``GOOGLE_API_KEY``) "
                f"to ``{_DOTENV_FILE}``, or export them in your shell (shell vars override ``.env``)."
            )
        bits = []
        if c and not self.cerebras_key_usable():
            bits.append("``CEREBRAS_API_KEY`` looks like a template/placeholder")
        if g and not self.gemini_key_usable():
            bits.append("``GEMINI_API_KEY`` / ``GOOGLE_API_KEY`` looks like a template/placeholder")
        if bits:
            return " ".join(bits) + " — replace with a real key."
        return ""
settings = Settings()


def get_settings() -> Settings:
    """Get application settings."""
    return settings


class DatabaseConnectionSettings:
    """Read-only SQLAlchemy-style pool defaults (extend when persisting investigations)."""

    url = settings.database_url
    echo = settings.debug
    pool_size = 10
    max_overflow = 20


class RedisClientSettings:
    """Read-only Redis client defaults for caching / task brokers."""

    url = settings.redis_url
    decode_responses = True
    socket_connect_timeout = 5
    socket_timeout = 5


class LlmProviderSettings:
    """Resolved LLM credentials and model identifiers for orchestration code."""

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


class LangSmithObservabilitySettings:
    """LangSmith tracing toggles (optional)."""

    enabled = settings.langsmith_enabled
    api_key = settings.langsmith_api_key
    project = settings.langsmith_project
    endpoint = settings.langsmith_endpoint
    tracing = settings.langsmith_tracing