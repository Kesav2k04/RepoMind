"""FastAPI surface for RepoMind's live repository analysis."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from repository import validate_github_url
from schemas import AnalysisResult, AnalysisStatus, AnalyzeRequest, ProgressEvent

app = FastAPI(
    title="RepoMind",
    version="1.0.0",
    description="Evidence-backed GitHub repository intelligence orchestrated by specialist agents.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
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


async def publish(job: Job, phase: str, message: str, role: str | None = None) -> None:
    event = ProgressEvent(phase=phase, message=message, role=role)  # type: ignore[arg-type]
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
    job = Job(job_id=f"job_{uuid4().hex[:12]}", repository_url=canonical_url)
    jobs[job.job_id] = job
    await publish(job, "queued", "Analysis queued. Preparing an isolated GitHub clone.")
    asyncio.create_task(run_analysis_task(job))
    return serialize_job(job)


async def run_analysis_task(job: Job) -> None:
    """Run the analysis after the response returns so the UI can subscribe first."""
    checkout = None
    try:
        # Deferred imports preserve a healthy API surface while specialist modules evolve.
        from master import orchestrate_analysis
        from repository import clone_github_repository, snapshot_repository

        job.status = "running"
        await publish(job, "cloning", "Cloning public repository with bounded history.")
        checkout = await clone_github_repository(job.repository_url)
        await publish(job, "indexing", "Building a bounded evidence pack from code, manifests, tests, and history.")
        snapshot = await asyncio.to_thread(snapshot_repository, checkout, job.repository_url)

        async def progress(phase: str, message: str, role: str | None = None) -> None:
            await publish(job, phase, message, role)

        job.result = await orchestrate_analysis(snapshot, progress)
        job.status = "completed"
        await publish(job, "completed", "Analysis complete. AGENTS.md and repository map are ready.")
    except Exception as exc:  # Expose a safe, actionable API error without leaking a traceback.
        job.status = "failed"
        job.error = str(exc)
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
