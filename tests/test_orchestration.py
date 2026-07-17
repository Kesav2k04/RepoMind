"""Tests for deterministic workers, artifacts, and mocked hosted reconciliation."""

from __future__ import annotations

import asyncio
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import master
import pytest
from repository import RepositorySnapshot
from schemas import AgentReport, EvidenceLocation, Finding
from settings import Settings
from workers.history import analyze as analyze_history


async def _collect_progress(phase: str, message: str, role: str | None = None) -> None:
    _collect_progress.events.append((phase, message, role))


_collect_progress.events: list[tuple[str, str, str | None]] = []


async def _collect_rich_progress(
    phase: str, message: str, role: str | None = None, **details: object
) -> None:
    _collect_rich_progress.events.append((phase, message, role, details))


_collect_rich_progress.events: list[tuple[str, str, str | None, dict[str, object]]] = []


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
    assert "## Things Not to Touch" in result.agents_md
    assert "## Verification Checklist" in result.agents_md
    assert "[HIGH] `src/app.py`" in result.repo_map.markdown
    dynamic_finding = next(finding for finding in risk_report.findings if finding.id == "risk-dynamic-code-execution")
    assert dynamic_finding.confidence == 0.96
    assert dynamic_finding.evidence[0].path == "src/app.py"
    assert dynamic_finding.evidence[0].line_start == 5
    assert result.validation.artifacts_validated is True
    assert result.validation.validated_findings == result.metrics.findings_published
    assert result.analysis_scope.status == "complete"


def test_orchestration_streams_concrete_specialist_actions(
    monkeypatch, repository_snapshot: RepositorySnapshot
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    _collect_rich_progress.events.clear()

    result = asyncio.run(master.orchestrate_analysis(repository_snapshot, _collect_rich_progress))

    progress_events = [event for event in _collect_rich_progress.events if event[0] == "agent_progress"]
    assert {role for _, _, role, _ in progress_events} == {
        "architecture",
        "risk",
        "testing",
        "history",
    }
    assert all(event[3].get("action") for event in progress_events)
    assert all(event[3].get("current") for event in progress_events)
    assert result.metrics.files_analyzed == repository_snapshot.file_count
    assert result.metrics.findings_published == sum(len(report.findings) for report in result.reports)
    assert result.reconciliation.accepted_count >= 1
    assert all(
        finding.evidence and 0 <= finding.confidence <= 1
        for report in result.reports
        for finding in report.findings
    )


def test_history_worker_tolerates_null_history_metadata(repository_snapshot: RepositorySnapshot) -> None:
    nullable_history = replace(
        repository_snapshot,
        commit_messages=[None, "  update auth  "],  # type: ignore[list-item]
        contributors=[None, "  Ada  "],  # type: ignore[list-item]
    )

    report = analyze_history(nullable_history)

    assert report.summary.startswith("Observed 1 recent commit subject")


def test_root_output_tolerates_missing_optional_model_text() -> None:
    response = SimpleNamespace(
        output=[
            SimpleNamespace(
                type="message",
                agent=SimpleNamespace(agent_name="/root"),
                phase="final_answer",
                content=[SimpleNamespace(type="output_text", text=None)],
            )
        ]
    )

    with pytest.raises(ValueError, match="No final root-agent output"):
        master._root_final_text(response)


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
                                    '{"priority_finding_ids":'
                                    '["risk-dynamic-code-execution"]}'
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
    assert "prioritized 1 validated deterministic finding" in (result.orchestration.note or "")
    assert result.agents_md.startswith("# AGENTS.md\n")
    assert "[HIGH] `src/app.py`" in result.repo_map.markdown
    assert len(calls) == 1
    request = calls[0]
    assert request["model"] == "gpt-5.6-unit-test"
    assert request["max_output_tokens"] == master.MAX_NATIVE_OUTPUT_TOKENS
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


def test_native_reconciliation_timeout_returns_fast_evidence_fallback(
    monkeypatch, repository_snapshot: RepositorySnapshot
) -> None:
    class SlowResponses:
        async def create(self, **_: object) -> object:
            await asyncio.sleep(0.05)
            return SimpleNamespace(output=[])

    class SlowClient:
        def __init__(self) -> None:
            self.beta = SimpleNamespace(responses=SlowResponses())

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(
        master,
        "settings",
        SimpleNamespace(openai_model="gpt-5.6-unit-test", gpt_timeout_seconds=0.001),
    )
    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(AsyncOpenAI=SlowClient))

    result = asyncio.run(master.orchestrate_analysis(repository_snapshot, _collect_progress))

    assert result.orchestration.mode == "evidence_fallback"
    assert "exceeded the demo timeout" in (result.orchestration.note or "")
    assert result.agents_md.startswith("# AGENTS.md\n")


def test_native_priority_payload_rejects_unknown_or_duplicate_evidence(repository_snapshot: RepositorySnapshot) -> None:
    reports = asyncio.run(master.run_specialists(repository_snapshot, _collect_progress))

    with pytest.raises(ValueError, match="unsupported or duplicate"):
        master._validated_priority_finding_ids(
            {"priority_finding_ids": ["not-a-real-id", "not-a-real-id"]}, reports
        )


def test_unsupported_evidence_paths_are_withheld_before_artifact_generation(
    repository_snapshot: RepositorySnapshot,
) -> None:
    report = AgentReport(
        role="risk",
        label="Risk",
        summary="Test report",
        confidence=0.9,
        findings=[
            Finding(
                id="unsupported-path",
                category="risk",
                title="Untrusted path",
                detail="This must never be shown.",
                severity="high",
                files=["outside-repository.py"],
                confidence=0.9,
                evidence=[
                    EvidenceLocation(
                        path="outside-repository.py",
                        line_start=1,
                        line_end=1,
                        excerpt="unsafe",
                        reason="Not present in the bounded inventory.",
                    )
                ],
            )
        ],
    )

    sanitized, rejected = master._evidence_backed_reports(repository_snapshot, [report])

    assert rejected == 1
    assert sanitized[0].findings == []
