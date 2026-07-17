"""Tests for deterministic workers, artifacts, and mocked hosted reconciliation."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

import master
from repository import RepositorySnapshot
from settings import Settings


async def _collect_progress(phase: str, message: str, role: str | None = None) -> None:
    _collect_progress.events.append((phase, message, role))


_collect_progress.events: list[tuple[str, str, str | None]] = []


def test_orchestrate_analysis_uses_four_worker_evidence_fallback(
    monkeypatch, repository_snapshot: RepositorySnapshot
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    _collect_progress.events.clear()

    result = asyncio.run(master.orchestrate_analysis(repository_snapshot, _collect_progress))

    assert result.orchestration.mode == "evidence_fallback"
    assert result.orchestration.completed_roles == ["architecture", "risk", "testing", "history"]
    assert [report.role for report in result.reports] == ["architecture", "risk", "testing", "history"]
    assert {role for phase, _, role in _collect_progress.events if phase == "agent_started"} == {
        "architecture",
        "risk",
        "testing",
        "history",
    }
    assert {role for phase, _, role in _collect_progress.events if phase == "agent_completed"} == {
        "architecture",
        "risk",
        "testing",
        "history",
    }

    risk_report = next(report for report in result.reports if report.role == "risk")
    assert any(finding.id == "risk-dynamic-code-execution" for finding in risk_report.findings)
    assert "# AGENTS.md" in result.agents_md
    assert "demo" in result.agents_md
    assert "`npm test`" in result.agents_md
    assert "[HIGH] `src/app.py`" in result.repo_map.markdown


def test_native_reconciliation_uses_configured_model_and_validates_root_output(
    monkeypatch, tmp_path: Path, repository_snapshot: RepositorySnapshot
) -> None:
    calls: list[dict[str, object]] = []

    class FakeResponses:
        async def create(self, **kwargs: object) -> object:
            calls.append(kwargs)
            return SimpleNamespace(
                output=[
                    SimpleNamespace(
                        type="message",
                        agent=SimpleNamespace(agent_name="/root"),
                        phase="final_answer",
                        content=[
                            SimpleNamespace(
                                type="output_text",
                                text=(
                                    '{"summary":"Reconciled evidence",'
                                    '"agents_md":"# Generated agent guide",'
                                    '"repo_map_markdown":"# Generated map"}'
                                ),
                            )
                        ],
                    )
                ]
            )

    class FakeClient:
        def __init__(self) -> None:
            self.beta = SimpleNamespace(responses=FakeResponses())

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(
        master,
        "settings",
        Settings(
            openai_model="gpt-5.6-unit-test",
            cache_dir=tmp_path / "cache",
            clone_timeout_seconds=3,
        ),
    )
    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(AsyncOpenAI=FakeClient))
    _collect_progress.events.clear()

    result = asyncio.run(master.orchestrate_analysis(repository_snapshot, _collect_progress))

    assert result.orchestration.mode == "native_multi_agent"
    assert result.orchestration.model == "gpt-5.6-unit-test"
    assert result.agents_md == "# Generated agent guide\n"
    assert result.repo_map.markdown == "# Generated map\n"
    assert result.repo_map.overview == "Reconciled evidence"
    assert len(calls) == 1
    request = calls[0]
    assert request["model"] == "gpt-5.6-unit-test"
    assert request["multi_agent"] == {"enabled": True, "max_concurrent_subagents": 4}
    assert request["betas"] == ["responses_multi_agent=v1"]
    developer_prompt = request["input"][0]["content"]  # type: ignore[index]
    for agent_name in (
        "architecture_mapper",
        "risk_auditor",
        "test_coverage_analyst",
        "history_archaeologist",
    ):
        assert agent_name in developer_prompt
    assert any(phase == "reconciled" for phase, _, _ in _collect_progress.events)
