"""Tests for public-repository input validation and bounded evidence extraction."""

from __future__ import annotations

from pathlib import Path

import pytest

from repository import snapshot_repository, validate_github_url


@pytest.mark.parametrize(
    ("repo_url", "canonical_url"),
    [
        ("https://github.com/openai/openai-python", "https://github.com/openai/openai-python.git"),
        ("https://www.github.com/acme/demo.git", "https://github.com/acme/demo.git"),
        ("https://github.com/Owner-1/repo.name", "https://github.com/Owner-1/repo.name.git"),
    ],
)
def test_validate_github_url_canonicalizes_supported_public_urls(repo_url: str, canonical_url: str) -> None:
    assert validate_github_url(repo_url) == canonical_url


@pytest.mark.parametrize(
    "repo_url",
    [
        "",
        " https://github.com/acme/demo",
        "http://github.com/acme/demo",
        "https://example.com/acme/demo",
        "https://github.com/acme/demo/issues",
        "https://user:pass@github.com/acme/demo",
        "https://github.com:443/acme/demo",
        "https://github.com/acme/demo?tab=readme",
        "https://github.com/acme/%64emo",
    ],
)
def test_validate_github_url_rejects_non_cloneable_or_unsafe_urls(repo_url: str) -> None:
    with pytest.raises(ValueError):
        validate_github_url(repo_url)


def test_snapshot_excludes_generated_and_dependency_directories(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "build").mkdir()
    (tmp_path / ".git").mkdir()
    (tmp_path / "package.json").write_text('{"scripts":{"test":"vitest run"}}', encoding="utf-8")
    (tmp_path / "src" / "app.py").write_text("print('ok')\n", encoding="utf-8")
    (tmp_path / "tests" / "test_app.py").write_text("def test_ok(): pass\n", encoding="utf-8")
    (tmp_path / "node_modules" / "ignored.js").write_text("ignored", encoding="utf-8")
    (tmp_path / "build" / "ignored.py").write_text("ignored", encoding="utf-8")
    (tmp_path / ".git" / "config").write_text("[core]\n", encoding="utf-8")

    snapshot = snapshot_repository(tmp_path, "https://github.com/acme/snapshot-demo.git")

    assert snapshot.name == "snapshot-demo"
    assert snapshot.primary_language == "Python"
    assert "src/app.py" in snapshot.files
    assert "tests/test_app.py" in snapshot.files
    assert all(not path.startswith(("node_modules/", "build/", ".git/")) for path in snapshot.files)
    assert snapshot.test_commands == ["npm test"]
    assert "package.json" in snapshot.important_file_contents
