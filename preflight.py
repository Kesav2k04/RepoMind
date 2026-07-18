"""Shared, bounded repository preflight used by the API, CLI, and MCP adapter."""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import Awaitable, Callable

from master import orchestrate_analysis
from repository import cleanup_checkout, clone_github_repository, snapshot_repository, validate_github_url
from schemas import AnalysisResult

ProgressCallback = Callable[..., Awaitable[None]]


async def run_preflight(
    repo_url: str,
    task_description: str | None = None,
    progress: ProgressCallback | None = None,
) -> AnalysisResult:
    """Clone, bound evidence, analyze, and reliably remove a public checkout.

    This is intentionally the shared entry point for agent-native consumers. It
    preserves the same GitHub-only boundary, evidence limits, native GPT-5.6
    path, and deterministic fallback as the dashboard.
    """
    canonical_url = validate_github_url(repo_url)
    callback = progress or _noop_progress
    checkout = None
    try:
        await _emit(
            callback,
            "cloning",
            "Cloning public repository with bounded history.",
            action="cloning_repository",
        )
        checkout = await clone_github_repository(canonical_url)
        await _emit(
            callback,
            "indexing",
            "Building a bounded evidence pack from code, manifests, tests, and history.",
            action="starting_evidence_pack",
        )
        loop = asyncio.get_running_loop()

        def evidence_progress(
            action: str,
            current: int | None,
            total: int | None,
            metrics: dict[str, int],
        ) -> None:
            asyncio.run_coroutine_threadsafe(
                _emit(
                    callback,
                    "indexing",
                    _evidence_message(action, current, total),
                    action=action,
                    current=current,
                    total=total,
                    metrics=metrics,
                ),
                loop,
            )

        snapshot = await asyncio.to_thread(
            snapshot_repository,
            checkout,
            canonical_url,
            evidence_progress,
        )
        return await orchestrate_analysis(snapshot, callback, task_description)
    finally:
        if checkout is not None:
            try:
                await asyncio.to_thread(cleanup_checkout, checkout)
            except (OSError, ValueError):
                # Checkout cleanup cannot invalidate an otherwise-complete handoff.
                pass


async def _noop_progress(
    phase: str,
    message: str,
    role: str | None = None,
    **details: object,
) -> None:
    del phase, message, role, details


async def _emit(
    progress: ProgressCallback,
    phase: str,
    message: str,
    role: str | None = None,
    **details: object,
) -> None:
    """Forward rich progress without breaking simple three-argument clients."""
    parameters = inspect.signature(progress).parameters.values()
    supports_details = any(parameter.kind is inspect.Parameter.VAR_KEYWORD for parameter in parameters)
    if supports_details:
        await progress(phase, message, role, **details)
    else:
        await progress(phase, message, role)


def _evidence_message(action: str, current: int | None, total: int | None) -> str:
    labels = {
        "inventorying_files": "Inventorying repository files",
        "sampling_evidence": "Sampling source and configuration evidence",
        "evidence_ready": "Evidence pack ready",
    }
    label = labels.get(action, "Building evidence pack")
    return f"{label}: {current}/{total}." if current is not None and total else label
