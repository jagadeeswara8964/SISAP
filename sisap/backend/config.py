"""Central application configuration.

All secrets and tunables are read from environment variables (or a local `.env`
file). Nothing sensitive is ever exposed to the frontend: the API never returns
raw environment values.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent


def _load_dotenv() -> None:
    """Minimal .env loader (avoids a hard dependency on python-dotenv)."""
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()


def _bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class Settings:
    """Runtime settings for SISAP.

    Attributes:
        demo_mode: When true the engine runs fully offline: curated standards,
            local embeddings, rule-based extraction and deterministic ranking.
        embedding_model: Sentence-Transformers model id used for semantic search.
        embedding_backend: "auto" (Sentence-Transformers, falling back to TF-IDF
            when unavailable), "sentence-transformers" or "tfidf".
    """

    app_name: str = "SISAP"
    app_version: str = "1.0.0"
    environment: str = field(default_factory=lambda: os.getenv("SISAP_ENV", "development"))

    # --- paths -------------------------------------------------------------
    project_root: Path = PROJECT_ROOT
    data_dir: Path = field(default_factory=lambda: Path(os.getenv("SISAP_DATA_DIR", PROJECT_ROOT / "data")))
    upload_dir: Path = field(default_factory=lambda: Path(os.getenv("SISAP_UPLOAD_DIR", BASE_DIR / "uploads")))
    reports_dir: Path = field(default_factory=lambda: Path(os.getenv("SISAP_REPORTS_DIR", PROJECT_ROOT / "reports")))
    index_dir: Path = field(default_factory=lambda: Path(os.getenv("SISAP_INDEX_DIR", PROJECT_ROOT / "data" / "embeddings")))

    # --- modes -------------------------------------------------------------
    demo_mode: bool = field(default_factory=lambda: _bool("DEMO_MODE", True))
    embedding_model: str = field(default_factory=lambda: os.getenv("SISAP_EMBEDDING_MODEL", "all-MiniLM-L6-v2"))
    embedding_backend: str = field(default_factory=lambda: os.getenv("SISAP_EMBEDDING_BACKEND", "auto").lower())

    # --- security / limits -------------------------------------------------
    max_upload_bytes: int = field(default_factory=lambda: _int("SISAP_MAX_UPLOAD_MB", 25) * 1024 * 1024)
    allowed_extensions: tuple[str, ...] = ("pdf",)
    cors_origins: tuple[str, ...] = field(
        default_factory=lambda: tuple(
            origin.strip() for origin in os.getenv("SISAP_CORS_ORIGINS", "*").split(",") if origin.strip()
        )
    )

    # --- optional LLM abstraction -----------------------------------------
    llm_provider: str = field(default_factory=lambda: os.getenv("SISAP_LLM_PROVIDER", "auto").lower())
    llm_api_key: str | None = field(default_factory=lambda: os.getenv("SISAP_LLM_API_KEY") or os.getenv("LLM_API_KEY"))
    llm_model: str = field(default_factory=lambda: os.getenv("SISAP_LLM_MODEL", "claude-sonnet-4-5"))
    llm_base_url: str | None = field(default_factory=lambda: os.getenv("SISAP_LLM_BASE_URL"))

    # --- dataset -----------------------------------------------------------
    standards_file: str = "standards.json"

    def ensure_directories(self) -> None:
        for directory in (self.data_dir, self.upload_dir, self.reports_dir, self.index_dir):
            directory.mkdir(parents=True, exist_ok=True)

    @property
    def standards_path(self) -> Path:
        return self.data_dir / self.standards_file

    @property
    def database_path(self) -> Path:
        return self.data_dir / "sisap.db"

    def public_dict(self) -> dict:
        """Non-sensitive settings view (safe to return through the API)."""
        return {
            "app_name": self.app_name,
            "version": self.app_version,
            "environment": self.environment,
            "demo_mode": self.demo_mode,
            "embedding_model": self.embedding_model,
            "embedding_backend": self.embedding_backend,
            "max_upload_mb": round(self.max_upload_bytes / (1024 * 1024), 1),
            "llm_configured": bool(self.llm_api_key),
        }


settings = Settings()
settings.ensure_directories()
