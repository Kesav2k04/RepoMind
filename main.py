"""FastAPI surface for RepoMind's live repository analysis."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from repository import validate_github_url
from schemas import AnalysisResult, AnalysisStatus, AnalyzeRequest, ProgressEvent
from settings import settings

app = FastAPI(
    title="RepoMind",
    version="1.0.0",
    description="Evidence-backed GitHub repository intelligence orchestrated by specialist agents.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_methods=["*"],
    allow_headers=["*"],
)


@dataclass
class Job:
    job_id: str
    repository_url: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    status: str = "queued"
    completed_at: datetime | None = None
    events: list[ProgressEvent] = field(default_factory=list)
    subscribers: set[asyncio.Queue[ProgressEvent]] = field(default_factory=set)
    result: AnalysisResult | None = None
    error: str | None = None


jobs: dict[str, Job] = {}
analysis_semaphore = asyncio.Semaphore(settings.max_concurrent_jobs)
MAX_QUEUED_JOBS_MULTIPLIER = 2


async def publish(
    job: Job,
    phase: str,
    message: str,
    role: str | None = None,
    *,
    action: str | None = None,
    current: int | None = None,
    total: int | None = None,
    metrics: dict[str, int] | None = None,
) -> None:
    percent = round((current / total) * 100) if current is not None and total else None
    event = ProgressEvent(
        phase=phase,
        message=message,
        role=role,  # type: ignore[arg-type]
        action=action,
        current=current,
        total=total,
        percent=percent,
        metrics=metrics or {},
    )
    job.events.append(event)
    for queue in tuple(job.subscribers):
        queue.put_nowait(event)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "repomind"}


@app.post("/api/analyze", response_model=AnalysisStatus, status_code=202)
async def start_analysis(request: AnalyzeRequest) -> AnalysisStatus:
    try:
        canonical_url = validate_github_url(str(request.repo_url))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if _at_demo_capacity():
        raise HTTPException(
            status_code=429,
            detail="RepoMind is at demo capacity. Wait for a running analysis to finish, then try again.",
        )
    job = Job(job_id=f"job_{uuid4().hex[:12]}", repository_url=canonical_url)
    jobs[job.job_id] = job
    await publish(job, "queued", "Analysis queued. Preparing an isolated GitHub clone.")
    asyncio.create_task(run_analysis_task(job))
    return serialize_job(job)


async def run_analysis_task(job: Job) -> None:
    """Run the analysis after the response returns so the UI can subscribe first."""
    if analysis_semaphore.locked():
        await publish(
            job,
            "queued",
            "Demo capacity is busy. Your bounded analysis will start next.",
            action="waiting_for_analysis_slot",
        )
    async with analysis_semaphore:
        await _run_analysis(job)


async def _run_analysis(job: Job) -> None:
    """Perform one resource-bounded analysis while holding a demo-capacity slot."""
    started = perf_counter()
    checkout = None
    try:
        # Deferred imports preserve a healthy API surface while specialist modules evolve.
        from master import orchestrate_analysis
        from repository import clone_github_repository, snapshot_repository

        job.status = "running"
        await publish(job, "cloning", "Cloning public repository with bounded history.", action="cloning_repository")
        checkout = await clone_github_repository(job.repository_url)
        await publish(job, "indexing", "Building a bounded evidence pack from code, manifests, tests, and history.", action="starting_evidence_pack")
        loop = asyncio.get_running_loop()

        def evidence_progress(action: str, current: int | None, total: int | None, metrics: dict[str, int]) -> None:
            asyncio.run_coroutine_threadsafe(
                publish(
                    job,
                    "indexing",
                    _evidence_message(action, current, total),
                    action=action,
                    current=current,
                    total=total,
                    metrics=metrics,
                ),
                loop,
            )

        snapshot = await asyncio.to_thread(snapshot_repository, checkout, job.repository_url, evidence_progress)

        async def progress(
            phase: str,
            message: str,
            role: str | None = None,
            **details: object,
        ) -> None:
            await publish(
                job,
                phase,
                message,
                role,
                action=details.get("action") if isinstance(details.get("action"), str) else None,
                current=details.get("current") if isinstance(details.get("current"), int) else None,
                total=details.get("total") if isinstance(details.get("total"), int) else None,
                metrics=details.get("metrics") if isinstance(details.get("metrics"), dict) else None,
            )

        job.result = await orchestrate_analysis(snapshot, progress)
        elapsed_ms = _job_duration_ms(started)
        job.result.metrics.duration_ms = elapsed_ms
        job.result.orchestration.duration_ms = elapsed_ms
        job.status = "completed"
        await publish(
            job,
            "completed",
            "Analysis complete. AGENTS.md and repository map are ready.",
            action="artifacts_ready",
            metrics=job.result.metrics.model_dump(),
        )
    except Exception as exc:  # Expose a safe, actionable API error without leaking a traceback.
        job.status = "failed"
        job.error = _safe_failure_message(exc)
        await publish(job, "failed", f"Analysis failed: {job.error}")
    finally:
        if checkout is not None:
            from repository import cleanup_checkout
            try:
                await asyncio.to_thread(cleanup_checkout, checkout)
            except (OSError, ValueError):
                pass
        job.completed_at = datetime.now(UTC)


def serialize_job(job: Job) -> AnalysisStatus:
    return AnalysisStatus(
        job_id=job.job_id,
        status=job.status,  # type: ignore[arg-type]
        repository_url=job.repository_url,
        created_at=job.created_at,
        completed_at=job.completed_at,
        events=job.events,
        result=job.result,
        error=job.error,
    )


@app.get("/api/analyze/{job_id}", response_model=AnalysisStatus)
async def get_analysis_status(job_id: str) -> AnalysisStatus:
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Analysis job not found")
    return serialize_job(job)


@app.get("/api/analyze/{job_id}/artifacts/{artifact_name}", response_class=PlainTextResponse)
async def get_artifact(job_id: str, artifact_name: str) -> PlainTextResponse:
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Analysis job not found")
    if job.result is None:
        raise HTTPException(status_code=409, detail="Analysis has not completed")
    artifacts = {"AGENTS.md": job.result.agents_md, "repo-map.md": job.result.repo_map.markdown}
    content = artifacts.get(artifact_name)
    if content is None:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return PlainTextResponse(content, headers={"Content-Disposition": f'attachment; filename="{artifact_name}"'})


@app.websocket("/api/analyze/{job_id}/events")
async def analysis_events(websocket: WebSocket, job_id: str) -> None:
    job = jobs.get(job_id)
    if job is None:
        await websocket.close(code=4404)
        return
    await websocket.accept()
    queue: asyncio.Queue[ProgressEvent] = asyncio.Queue()
    history = list(job.events)
    job.subscribers.add(queue)
    try:
        for event in history:
            await websocket.send_json(event.model_dump(mode="json"))
        while job.status not in {"completed", "failed"}:
            event = await queue.get()
            await websocket.send_json(event.model_dump(mode="json"))
        await websocket.send_json({"phase": "stream_end", "status": job.status})
    except WebSocketDisconnect:
        pass
    finally:
        job.subscribers.discard(queue)


def _evidence_message(action: str, current: int | None, total: int | None) -> str:
    labels = {
        "inventorying_files": "Inventorying repository files",
        "sampling_evidence": "Sampling source and configuration evidence",
        "evidence_ready": "Evidence pack ready",
    }
    label = labels.get(action, "Building evidence pack")
    return f"{label}: {current}/{total}." if current is not None and total else label


def _at_demo_capacity() -> bool:
    active_jobs = sum(1 for job in jobs.values() if job.status in {"queued", "running"})
    return active_jobs >= settings.max_concurrent_jobs * MAX_QUEUED_JOBS_MULTIPLIER


def _job_duration_ms(started: float) -> int:
    """Report the user's full wait: clone, evidence, specialists, and reconciliation."""
    return round((perf_counter() - started) * 1000)


def _safe_failure_message(exc: Exception) -> str:
    """Return an actionable user message without exposing implementation details."""
    if isinstance(exc, (TimeoutError, asyncio.TimeoutError)):
        return "Analysis timed out. Try a smaller public repository or retry in a moment."
    detail = str(exc).lower()
    if "clone" in detail or "repository" in detail or "git" in detail:
        return "RepoMind could not clone this repository. Confirm that it is public and reachable, then try again."
    return "RepoMind could not complete this analysis. Try again or choose another public repository."
