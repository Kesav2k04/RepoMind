"""Concurrent deterministic specialist-worker execution."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
import inspect

from repository import RepositorySnapshot
from schemas import AgentReport
from workers import ANALYZERS
from workers._shared import WorkerUpdate

ProgressCallback = Callable[..., Awaitable[None]]
WORKER_ROLES = ("architecture", "risk", "testing", "history")


async def run_specialists(snapshot: RepositorySnapshot, progress: ProgressCallback) -> list[AgentReport]:
    """Run the four read-only specialist lenses concurrently against one snapshot."""

    async def run(role: str) -> AgentReport:
        await _publish(
            progress,
            "agent_started",
            f"{role.title()} specialist is starting its evidence review.",
            role,
            action="Starting specialist review",
            current=0,
            total=4,
            percent=0,
        )
        loop = asyncio.get_running_loop()
        updates: asyncio.Queue[WorkerUpdate] = asyncio.Queue()

        def observe(update: WorkerUpdate) -> None:
            loop.call_soon_threadsafe(updates.put_nowait, update)

        analysis_task = asyncio.create_task(asyncio.to_thread(ANALYZERS[role], snapshot, observe))
        while not analysis_task.done():
            try:
                update = await asyncio.wait_for(updates.get(), timeout=0.05)
            except TimeoutError:
                continue
            await _publish_update(progress, role, update)

        report = await analysis_task
        while not updates.empty():
            await _publish_update(progress, role, updates.get_nowait())
        await _publish(
            progress,
            "agent_completed",
            f"{role.title()} specialist completed {len(report.findings)} evidence-backed finding(s).",
            role,
            action="Completed specialist review",
            current=4,
            total=4,
            percent=100,
            metrics={"findings": len(report.findings), "evidence_locations": report.evidence_count},
        )
        return report

    return list(await asyncio.gather(*(run(role) for role in WORKER_ROLES)))


async def _publish_update(progress: ProgressCallback, role: str, update: WorkerUpdate) -> None:
    percent = round((update.current / update.total) * 100) if update.total else None
    await _publish(
        progress,
        "agent_progress",
        f"{role.title()}: {update.action}",
        role,
        action=update.action,
        current=update.current,
        total=update.total,
        percent=percent,
        metrics=update.metrics,
    )


async def _publish(
    progress: ProgressCallback,
    phase: str,
    message: str,
    role: str | None,
    **details: object,
) -> None:
    """Support both legacy three-argument and enriched progress callbacks."""
    signature = inspect.signature(progress)
    parameters = signature.parameters.values()
    accepts_keywords = any(parameter.kind is inspect.Parameter.VAR_KEYWORD for parameter in parameters)
    if accepts_keywords:
        await progress(phase, message, role, **details)
        return
    accepted = {name for name in signature.parameters if name not in {"phase", "message", "role"}}
    supported_details = {name: value for name, value in details.items() if name in accepted}
    await progress(phase, message, role, **supported_details)
