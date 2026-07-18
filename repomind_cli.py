"""The local RepoMind command-line handoff for coding agents and developers."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Sequence

from preflight import run_preflight
from schemas import AnalysisResult


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="repomind",
        description="Create an evidence-backed repository preflight for the next coding task.",
    )
    subcommands = parser.add_subparsers(dest="command", required=True)
    preflight = subcommands.add_parser(
        "preflight",
        help="Analyze a public GitHub repository and write a verified AGENTS.md handoff.",
    )
    preflight.add_argument("repo_url", help="Public GitHub HTTPS repository URL.")
    preflight.add_argument("--task", default=None, help="Optional change the next coding agent is about to make.")
    preflight.add_argument(
        "-o",
        "--output",
        required=True,
        type=Path,
        metavar="AGENTS.md",
        help="Destination for AGENTS.md. Existing files require --force.",
    )
    preflight.add_argument(
        "--map-output",
        type=Path,
        metavar="repo-map.md",
        help="Destination for the risk-annotated map (defaults beside AGENTS.md).",
    )
    preflight.add_argument("--force", action="store_true", help="Allow overwriting an existing artifact path.")
    preflight.add_argument("--json", action="store_true", help="Print only the final machine-readable summary to stdout.")
    return parser


async def run_command(arguments: argparse.Namespace) -> int:
    if arguments.command != "preflight":
        raise ValueError("Unknown RepoMind command.")
    agents_path = _output_path(arguments.output)
    map_path = _output_path(arguments.map_output or agents_path.with_name("repo-map.md"))
    if agents_path == map_path:
        raise ValueError("AGENTS.md and repository-map outputs must use different paths.")
    _check_output_path(agents_path, arguments.force)
    _check_output_path(map_path, arguments.force)
    progress = _silent_progress if arguments.json else _console_progress
    result = await run_preflight(arguments.repo_url, arguments.task, progress)
    _write_artifact(agents_path, result.agents_md)
    _write_artifact(map_path, result.repo_map.markdown)
    summary = _summary(result, agents_path, map_path)
    if arguments.json:
        print(json.dumps(summary, ensure_ascii=False))
    else:
        _print_summary(summary)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    arguments = parser.parse_args(argv)
    try:
        return asyncio.run(run_command(arguments))
    except Exception as exc:
        print(f"RepoMind preflight failed: {_safe_error(exc)}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("RepoMind preflight cancelled before artifacts were written.", file=sys.stderr)
        return 130


async def _console_progress(
    phase: str,
    message: str,
    role: str | None = None,
    **details: object,
) -> None:
    action = details.get("action")
    prefix = role or phase
    detail = action if isinstance(action, str) and action else message
    print(f"[{prefix}] {detail}")


async def _silent_progress(
    phase: str,
    message: str,
    role: str | None = None,
    **details: object,
) -> None:
    del phase, message, role, details


def _output_path(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    if not resolved.parent.is_dir():
        raise ValueError(f"Output directory does not exist: {resolved.parent}")
    return resolved


def _check_output_path(path: Path, force: bool) -> None:
    if path.is_dir():
        raise ValueError(f"Output path is a directory: {path}")
    if path.exists() and not force:
        raise ValueError(f"Output already exists: {path}. Use --force to replace it.")


def _write_artifact(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8", newline="\n")


def _summary(result: AnalysisResult, agents_path: Path, map_path: Path) -> dict[str, object]:
    return {
        "repository": result.repository.name,
        "repository_url": result.repository.url,
        "mode": result.orchestration.mode,
        "model": result.orchestration.model,
        "files_analyzed": result.metrics.files_analyzed,
        "findings_published": result.metrics.findings_published,
        "firewall": {
            "proposed_claims": result.validation.proposed_claims,
            "verified_claims": result.validation.validated_findings,
            "rejected_claims": result.validation.rejected_claims,
        },
        "task_brief": result.task_brief.model_dump(mode="json") if result.task_brief else None,
        "artifacts": {"agents_md": str(agents_path), "repository_map": str(map_path)},
    }


def _print_summary(summary: dict[str, object]) -> None:
    firewall = summary["firewall"]
    artifacts = summary["artifacts"]
    print("\nRepoMind preflight complete")
    print(f"Repository: {summary['repository']}")
    print(f"Mode: {summary['mode']}")
    print(f"Evidence: {summary['files_analyzed']} files, {summary['findings_published']} published findings")
    print(
        "Firewall: "
        f"{firewall['verified_claims']}/{firewall['proposed_claims']} claims verified; "
        f"{firewall['rejected_claims']} withheld"
    )
    print(f"AGENTS.md: {artifacts['agents_md']}")
    print(f"Repository map: {artifacts['repository_map']}")


def _safe_error(exc: Exception) -> str:
    detail = str(exc).strip()
    lowered = detail.lower()
    if "github" in lowered or "repository" in lowered or "clone" in lowered or "git" in lowered:
        return "could not read that public GitHub repository. Confirm the URL and try again."
    if isinstance(exc, OSError):
        return "could not write the requested artifact path. Check the destination and try again."
    if isinstance(exc, ValueError):
        return detail or "the request was invalid. Check the arguments and try again."
    return "the bounded analysis could not complete. Try again."


if __name__ == "__main__":
    raise SystemExit(main())
