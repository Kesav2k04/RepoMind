"""Runtime configuration for RepoMind.

Configuration is deliberately small for the hackathon MVP. Environment variables
keep model choice and repository-cache location out of source control.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    pass
else:
    load_dotenv()


@dataclass(frozen=True)
class Settings:
    openai_model: str
    cache_dir: Path
    clone_timeout_seconds: int

    @classmethod
    def from_environment(cls) -> "Settings":
        return cls(
            openai_model=os.getenv("OPENAI_MODEL", "gpt-5.6-sol"),
            cache_dir=Path(os.getenv("REPOMIND_CACHE_DIR", "D:/dev-cache/repomind/repos")),
            clone_timeout_seconds=int(os.getenv("REPOMIND_CLONE_TIMEOUT_SECONDS", "120")),
        )


settings = Settings.from_environment()
