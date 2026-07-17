"""Tests for public-repository input validation and bounded evidence extraction."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

import repository
import settings as settings_module
from repository import evidence_location, snapshot_repository, validate_github_url
from settings import Settings


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


def test_snapshot_reports_bounded_live_evidence_progress(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("print('ok')\n", encoding="utf-8")
    events: list[tuple[str, int | None, int | None, dict[str, int]]] = []

    snapshot = snapshot_repository(
        tmp_path,
        "https://github.com/acme/progress-demo.git",
        lambda action, current, total, metrics: events.append((action, current, total, metrics)),
    )

    assert snapshot.metrics()["files_analyzed"] == 1
    assert {event[0] for event in events} >= {
        "inventorying_files",
        "sampling_evidence",
        "evidence_ready",
    }
    ready = next(event for event in events if event[0] == "evidence_ready")
    assert ready[1:3] == (1, 1)
    assert ready[3]["sampled_files"] == 1


def test_snapshot_discloses_inventory_truncation_in_summary_and_progress(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(repository, "MAX_DISCOVERED_FILES", 4)
    monkeypatch.setattr(repository, "MAX_FILES", 2)
    (tmp_path / "src").mkdir()
    for index in range(5):
        (tmp_path / "src" / f"module_{index}.py").write_text("print('ok')\n", encoding="utf-8")
    events: list[tuple[str, int | None, int | None, dict[str, int]]] = []

    snapshot = snapshot_repository(
        tmp_path,
        "https://github.com/acme/bounded-demo.git",
        lambda action, current, total, metrics: events.append((action, current, total, metrics)),
    )

    assert snapshot.discovered_file_count == 4
    assert snapshot.selected_file_count == 2
    assert snapshot.inventory_limit_reached is True
    assert snapshot.selection_limit_reached is True
    assert snapshot.partial_analysis is True
    assert snapshot.prompt_summary()["analysis_scope"] == {
        "discovered_files": 4,
        "selected_files": 2,
        "discovered_count_is_lower_bound": True,
        "inventory_limit_reached": True,
        "selection_limit_reached": True,
        "source_evidence_partial": True,
        "evidence_chars_collected": 26,
        "evidence_char_limit_reached": False,
        "oversized_files_skipped": 0,
        "unreadable_files_skipped": 0,
        "files_with_truncated_excerpts": 0,
        "files_omitted_by_char_limit": 0,
    }
    ready = next(event for event in events if event[0] == "evidence_ready")
    assert ready[3]["files_discovered"] == 4
    assert ready[3]["files_selected"] == 2
    assert ready[3]["partial_analysis"] == 1


def test_snapshot_discloses_content_budget_truncation(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(repository, "MAX_EVIDENCE_CHARS", 5)
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("abcdefghij", encoding="utf-8")

    snapshot = snapshot_repository(tmp_path, "https://github.com/acme/content-budget-demo.git")

    assert snapshot.sampled_contents == {"src/app.py": "abcde"}
    assert snapshot.evidence_chars_collected == 5
    assert snapshot.evidence_char_limit_reached is True
    assert snapshot.files_with_truncated_excerpts == 1
    assert snapshot.partial_analysis is True
    assert snapshot.prompt_summary()["evidence_limits"]["max_total_content_chars"] == 5


def test_portable_cache_root_accepts_any_writable_configured_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cache_dir = tmp_path / "portable-cache" / "repos"
    monkeypatch.setattr(
        repository,
        "settings",
        Settings(openai_model="test", cache_dir=cache_dir, clone_timeout_seconds=1),
    )

    assert repository._cache_root() == cache_dir.resolve()
    assert cache_dir.is_dir()


def test_cache_root_reports_an_actionable_error_for_a_file_destination(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cache_file = tmp_path / "not-a-directory"
    cache_file.write_text("not a cache", encoding="utf-8")
    monkeypatch.setattr(
        repository,
        "settings",
        Settings(openai_model="test", cache_dir=cache_file, clone_timeout_seconds=1),
    )

    with pytest.raises(RuntimeError, match="REPOMIND_CACHE_DIR"):
        repository._cache_root()


def test_settings_falls_back_to_a_portable_temp_cache_without_d_drive(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("REPOMIND_CACHE_DIR", raising=False)
    monkeypatch.setattr(settings_module, "_d_drive_is_available", lambda: False)
    monkeypatch.setattr(settings_module.tempfile, "gettempdir", lambda: str(tmp_path / "temporary"))

    configured = settings_module.Settings.from_environment()

    assert configured.cache_dir == tmp_path / "temporary" / "repomind" / "repos"


def test_settings_parse_optional_runtime_controls_safely(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    cache_dir = tmp_path / "repomind-cache"
    monkeypatch.setenv("REPOMIND_CACHE_DIR", str(cache_dir))
    monkeypatch.setenv("REPOMIND_CLONE_TIMEOUT_SECONDS", "not-an-int")
    monkeypatch.setenv("REPOMIND_GPT_TIMEOUT_SECONDS", "0")
    monkeypatch.setenv("REPOMIND_MAX_CONCURRENT_JOBS", "-2")
    monkeypatch.setenv(
        "REPOMIND_CORS_ORIGINS",
        " https://demo.example/ , http://localhost:5173/ , https://demo.example ",
    )

    configured = settings_module.Settings.from_environment()

    assert configured.cache_dir == cache_dir
    assert configured.clone_timeout_seconds == 120
    assert configured.gpt_timeout_seconds == 1
    assert configured.max_concurrent_jobs == 1
    assert configured.cors_origins == (
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://demo.example",
    )


def test_evidence_location_reports_exact_line_and_bounded_excerpt() -> None:
    evidence = evidence_location(
        "src/example.py",
        "first line\nresult = eval(payload)\nlast line\n",
        "eval(payload)",
        "Matched dynamic execution.",
    )

    assert evidence.path == "src/example.py"
    assert evidence.line_start == evidence.line_end == 2
    assert evidence.excerpt == "result = eval(payload)"
    assert evidence.reason == "Matched dynamic execution."


def test_git_history_capture_decodes_repository_text_as_utf8(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: list[dict[str, object]] = []

    def fake_run(*_: object, **kwargs: object) -> SimpleNamespace:
        calls.append(kwargs)
        return SimpleNamespace(returncode=0, stdout="café\n", stderr="")

    monkeypatch.setattr(repository.subprocess, "run", fake_run)

    messages, _, _, _, _, _ = repository._git_evidence(tmp_path)

    assert messages == ["café"]
    assert calls
    assert all(call["encoding"] == "utf-8" and call["errors"] == "replace" for call in calls)
