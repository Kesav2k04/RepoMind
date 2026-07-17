"""Runtime configuration for RepoMind.

Configuration is deliberately small for the hackathon MVP. Environment variables
keep model choice and repository-cache location out of source control.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import tempfile

try:
    from dotenv import load_dotenv
except ImportError:
    pass
else:
    load_dotenv()


LOCAL_DEV_CORS_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)


def _d_drive_is_available() -> bool:
    """Keep the established D: cache only on hosts where that drive exists."""
    return Path("D:/").is_dir()


def _default_cache_dir() -> Path:
    """Choose the local D: cache when available, otherwise use a portable temp path."""
    if _d_drive_is_available():
        d_drive = Path("D:/")
        return d_drive / "dev-cache" / "repomind" / "repos"
    return Path(tempfile.gettempdir()) / "repomind" / "repos"


def _positive_int(name: str, default: int, *, minimum: int = 1) -> int:
    """Read an integer setting without making a malformed environment fatal."""
    raw_value = os.getenv(name, "").strip()
    try:
        value = int(raw_value) if raw_value else default
    except ValueError:
        return default
    return max(minimum, value)


def _cors_origins() -> tuple[str, ...]:
    """Combine explicitly configured browser origins with local development origins."""
    configured = os.getenv("REPOMIND_CORS_ORIGINS", "")
    origins = [origin.strip().rstrip("/") for origin in configured.split(",") if origin.strip()]
    return tuple(dict.fromkeys((*LOCAL_DEV_CORS_ORIGINS, *origins)))


@dataclass(frozen=True)
class Settings:
    openai_model: str
    cache_dir: Path
    clone_timeout_seconds: int
    gpt_timeout_seconds: int = 45
    max_concurrent_jobs: int = 2
    cors_origins: tuple[str, ...] = LOCAL_DEV_CORS_ORIGINS

    @classmethod
    def from_environment(cls) -> "Settings":
        configured_cache_dir = os.getenv("REPOMIND_CACHE_DIR", "").strip()
        return cls(
            openai_model=os.getenv("OPENAI_MODEL", "").strip() or "gpt-5.6-sol",
            cache_dir=Path(configured_cache_dir).expanduser() if configured_cache_dir else _default_cache_dir(),
            clone_timeout_seconds=_positive_int("REPOMIND_CLONE_TIMEOUT_SECONDS", 120),
            gpt_timeout_seconds=_positive_int("REPOMIND_GPT_TIMEOUT_SECONDS", 45),
            max_concurrent_jobs=_positive_int("REPOMIND_MAX_CONCURRENT_JOBS", 2),
            cors_origins=_cors_origins(),
        )


settings = Settings.from_environment()
