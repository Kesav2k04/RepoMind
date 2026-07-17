"""Tests for API-facing live progress contracts."""

from __future__ import annotations

import asyncio
from time import perf_counter

from main import Job, _job_duration_ms, publish, serialize_job


def test_publish_serializes_live_action_progress_and_metrics() -> None:
    job = Job(job_id="job_progress", repository_url="https://github.com/acme/demo.git")

    asyncio.run(
        publish(
            job,
            "agent_progress",
            "Risk: Checking dependencies",
            "risk",
            action="Checking dependencies",
            current=2,
            total=4,
            metrics={"sampled_files": 12},
        )
    )

    event = job.events[-1]
    payload = serialize_job(job).model_dump(mode="json")
    assert event.percent == 50
    assert event.action == "Checking dependencies"
    assert event.metrics == {"sampled_files": 12}
    assert payload["events"][0]["percent"] == 50
    assert payload["events"][0]["metrics"]["sampled_files"] == 12


def test_job_duration_includes_elapsed_wall_clock_time() -> None:
    started = perf_counter() - 1.2

    assert _job_duration_ms(started) >= 1_100
