# backend-api/app/config.py
import os
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


# Resolve a default .env path inside backend-api/, but also allow overrides.
_BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_DEFAULT_ENV = os.path.join(_BACKEND_DIR, ".env")
# Optional override via env (useful on Render or CI):
_OVERRIDE_ENV = os.getenv("PHEONA_ENV_FILE")

# Build the load order: override file (if set) -> backend-api/.env -> current cwd .env
_ENV_FILES = tuple([p for p in (_OVERRIDE_ENV, _DEFAULT_ENV, ".env") if p])


class Settings(BaseSettings):
    """
    Loads configuration from:
      1) OS environment variables (highest priority)
      2) The first existing file among PHEONA_ENV_FILE, backend-api/.env, or ./\.env

    Notes:
    - You do NOT need a "DB name" for Redis Cloud; use host/port/password (TLS) and logical DB index `/0`.
    - CORS is permissive for localhost; use FRONTEND_ALLOWED_ORIGIN_REGEX on deploy (e.g. ^https://.*\.streamlit\.app$).
    """
    # Tell pydantic-settings to read our dotenv files automatically (and ignore unknown keys)
    model_config = SettingsConfigDict(
        env_file=_ENV_FILES,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- General ---
    ENV: str = "development"

    # --- CORS ---
    # Local dev defaults for Streamlit at :8501
    FRONTEND_ALLOWED_ORIGINS: str = "http://localhost:8501,http://127.0.0.1:8501"
    # When deploying Streamlit Cloud, set: ^https://.*\.streamlit\.app$
    FRONTEND_ALLOWED_ORIGIN_REGEX: Optional[str] = None

    # --- API key for Streamlit → Backend ---
    BACKEND_API_KEY: str

    # --- Redis Cloud ---
    # Option A: full rediss URL (TLS), e.g. rediss://default:<PASS>@<HOST>:<PORT>/0
    REDIS_URL: Optional[str] = None
    # Option B: Host/Port/Password from Redis Cloud UI (username is usually "default")
    REDIS_HOST: Optional[str] = None
    REDIS_PORT: Optional[int] = None
    REDIS_USERNAME: str = "default"
    REDIS_PASSWORD: Optional[str] = None

    # --- Vapi ---
    VAPI_API_KEY: str
    VAPI_BASE_URL: str = "https://api.vapi.ai"
    VAPI_DEFAULT_AREACODE: Optional[str] = None  # e.g., "415" (US only; free numbers)

    # --- Groq ---
    GROQ_API_KEY: str
    # Must be a model that supports Structured Outputs (json_schema)
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # --- Paths (repo-aware defaults) ---
    PHEONA_REPO_ROOT: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    PHEONA_TEMPLATES_DIR: str = os.path.join(PHEONA_REPO_ROOT, "templates")
    PHEONA_PROMPTS_DIR: str = os.path.join(PHEONA_REPO_ROOT, "prompts")

    @property
    def allowed_origins(self) -> List[str]:
        s = (self.FRONTEND_ALLOWED_ORIGINS or "").strip()
        return [o.strip() for o in s.split(",")] if s else []

    def resolved_redis_url(self) -> str:
        """
        Prefer REDIS_URL if provided; otherwise compose a TLS URL from host/port/password.
        Redis Cloud doesn't use a 'DB name' in the URL—use logical DB index '/0'.
        """
        if self.REDIS_URL:
            return self.REDIS_URL
        if self.REDIS_HOST and self.REDIS_PORT and self.REDIS_PASSWORD:
            return f"rediss://{self.REDIS_USERNAME}:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/0"
        raise ValueError("Configure REDIS_URL or REDIS_HOST/REDIS_PORT/REDIS_PASSWORD")


settings = Settings()
