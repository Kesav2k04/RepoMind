"""RepoMind's local stdio MCP adapter for Codex, Cursor, and Claude Code."""

from __future__ import annotations

from collections import OrderedDict
from uuid import uuid4

from mcp.server.fastmcp import FastMCP

from preflight import run_preflight
from schemas import AnalysisResult

server = FastMCP(
    name="RepoMind",
    instructions=(
        "Run a read-only repository preflight before an unfamiliar or risky change. "
        "Treat every finding as bounded evidence, not a complete repository verdict."
    ),
)
_ARTIFACT_CACHE_LIMIT = 12
_artifacts: OrderedDict[str, dict[str, str]] = OrderedDict()


@server.tool(
    name="repomind_preflight",
    description=(
        "Read a public GitHub repository through RepoMind's bounded evidence pipeline and return a "
        "task-scoped, citation-checked AGENTS.md handoff plus risk map."
    ),
)
async def repomind_preflight(repo_url: str, task_description: str | None = None) -> dict[str, object]:
    """Run the same native/fallback preflight used by RepoMind's dashboard."""
    try:
        result = await run_preflight(repo_url, task_description)
    except Exception as exc:
        return {"ok": False, "error": _safe_error(exc)}
    job_id = f"mcp_{uuid4().hex[:12]}"
    _store_artifacts(job_id, result)
    return _preflight_payload(job_id, result)


@server.tool(
    name="repomind_get_artifact",
    description="Return a previously generated RepoMind AGENTS.md or risk-annotated repository map by MCP job ID.",
)
async def repomind_get_artifact(job_id: str, name: str) -> dict[str, object]:
    """Retrieve an artifact created during the current local MCP server session."""
    if name not in {"AGENTS.md", "repo-map.md"}:
        return {"ok": False, "error": "Artifact name must be AGENTS.md or repo-map.md."}
    artifacts = _artifacts.get(job_id)
    if artifacts is None:
        return {
            "ok": False,
            "error": "Artifact was not found in this MCP session. Run repomind_preflight again.",
        }
    _artifacts.move_to_end(job_id)
    return {"ok": True, "job_id": job_id, "name": name, "content": artifacts[name]}


def _store_artifacts(job_id: str, result: AnalysisResult) -> None:
    _artifacts[job_id] = {"AGENTS.md": result.agents_md, "repo-map.md": result.repo_map.markdown}
    _artifacts.move_to_end(job_id)
    while len(_artifacts) > _ARTIFACT_CACHE_LIMIT:
        _artifacts.popitem(last=False)


def _preflight_payload(job_id: str, result: AnalysisResult) -> dict[str, object]:
    return {
        "ok": True,
        "job_id": job_id,
        "repository": result.repository.model_dump(mode="json"),
        "execution": {
            "mode": result.orchestration.mode,
            "model": result.orchestration.model,
            "note": result.orchestration.note,
            "model_tool_calls": result.metrics.model_tool_calls,
        },
        "firewall": result.validation.model_dump(mode="json"),
        "task_brief": result.task_brief.model_dump(mode="json") if result.task_brief else None,
        "findings": [
            finding.model_dump(mode="json")
            for report in result.reports
            for finding in report.findings
        ],
        "artifacts": {"agents_md": result.agents_md, "repository_map": result.repo_map.markdown},
    }


def _safe_error(exc: Exception) -> str:
    detail = str(exc).strip()
    lowered = detail.lower()
    if "github" in lowered or "repository" in lowered or "clone" in lowered or "git" in lowered:
        return "RepoMind could not read that public GitHub repository. Confirm the URL and try again."
    if isinstance(exc, OSError):
        return "RepoMind could not complete local artifact handling. Try again."
    if isinstance(exc, ValueError):
        return detail or "RepoMind could not validate that request. Try again."
    return "RepoMind could not complete the bounded analysis. Try again."


def main() -> None:
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
