"""Concurrent deterministic specialist-worker execution."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from repository import RepositorySnapshot
from schemas import AgentReport
from workers import ANALYZERS

ProgressCallback = Callable[[str, str, str | None], Awaitable[None]]
WORKER_ROLES = ("architecture", "risk", "testing", "history")


async def run_specialists(snapshot: RepositorySnapshot, progress: ProgressCallback) -> list[AgentReport]:
    """Run the four read-only specialist lenses concurrently against one snapshot."""

    async def run(role: str) -> AgentReport:
        await progress("agent_started", f"{role.title()} specialist is reviewing repository evidence.", role)
        report = await asyncio.to_thread(ANALYZERS[role], snapshot)
        await progress("agent_completed", f"{role.title()} specialist returned {len(report.findings)} finding(s).", role)
        return report

    return list(await asyncio.gather(*(run(role) for role in WORKER_ROLES)))