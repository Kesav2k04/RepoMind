"""Tests for deterministic workers, artifacts, and mocked hosted reconciliation."""

from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import master
import native_agents
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


def test_structured_root_output_tolerates_missing_optional_model_text() -> None:
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

    with pytest.raises(ValueError, match="returned no structured reconciliation"):
        master._parse_response_json(response)


def test_native_specialists_use_read_only_tools_and_firewall_verified_claims(
    monkeypatch, tmp_path: Path, repository_snapshot: RepositorySnapshot
) -> None:
    calls: list[dict[str, object]] = []

    class FakeResponses:
        async def create(self, **kwargs: object) -> object:
            calls.append(kwargs)
            metadata = kwargs.get("metadata")
            if metadata == {"repomind_stage": "root_reconciliation"}:
                packet = kwargs["input"][0]["content"]  # type: ignore[index]
                inventory = json.loads(packet)["verified_finding_inventory"]
                return SimpleNamespace(
                    output=[],
                    output_text=json.dumps(
                        {
                            "priority_finding_ids": [inventory[0]["id"]],
                            "merged_finding_ids": [],
                            "deferred_finding_ids": [],
                        }
                    ),
                )
            input_items = kwargs["input"]  # type: ignore[index]
            has_tool_output = any(
                isinstance(item, dict) and item.get("type") == "function_call_output"
                for item in input_items
            )
            if not has_tool_output:
                return SimpleNamespace(
                    output=[
                        SimpleNamespace(
                            type="function_call",
                            name="read_file",
                            arguments='{"path":"src/app.py","line_start":1,"line_end":7}',
                            call_id="read_source",
                        )
                    ],
                    output_text="",
                )
            return SimpleNamespace(
                output=[],
                output_text=(
                    '{"summary":"Source-reviewed risk signal.","findings":['
                    '{"title":"Dynamic evaluation is reachable","detail":"The handler evaluates payload text.",'
                    '"recommendation":"Replace dynamic evaluation with an explicit parser.",'
                    '"path":"src/app.py","line_start":5,"line_end":5,'
                    '"quoted_evidence":"return eval(payload)","severity":"high","confidence":0.99}]}'
                ),
            )

    class FakeClient:
        def __init__(self) -> None:
            self.responses = FakeResponses()

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

    result = asyncio.run(
        master.orchestrate_analysis(
            repository_snapshot,
            _collect_progress,
            "Replace the dynamic parser without changing the public API.",
        )
    )

    assert result.orchestration.mode == "native_multi_agent"
    assert result.orchestration.model == "gpt-5.6-unit-test"
    assert len(result.orchestration.priority_finding_ids) == 1
    assert "parallel GPT-5.6 source specialists" in (result.orchestration.note or "")
    assert result.agents_md.startswith("# AGENTS.md\n")
    assert "## Current Task Brief" in result.agents_md
    assert "Replace the dynamic parser" in result.agents_md
    assert "[HIGH] `src/app.py`" in result.repo_map.markdown
    assert result.metrics.model_tool_calls == 4
    assert result.metrics.model_workers_completed == 4
    assert result.validation.proposed_claims == 4
    assert result.validation.validated_findings == 4
    assert result.validation.rejected_claims == 0
    assert len(calls) == 9
    specialist_requests = [call for call in calls if call["metadata"] == {"repomind_stage": "specialist"}]
    assert len(specialist_requests) == 8
    assert all(request["model"] == "gpt-5.6-unit-test" for request in calls)
    assert all("tools" in request for request in specialist_requests)
    assert all("beta" not in request and "multi_agent" not in request for request in calls)
    assert {role for phase, _, role in _collect_progress.events if phase == "agent_tool_call"} == {
        "architecture",
        "risk",
        "testing",
        "history",
    }
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
            self.responses = SlowResponses()

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(
        master,
        "settings",
        SimpleNamespace(openai_model="gpt-5.6-unit-test", gpt_timeout_seconds=0.001),
    )
    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(AsyncOpenAI=SlowClient))

    result = asyncio.run(master.orchestrate_analysis(repository_snapshot, _collect_progress))

    assert result.orchestration.mode == "evidence_fallback"
    assert "exceeded the application deadline" in (result.orchestration.note or "")
    assert result.agents_md.startswith("# AGENTS.md\n")


def test_native_root_payload_rejects_unknown_or_duplicate_evidence(repository_snapshot: RepositorySnapshot) -> None:
    reports = asyncio.run(master.run_specialists(repository_snapshot, _collect_progress))

    with pytest.raises(ValueError, match="unsupported or duplicate"):
        master._validated_root_groups(
            {
                "priority_finding_ids": ["not-a-real-id"],
                "merged_finding_ids": [],
                "deferred_finding_ids": ["not-a-real-id"],
            },
            reports,
        )


def test_evidence_firewall_rejects_a_fabricated_quote(repository_snapshot: RepositorySnapshot) -> None:
    fabricated = {
        "title": "Invented claim",
        "detail": "This should never be published.",
        "recommendation": "Do something.",
        "path": "src/app.py",
        "line_start": 5,
        "line_end": 5,
        "quoted_evidence": "this text does not exist in the repository",
        "severity": "critical",
        "confidence": 1.0,
    }

    assert native_agents._verified_finding(repository_snapshot, "risk", fabricated) is None


def test_evidence_firewall_requires_the_specialist_to_have_read_the_cited_source(
    repository_snapshot: RepositorySnapshot,
) -> None:
    payload = {
        "summary": "A claim that happens to match a repository line.",
        "findings": [
            {
                "title": "Dynamic evaluation is reachable",
                "detail": "The handler evaluates payload text.",
                "recommendation": "Replace dynamic evaluation with an explicit parser.",
                "path": "src/app.py",
                "line_start": 5,
                "line_end": 5,
                "quoted_evidence": "return eval(payload)",
                "severity": "high",
                "confidence": 1.0,
            }
        ],
    }

    result = native_agents._firewall_report(
        repository_snapshot,
        "risk",
        payload,
        tool_calls=1,
        observed_source_evidence={},
    )

    assert result.verified_claims == 0
    assert result.rejected_claims == 1


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
