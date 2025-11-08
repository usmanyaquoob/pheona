# backend-api/app/config.py
import os
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_DEFAULT_ENV = os.path.join(_BACKEND_DIR, ".env")
_OVERRIDE_ENV = os.getenv("PHEONA_ENV_FILE")

_ENV_FILES = tuple([p for p in (_OVERRIDE_ENV, _DEFAULT_ENV, ".env") if p])

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILES,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- General ---
    ENV: str = "development"

    # --- CORS ---
    FRONTEND_ALLOWED_ORIGINS: str = "http://localhost:8501,http://127.0.0.1:8501"
    FRONTEND_ALLOWED_ORIGIN_REGEX: Optional[str] = None

    # --- API key (frontend -> backend) ---
    BACKEND_API_KEY: str

    # --- Redis Cloud ---
    # Option A: full URL, e.g. redis://user:pass@host:port/0  or  rediss://...
    REDIS_URL: Optional[str] = None
    # Option B: discrete host/port creds
    REDIS_HOST: Optional[str] = None
    REDIS_PORT: Optional[int] = None
    REDIS_USERNAME: str = "default"
    REDIS_PASSWORD: Optional[str] = None
    # If your Redis Cloud endpoint requires TLS, set REDIS_TLS=1
    REDIS_TLS: Optional[bool] = None

    # --- Vapi ---
    VAPI_API_KEY: str
    VAPI_BASE_URL: str = "https://api.vapi.ai"
    VAPI_DEFAULT_AREACODE: Optional[str] = None

    # --- Groq (prompt specialization only) ---
    GROQ_API_KEY: str
    GROQ_MODEL: str = "openai/gpt-oss-120b"  # supports json_schema outputs

    # --- Paths ---
    PHEONA_REPO_ROOT: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    PHEONA_TEMPLATES_DIR: str = os.path.join(PHEONA_REPO_ROOT, "templates")
    PHEONA_PROMPTS_DIR: str = os.path.join(PHEONA_REPO_ROOT, "prompts")

    @property
    def allowed_origins(self) -> List[str]:
        s = (self.FRONTEND_ALLOWED_ORIGINS or "").strip()
        return [o.strip() for o in s.split(",")] if s else []

settings = Settings()
