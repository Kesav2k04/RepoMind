"""Shared local-only fixtures for RepoMind backend tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from repository import RepositorySnapshot, snapshot_repository


@pytest.fixture
def repository_snapshot(tmp_path: Path) -> RepositorySnapshot:
    """Create a small, representative checkout without GitHub or Git history."""
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "dist").mkdir()

    (tmp_path / "README.md").write_text("# Demo repository\n", encoding="utf-8")
    (tmp_path / "package.json").write_text(
        '{"dependencies":{"react":"1.0"},"scripts":{"test":"vitest run"}}',
        encoding="utf-8",
    )
    (tmp_path / "package-lock.json").write_text("{}", encoding="utf-8")
    (tmp_path / "src" / "app.py").write_text(
        "import os\n\n"
        "def run(payload: str):\n"
        "    # TODO replace this parser\n"
        "    return eval(payload)\n\n"
        "token = os.getenv('DEMO_TOKEN')\n",
        encoding="utf-8",
    )
    (tmp_path / "tests" / "test_app.py").write_text(
        "from src.app import run\n\n"
        "def test_run():\n"
        "    assert run('1 + 1') == 2\n",
        encoding="utf-8",
    )
    (tmp_path / "node_modules" / "ignored.js").write_text("ignored", encoding="utf-8")
    (tmp_path / "dist" / "ignored.js").write_text("ignored", encoding="utf-8")
    return snapshot_repository(tmp_path, "https://github.com/acme/demo.git")
