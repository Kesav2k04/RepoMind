"""RepoMind's master orchestration and optional native GPT-5.6 reconciliation."""

from __future__ import annotations

import json
import os
import re
from time import perf_counter
from collections.abc import Awaitable, Callable

from artifacts import build_repository_map, generate_agents_md
from repository import RepositorySnapshot
from schemas import AnalysisResult, OrchestrationMeta
from settings import settings
from worker import run_specialists

ProgressCallback = Callable[[str, str, str | None], Awaitable[None]]


async def orchestrate_analysis(snapshot: RepositorySnapshot, progress: ProgressCallback) -> AnalysisResult:
    """Run four deterministic workers then optionally reconcile with hosted Multi-agent."""
    started = perf_counter()
    await progress("orchestrating", "Dispatching four bounded specialist workstreams in parallel.")
    reports = await run_specialists(snapshot, progress)
    fallback = AnalysisResult(
        repository=snapshot.repository_info(),
        reports=reports,
        agents_md=generate_agents_md(snapshot, reports),
        repo_map=build_repository_map(snapshot, reports),
        orchestration=OrchestrationMeta(
            mode="evidence_fallback",
            completed_roles=["architecture", "risk", "testing", "history"],
        ),
    )
    if not os.getenv("OPENAI_API_KEY"):
        fallback.orchestration.duration_ms = _duration_ms(started)
        fallback.orchestration.note = (
            "Evidence-first fallback used because OPENAI_API_KEY is not configured. "
            "Configure it to enable hosted GPT-5.6 multi-agent reconciliation."
        )
        return fallback

    await progress("reconciling", "GPT-5.6 root agent is reconciling the four independent reports.")
    try:
        result = await _reconcile_with_native_multi_agent(snapshot, reports, fallback)
    except Exception as exc:
        fallback.orchestration.duration_ms = _duration_ms(started)
        fallback.orchestration.note = (
            "Hosted reconciliation was unavailable; returned evidence-first analysis instead. "
            f"Details: {type(exc).__name__}."
        )
        await progress("reconciliation_fallback", fallback.orchestration.note)
        return fallback

    result.orchestration.duration_ms = _duration_ms(started)
    await progress("reconciled", "GPT-5.6 native multi-agent reconciliation completed.")
    return result


async def _reconcile_with_native_multi_agent(
    snapshot: RepositorySnapshot, reports: list, fallback: AnalysisResult
) -> AnalysisResult:
    """Ask a hosted root agent to delegate and reconcile evidence-only findings.

    The API owns the subagent tree. RepoMind supplies deterministic reports and a
    bounded repository packet so the model cannot claim access to an unbounded
    filesystem or external sources.
    """
    from openai import AsyncOpenAI

    developer_instructions = """You are RepoMind's /root technical-analysis agent.
Delegate exactly four concurrent, bounded reviews to subagents named architecture_mapper,
risk_auditor, test_coverage_analyst, and history_archaeologist. Give each subagent only its
matching section of the supplied evidence packet, wait for all results, then reconcile them.
Never claim facts that are not present in the evidence. Preserve file paths exactly and
resolve duplicates or disagreements explicitly.

Return ONLY valid JSON with these string fields: `summary`, `agents_md`, and `repo_map_markdown`.
`agents_md` must be concise and practical for future coding agents, covering repository overview,
architecture/navigation, working rules, risk-aware areas, and tests/verification. `repo_map_markdown`
must be a human-readable map with [critical], [high], [medium], [low], or [info] labels."""
    evidence = {
        "repository": snapshot.prompt_summary(),
        "specialist_reports": [report.model_dump(mode="json") for report in reports],
    }
    client = AsyncOpenAI()
    response = await client.beta.responses.create(
        model=settings.openai_model,
        input=[
            {"role": "developer", "content": developer_instructions},
            {"role": "user", "content": json.dumps(evidence, ensure_ascii=False)},
        ],
        multi_agent={"enabled": True, "max_concurrent_subagents": 4},
        betas=["responses_multi_agent=v1"],
    )
    payload = _extract_json(_root_final_text(response))
    agents_md = payload.get("agents_md")
    repo_map_markdown = payload.get("repo_map_markdown")
    if not isinstance(agents_md, str) or not agents_md.strip():
        raise ValueError("Root agent did not return a usable AGENTS.md artifact.")
    if not isinstance(repo_map_markdown, str) or not repo_map_markdown.strip():
        raise ValueError("Root agent did not return a usable repository map artifact.")
    fallback.agents_md = agents_md.strip() + "\n"
    fallback.repo_map.markdown = repo_map_markdown.strip() + "\n"
    summary = payload.get("summary")
    if isinstance(summary, str) and summary.strip():
        fallback.repo_map.overview = summary.strip()
    fallback.orchestration = OrchestrationMeta(
        mode="native_multi_agent",
        model=settings.openai_model,
        completed_roles=["architecture", "risk", "testing", "history"],
        note="Hosted root agent delegated four specialist reviews and reconciled their evidence.",
    )
    return fallback


def _root_final_text(response: object) -> str:
    parts: list[str] = []
    for item in getattr(response, "output", []):
        agent = getattr(item, "agent", None)
        if getattr(item, "type", None) != "message" or getattr(agent, "agent_name", None) != "/root":
            continue
        if getattr(item, "phase", None) not in {None, "final_answer"}:
            continue
        for content in getattr(item, "content", []):
            if getattr(content, "type", None) == "output_text":
                parts.append(getattr(content, "text", ""))
    final_text = "".join(parts).strip()
    if not final_text:
        raise ValueError("No final root-agent output was returned.")
    return final_text


def _extract_json(text: str) -> dict[str, object]:
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    parsed = json.loads(fenced.group(1) if fenced else text)
    if not isinstance(parsed, dict):
        raise ValueError("Expected a JSON object from the root agent.")
    return parsed


def _duration_ms(started: float) -> int:
    return round((perf_counter() - started) * 1000)