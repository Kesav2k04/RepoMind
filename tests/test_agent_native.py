"""Tests for RepoMind's agent-native CLI and MCP delivery surfaces."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import main
import master
import pytest
import repomind_cli
import repomind_mcp
from preflight import run_preflight
from repository import RepositorySnapshot


async def _quiet_progress(
    phase: str,
    message: str,
    role: str | None = None,
    **details: object,
) -> None:
    del phase, message, role, details


def test_preflight_rejects_non_github_urls_before_any_clone() -> None:
    with pytest.raises(ValueError, match="github.com"):
        asyncio.run(run_preflight("https://example.com/acme/demo"))


def test_cli_writes_both_verified_artifacts_without_starting_a_server(
    monkeypatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    repository_snapshot: RepositorySnapshot,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = asyncio.run(
        master.orchestrate_analysis(
            repository_snapshot,
            _quiet_progress,
            "Replace the dynamic parser without changing the public API.",
        )
    )

    async def fake_preflight(*_: object) -> object:
        return result

    monkeypatch.setattr(repomind_cli, "run_preflight", fake_preflight)
    agents_path = tmp_path / "AGENTS.md"
    map_path = tmp_path / "repo-map.md"

    exit_code = repomind_cli.main(
        [
            "preflight",
            "https://github.com/acme/demo.git",
            "--task",
            "Replace the dynamic parser without changing the public API.",
            "--output",
            str(agents_path),
            "--map-output",
            str(map_path),
            "--json",
        ]
    )

    summary = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert agents_path.read_text(encoding="utf-8").startswith("# AGENTS.md")
    assert "## Current Task Brief" in agents_path.read_text(encoding="utf-8")
    assert "risk-annotated repository map" in map_path.read_text(encoding="utf-8")
    assert summary["mode"] == "evidence_fallback"
    assert summary["task_brief"]["review_paths"]


def test_mcp_preflight_and_artifact_lookup_share_the_same_verified_result(
    monkeypatch,
    repository_snapshot: RepositorySnapshot,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = asyncio.run(master.orchestrate_analysis(repository_snapshot, _quiet_progress, "Review parser safety."))

    async def fake_preflight(*_: object) -> object:
        return result

    repomind_mcp._artifacts.clear()
    monkeypatch.setattr(repomind_mcp, "run_preflight", fake_preflight)

    payload = asyncio.run(
        repomind_mcp.repomind_preflight(
            "https://github.com/acme/demo.git",
            "Review parser safety.",
        )
    )
    artifact = asyncio.run(repomind_mcp.repomind_get_artifact(payload["job_id"], "AGENTS.md"))

    assert payload["ok"] is True
    assert payload["execution"]["mode"] == "evidence_fallback"
    assert payload["firewall"]["artifacts_validated"] is True
    assert artifact == {
        "ok": True,
        "job_id": payload["job_id"],
        "name": "AGENTS.md",
        "content": result.agents_md,
    }


def test_dashboard_uses_the_shared_preflight_entry_point(
    monkeypatch,
    repository_snapshot: RepositorySnapshot,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = asyncio.run(master.orchestrate_analysis(repository_snapshot, _quiet_progress))
    calls: list[tuple[str, str | None]] = []

    async def fake_preflight(
        repo_url: str,
        task_description: str | None,
        progress: object,
    ) -> object:
        assert callable(progress)
        calls.append((repo_url, task_description))
        return result

    monkeypatch.setitem(sys.modules, "preflight", SimpleNamespace(run_preflight=fake_preflight))
    job = main.Job(
        job_id="job_shared_preflight",
        repository_url="https://github.com/acme/demo.git",
        task_description="Review parser safety.",
    )

    asyncio.run(main._run_analysis(job))

    assert calls == [("https://github.com/acme/demo.git", "Review parser safety.")]
    assert job.status == "completed"
    assert job.result is result
