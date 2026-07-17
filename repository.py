"""Safe GitHub checkout and bounded evidence extraction for RepoMind."""

from __future__ import annotations

import asyncio
from collections import Counter
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from collections.abc import Callable, Iterable
from urllib.parse import urlparse

from schemas import EvidenceLocation, RepositoryInfo
from settings import settings

IGNORED_DIRECTORIES = {
    ".git", ".next", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".tox", ".venv",
    "__pycache__", "bower_components", "build", "coverage", "dist", "node_modules", "out",
    "target", "vendor", "venv",
}
TEXT_EXTENSIONS = {
    ".py": "Python", ".ts": "TypeScript", ".tsx": "TypeScript", ".js": "JavaScript",
    ".jsx": "JavaScript", ".go": "Go", ".rs": "Rust", ".java": "Java", ".kt": "Kotlin",
    ".rb": "Ruby", ".php": "PHP", ".cs": "C#", ".c": "C", ".h": "C", ".cpp": "C++",
    ".swift": "Swift", ".sql": "SQL", ".sh": "Shell", ".md": "Markdown", ".json": "JSON",
    ".yaml": "YAML", ".yml": "YAML", ".toml": "TOML", ".mjs": "JavaScript",
    ".css": "CSS", ".html": "HTML", ".vue": "Vue", ".svelte": "Svelte", ".cc": "C++",
    ".hpp": "C++", ".kts": "Kotlin",
}
IMPORTANT_NAMES = {
    "readme.md", "agents.md", "package.json", "pyproject.toml", "requirements.txt", "setup.py",
    "dockerfile", "docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml",
    "makefile", "go.mod", "cargo.toml", "setup.cfg",
}
CONFIG_NAMES = IMPORTANT_NAMES | {
    ".env.example", ".gitignore", "jest.config.js", "jest.config.ts", "pytest.ini", "ruff.toml",
    "tsconfig.json", "vite.config.ts",
}
MAX_FILES = 500
MAX_DISCOVERED_FILES = 10_000
MAX_FILE_BYTES = 80_000
MAX_IMPORTANT_FILE_CHARS = 10_000
MAX_SAMPLE_FILE_CHARS = 3_000
MAX_EVIDENCE_CHARS = 180_000
CLONE_TIMEOUT_SECONDS = 120
GIT_TIMEOUT_SECONDS = 15
CLONE_HISTORY_DEPTH = 100
MAX_EVIDENCE_EXCERPT_CHARS = 240
MAX_EVIDENCE_REASON_CHARS = 320
PROGRESS_BATCH_SIZE = 25

_GITHUB_OWNER_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37})?$")
_GITHUB_REPOSITORY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")

SnapshotProgressCallback = Callable[[str, int | None, int | None, dict[str, int]], None]

_MANIFEST_NAMES = {
    "package.json", "pyproject.toml", "requirements.txt", "setup.py", "setup.cfg", "pipfile",
    "go.mod", "cargo.toml", "cargo.lock", "gemfile", "gemfile.lock", "composer.json",
    "pom.xml", "build.gradle", "build.gradle.kts", "gradle.properties", "mix.exs",
}


@dataclass(frozen=True)
class FileInventory:
    """The bounded file inventory and the limits encountered while producing it."""

    records: list[tuple[str, int]]
    discovered_file_count: int
    inventory_limit_reached: bool
    selection_limit_reached: bool


@dataclass
class EvidenceExtraction:
    """Evidence retained from selected files, with explicit extraction boundaries."""

    important: dict[str, str]
    sampled: dict[str, str]
    chars_collected: int = 0
    evidence_char_limit_reached: bool = False
    oversized_files_skipped: int = 0
    unreadable_files_skipped: int = 0
    files_with_truncated_excerpts: int = 0
    files_omitted_by_char_limit: int = 0


@dataclass
class RepositorySnapshot:
    root: Path
    source_url: str
    name: str
    commit: str | None
    default_branch: str | None
    files: list[str]
    language_counts: Counter[str]
    language_examples: dict[str, str]
    important_file_contents: dict[str, str]
    sampled_contents: dict[str, str]
    config_files: list[str]
    commit_messages: list[str]
    churn_files: list[tuple[str, int]]
    contributors: list[str]
    test_commands: list[str]
    commits_inspected: int = 0
    discovered_file_count: int = 0
    inventory_limit_reached: bool = False
    selection_limit_reached: bool = False
    evidence_chars_collected: int = 0
    evidence_char_limit_reached: bool = False
    oversized_files_skipped: int = 0
    unreadable_files_skipped: int = 0
    files_with_truncated_excerpts: int = 0
    files_omitted_by_char_limit: int = 0

    @property
    def file_count(self) -> int:
        return len(self.files)

    @property
    def selected_file_count(self) -> int:
        """Number of files retained in this bounded inventory."""
        return self.file_count

    @property
    def partial_analysis(self) -> bool:
        """Whether any repository source was excluded or truncated by safety limits."""
        return any(
            (
                self.inventory_limit_reached,
                self.selection_limit_reached,
                self.evidence_char_limit_reached,
                self.oversized_files_skipped > 0,
                self.unreadable_files_skipped > 0,
                self.files_with_truncated_excerpts > 0,
                self.files_omitted_by_char_limit > 0,
            )
        )

    def evidence_limits(self) -> dict[str, int]:
        """Return the fixed source-evidence budgets used for this snapshot."""
        return {
            "max_discovered_files": MAX_DISCOVERED_FILES,
            "max_selected_files": MAX_FILES,
            "max_inventory_files": MAX_FILES,
            "max_file_bytes_for_content": MAX_FILE_BYTES,
            "max_total_content_chars": MAX_EVIDENCE_CHARS,
        }

    @property
    def primary_language(self) -> str:
        return self.language_counts.most_common(1)[0][0] if self.language_counts else "Unknown"

    @property
    def combined_config(self) -> str:
        return "\n".join(self.important_file_contents.values())

    @property
    def combined_test_content(self) -> str:
        return "\n".join(
            content for path, content in self.sampled_contents.items() if _is_test_path(path)
        )

    def repository_info(self) -> RepositoryInfo:
        return RepositoryInfo(name=self.name, url=self.source_url, default_branch=self.default_branch,
                              commit=self.commit, file_count=self.file_count, primary_language=self.primary_language)

    def metrics(self) -> dict[str, int]:
        """Return UI-ready, evidence-backed counts for this bounded snapshot."""
        return repository_metrics(self)

    def prompt_summary(self) -> dict[str, object]:
        return {
            "name": self.name, "commit": self.commit, "default_branch": self.default_branch,
            "file_count": self.file_count, "languages": dict(self.language_counts.most_common(8)),
            "files": self.files, "config_files": self.config_files, "test_commands": self.test_commands,
            "recent_commit_subjects": self.commit_messages, "high_churn_files": self.churn_files,
            "important_file_contents": self.important_file_contents, "source_samples": self.sampled_contents,
            "evidence_limits": self.evidence_limits(),
            "analysis_scope": {
                "discovered_files": self.discovered_file_count,
                "selected_files": self.selected_file_count,
                "discovered_count_is_lower_bound": self.inventory_limit_reached,
                "inventory_limit_reached": self.inventory_limit_reached,
                "selection_limit_reached": self.selection_limit_reached,
                "source_evidence_partial": self.partial_analysis,
                "evidence_chars_collected": self.evidence_chars_collected,
                "evidence_char_limit_reached": self.evidence_char_limit_reached,
                "oversized_files_skipped": self.oversized_files_skipped,
                "unreadable_files_skipped": self.unreadable_files_skipped,
                "files_with_truncated_excerpts": self.files_with_truncated_excerpts,
                "files_omitted_by_char_limit": self.files_omitted_by_char_limit,
            },
        }


def validate_github_url(repo_url: str) -> str:
    """Validate a public GitHub URL and return a canonical clone URL."""
    if not isinstance(repo_url, str) or not repo_url or repo_url != repo_url.strip():
        raise ValueError("Repository URL must be a non-empty, unpadded string.")
    if "%" in repo_url:
        raise ValueError("Repository URL must not contain encoded path characters.")
    parsed = urlparse(repo_url)
    if parsed.scheme != "https" or parsed.hostname not in {"github.com", "www.github.com"}:
        raise ValueError("RepoMind accepts public https://github.com/owner/repository URLs only.")
    try:
        has_port = parsed.port is not None
    except ValueError as exc:
        raise ValueError("Repository URL contains an invalid port.") from exc
    if parsed.username or parsed.password or has_port or parsed.query or parsed.fragment:
        raise ValueError("Repository URL must not include credentials, ports, query parameters, or fragments.")
    parts = [part for part in parsed.path.strip("/").split("/") if part]
    if len(parts) != 2:
        raise ValueError("Repository URL must include exactly an owner and repository name.")
    owner, repository = parts
    if repository.lower().endswith(".git"):
        repository = repository[:-4]
    if (
        not _GITHUB_OWNER_RE.fullmatch(owner)
        or not _GITHUB_REPOSITORY_RE.fullmatch(repository)
        or repository.endswith(".")
    ):
        raise ValueError("Repository owner or name is invalid.")
    return f"https://github.com/{owner}/{repository}.git"


def repository_metrics(snapshot: RepositorySnapshot) -> dict[str, int]:
    """Return bounded evidence-pack counts used by progress and completion UI."""
    return {
        "files_analyzed": snapshot.file_count,
        "files_discovered": snapshot.discovered_file_count,
        "files_selected": snapshot.selected_file_count,
        "files_excluded_by_selection": max(0, snapshot.discovered_file_count - snapshot.selected_file_count),
        "sampled_files": len(snapshot.sampled_contents),
        "manifests_found": count_manifest_files(snapshot.files),
        "tests_discovered": count_test_files(snapshot.files),
        "commits_inspected": max(0, snapshot.commits_inspected),
        "partial_analysis": int(snapshot.partial_analysis),
        "inventory_limit_reached": int(snapshot.inventory_limit_reached),
        "selection_limit_reached": int(snapshot.selection_limit_reached),
        "evidence_chars_collected": max(0, snapshot.evidence_chars_collected),
        "evidence_char_limit_reached": int(snapshot.evidence_char_limit_reached),
        "oversized_files_skipped": max(0, snapshot.oversized_files_skipped),
        "unreadable_files_skipped": max(0, snapshot.unreadable_files_skipped),
        "files_with_truncated_excerpts": max(0, snapshot.files_with_truncated_excerpts),
        "files_omitted_by_char_limit": max(0, snapshot.files_omitted_by_char_limit),
    }


def count_manifest_files(paths: Iterable[str]) -> int:
    """Count recognized dependency/build manifests from an inventory of relative paths."""
    return sum(
        1
        for path in paths
        if isinstance(path, str) and Path(path).name.lower() in _MANIFEST_NAMES
    )


def count_test_files(paths: Iterable[str]) -> int:
    """Count conventionally named or located test files from an inventory."""
    return sum(1 for path in paths if isinstance(path, str) and _is_test_path(path))


def evidence_location(
    path: str,
    content: str | None,
    pattern_or_text: re.Pattern[str] | str,
    reason: str | None = None,
) -> EvidenceLocation:
    """Create a bounded, exact evidence location for a matched excerpt.

    A missing excerpt or no match is represented as file-level evidence rather
    than guessed line data. This keeps downstream findings factual even when a
    file could not be sampled or a pattern no longer appears in its excerpt.
    """
    safe_path = _bounded_text(path, 512).replace("\\", "/") or "unknown"
    safe_reason = _bounded_text(reason, MAX_EVIDENCE_REASON_CHARS) or None
    if not isinstance(content, str) or not content:
        return EvidenceLocation(path=safe_path, reason=safe_reason)

    match_start, match_end = _match_span(content, pattern_or_text)
    if match_start is None or match_end is None:
        return EvidenceLocation(path=safe_path, reason=safe_reason)

    line_start = content.count("\n", 0, match_start) + 1
    line_end = content.count("\n", 0, max(match_start, match_end - 1)) + 1
    excerpt = _excerpt_around_match(content, match_start, match_end)
    return EvidenceLocation(
        path=safe_path,
        line_start=line_start,
        line_end=line_end,
        excerpt=excerpt,
        reason=safe_reason,
    )


def _match_span(content: str, pattern_or_text: re.Pattern[str] | str) -> tuple[int | None, int | None]:
    if isinstance(pattern_or_text, str):
        if not pattern_or_text:
            return None, None
        start = content.find(pattern_or_text)
        return (start, start + len(pattern_or_text)) if start >= 0 else (None, None)
    if isinstance(pattern_or_text, re.Pattern):
        match = pattern_or_text.search(content)
        return (match.start(), match.end()) if match else (None, None)
    return None, None


def _excerpt_around_match(content: str, match_start: int, match_end: int) -> str:
    line_start = content.rfind("\n", 0, match_start) + 1
    line_end = content.find("\n", match_end)
    if line_end < 0:
        line_end = len(content)
    line = content[line_start:line_end].rstrip("\r")
    offset = match_start - line_start
    if len(line) <= MAX_EVIDENCE_EXCERPT_CHARS:
        return line
    visible_limit = MAX_EVIDENCE_EXCERPT_CHARS - 2
    before = visible_limit // 2
    after = visible_limit - before
    start = max(0, offset - before)
    end = min(len(line), max(offset + after, match_end - line_start))
    if end - start > visible_limit:
        start = min(start, len(line) - visible_limit)
        end = start + visible_limit
    excerpt = line[start:end]
    return f"{'…' if start else ''}{excerpt}{'…' if end < len(line) else ''}"


def _bounded_text(value: object, limit: int) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()[:limit]


def _metrics_from_files(
    paths: Iterable[str],
    *,
    discovered_file_count: int | None = None,
    inventory_limit_reached: bool = False,
    selection_limit_reached: bool = False,
) -> dict[str, int]:
    inventory = list(paths)
    return {
        "files_analyzed": len(inventory),
        "files_discovered": max(0, discovered_file_count if discovered_file_count is not None else len(inventory)),
        "files_selected": len(inventory),
        "files_excluded_by_selection": max(
            0,
            (discovered_file_count if discovered_file_count is not None else len(inventory)) - len(inventory),
        ),
        "sampled_files": 0,
        "manifests_found": count_manifest_files(inventory),
        "tests_discovered": count_test_files(inventory),
        "commits_inspected": 0,
        "partial_analysis": int(inventory_limit_reached or selection_limit_reached),
        "inventory_limit_reached": int(inventory_limit_reached),
        "selection_limit_reached": int(selection_limit_reached),
        "evidence_chars_collected": 0,
        "evidence_char_limit_reached": 0,
        "oversized_files_skipped": 0,
        "unreadable_files_skipped": 0,
        "files_with_truncated_excerpts": 0,
        "files_omitted_by_char_limit": 0,
    }


def _apply_extraction_metrics(metrics: dict[str, int], extraction: EvidenceExtraction) -> None:
    """Keep progress telemetry aligned with the evidence actually retained."""
    metrics.update(
        {
            "sampled_files": len(extraction.sampled),
            "evidence_chars_collected": extraction.chars_collected,
            "evidence_char_limit_reached": int(extraction.evidence_char_limit_reached),
            "oversized_files_skipped": extraction.oversized_files_skipped,
            "unreadable_files_skipped": extraction.unreadable_files_skipped,
            "files_with_truncated_excerpts": extraction.files_with_truncated_excerpts,
            "files_omitted_by_char_limit": extraction.files_omitted_by_char_limit,
        }
    )
    metrics["partial_analysis"] = int(
        bool(metrics.get("inventory_limit_reached"))
        or bool(metrics.get("selection_limit_reached"))
        or extraction.evidence_char_limit_reached
        or extraction.oversized_files_skipped > 0
        or extraction.unreadable_files_skipped > 0
        or extraction.files_with_truncated_excerpts > 0
        or extraction.files_omitted_by_char_limit > 0
    )


def _emit_progress(
    on_progress: SnapshotProgressCallback | None,
    action: str,
    current: int | None,
    total: int | None,
    metrics: dict[str, int],
) -> None:
    """Publish telemetry without allowing an observer failure to break analysis."""
    if on_progress is None:
        return
    try:
        on_progress(action, current, total, dict(metrics))
    except Exception:
        return


async def clone_github_repository(repo_url: str) -> Path:
    """Perform a bounded shallow checkout below the configured portable cache root."""
    canonical = validate_github_url(repo_url)
    cache_root = _cache_root()
    try:
        target = Path(tempfile.mkdtemp(prefix="analysis-", dir=cache_root))
    except OSError as exc:
        raise RuntimeError(
            "RepoMind could not create an isolated repository checkout. "
            "Choose a writable REPOMIND_CACHE_DIR and try again."
        ) from exc
    environment = os.environ.copy()
    environment["GIT_TERMINAL_PROMPT"] = "0"
    try:
        completed = await asyncio.to_thread(
            subprocess.run,
            [
                "git", "clone", "--depth", str(CLONE_HISTORY_DEPTH), "--no-tags", "--single-branch",
                "--config", "protocol.file.allow=never", canonical, str(target),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=settings.clone_timeout_seconds,
            check=False,
            env=environment,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        shutil.rmtree(target, ignore_errors=True)
        raise RuntimeError("Git clone did not complete within RepoMind's safety limits.") from exc
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip().replace("\n", " ")[-500:]
        shutil.rmtree(target, ignore_errors=True)
        raise RuntimeError(f"Git clone failed: {detail or 'unknown Git error'}")
    return target


def cleanup_checkout(checkout: Path) -> None:
    """Remove only the isolated checkout directory created for a completed job."""
    cache_root = _cache_root().resolve()
    candidate = checkout.resolve()
    try:
        candidate.relative_to(cache_root)
    except ValueError as exc:
        raise ValueError("Refusing to remove a checkout outside REPOMIND_CACHE_DIR.") from exc
    if not candidate.name.startswith("analysis-"):
        raise ValueError("Refusing to remove a directory not created by RepoMind.")
    shutil.rmtree(candidate, ignore_errors=True)

def _cache_root() -> Path:
    """Create and resolve the configured cache root with an actionable error."""
    try:
        cache_root = settings.cache_dir.expanduser()
        cache_root.mkdir(parents=True, exist_ok=True)
        cache_root = cache_root.resolve()
    except (OSError, RuntimeError) as exc:
        raise RuntimeError(
            "RepoMind could not create REPOMIND_CACHE_DIR. "
            "Choose a writable local directory and try again."
        ) from exc
    if not cache_root.is_dir():
        raise RuntimeError("REPOMIND_CACHE_DIR must point to a writable directory.")
    return cache_root


def snapshot_repository(
    root: Path,
    source_url: str,
    on_progress: SnapshotProgressCallback | None = None,
) -> RepositorySnapshot:
    """Extract deterministic evidence without following repository symlinks.

    ``on_progress`` is synchronous so callers can safely invoke this function in
    a worker thread. It receives only bounded numeric metrics and is best-effort:
    an observer error must never fail a repository analysis.
    """
    root = root.resolve()
    if not root.is_dir():
        raise ValueError("Repository checkout directory does not exist.")
    _emit_progress(on_progress, "inventorying_files", 0, None, _metrics_from_files(()))
    inventory = _collect_file_records(root, on_progress)
    records = inventory.records
    files = [relative for relative, _ in records]
    language_counts: Counter[str] = Counter()
    language_examples: dict[str, str] = {}
    for relative, _ in records:
        language = TEXT_EXTENSIONS.get(Path(relative).suffix.lower())
        if language and language != "Markdown":
            language_counts[language] += 1
            language_examples.setdefault(language, relative)
    inventory_metrics = _metrics_from_files(
        files,
        discovered_file_count=inventory.discovered_file_count,
        inventory_limit_reached=inventory.inventory_limit_reached,
        selection_limit_reached=inventory.selection_limit_reached,
    )
    extraction = _extract_content(root, records, on_progress, inventory_metrics)
    messages, churn, contributors, commit, branch, commits_inspected = _git_evidence(root)
    package = _load_package_json(root / "package.json")
    snapshot = RepositorySnapshot(
        root=root, source_url=source_url, name=_repository_name(source_url, root), commit=commit,
        default_branch=branch, files=files,
        language_counts=language_counts, language_examples=language_examples,
        important_file_contents=extraction.important, sampled_contents=extraction.sampled,
        config_files=[path for path in files if _is_config_path(path)][:32],
        commit_messages=messages, churn_files=churn, contributors=contributors,
        test_commands=_test_commands(package, files), commits_inspected=commits_inspected,
        discovered_file_count=inventory.discovered_file_count,
        inventory_limit_reached=inventory.inventory_limit_reached,
        selection_limit_reached=inventory.selection_limit_reached,
        evidence_chars_collected=extraction.chars_collected,
        evidence_char_limit_reached=extraction.evidence_char_limit_reached,
        oversized_files_skipped=extraction.oversized_files_skipped,
        unreadable_files_skipped=extraction.unreadable_files_skipped,
        files_with_truncated_excerpts=extraction.files_with_truncated_excerpts,
        files_omitted_by_char_limit=extraction.files_omitted_by_char_limit,
    )
    _emit_progress(
        on_progress,
        "evidence_ready",
        snapshot.file_count,
        snapshot.file_count,
        repository_metrics(snapshot),
    )
    return snapshot


def _collect_file_records(
    root: Path,
    on_progress: SnapshotProgressCallback | None = None,
) -> FileInventory:
    """Build a deterministic inventory with bounded traversal and content input."""
    candidates: list[tuple[str, int]] = []
    for directory, directory_names, file_names in os.walk(root, topdown=True, followlinks=False):
        directory_names[:] = sorted(
            name for name in directory_names if name.lower() not in IGNORED_DIRECTORIES
        )
        for file_name in sorted(file_names):
            if len(candidates) >= MAX_DISCOVERED_FILES:
                break
            path = Path(directory, file_name)
            try:
                if path.is_symlink() or not path.is_file():
                    continue
                candidates.append((path.relative_to(root).as_posix(), path.stat().st_size))
                if len(candidates) % PROGRESS_BATCH_SIZE == 0:
                    _emit_progress(
                        on_progress,
                        "inventorying_files",
                        len(candidates),
                        None,
                        _metrics_from_files(
                            (relative for relative, _ in candidates),
                            discovered_file_count=len(candidates),
                            selection_limit_reached=len(candidates) > MAX_FILES,
                        ),
                    )
            except OSError:
                continue
        if len(candidates) >= MAX_DISCOVERED_FILES:
            break
    inventory_limit_reached = len(candidates) >= MAX_DISCOVERED_FILES
    selected = sorted(candidates, key=lambda item: (_file_priority(item[0]), item[0].lower()))[:MAX_FILES]
    selection_limit_reached = len(candidates) > len(selected)
    _emit_progress(
        on_progress,
        "inventorying_files",
        len(selected),
        None if inventory_limit_reached else len(candidates),
        _metrics_from_files(
            (relative for relative, _ in selected),
            discovered_file_count=len(candidates),
            inventory_limit_reached=inventory_limit_reached,
            selection_limit_reached=selection_limit_reached,
        ),
    )
    return FileInventory(
        records=sorted(selected, key=lambda item: item[0]),
        discovered_file_count=len(candidates),
        inventory_limit_reached=inventory_limit_reached,
        selection_limit_reached=selection_limit_reached,
    )


def _file_priority(relative: str) -> int:
    if Path(relative).name.lower() in IMPORTANT_NAMES:
        return 0
    if _is_config_path(relative):
        return 1
    if _is_test_path(relative):
        return 2
    if len(Path(relative).parts) == 1:
        return 3
    return 4


def _extract_content(
    root: Path,
    records: list[tuple[str, int]],
    on_progress: SnapshotProgressCallback | None = None,
    inventory_metrics: dict[str, int] | None = None,
) -> EvidenceExtraction:
    extraction = EvidenceExtraction(important={}, sampled={})
    ordered_records = sorted(records, key=lambda item: (_file_priority(item[0]), item[0].lower()))
    total = len(ordered_records)
    metrics = dict(inventory_metrics or _metrics_from_files(relative for relative, _ in records))
    _apply_extraction_metrics(metrics, extraction)
    _emit_progress(on_progress, "sampling_evidence", 0, total, metrics)
    for current, (relative, size) in enumerate(ordered_records, start=1):
        if size > MAX_FILE_BYTES or not _is_text_candidate(relative):
            if size > MAX_FILE_BYTES:
                extraction.oversized_files_skipped += 1
        else:
            is_important = Path(relative).name.lower() in IMPORTANT_NAMES
            read_result = _read_text_excerpt(
                root / relative,
                MAX_IMPORTANT_FILE_CHARS if is_important else MAX_SAMPLE_FILE_CHARS,
            )
            if read_result is None:
                extraction.unreadable_files_skipped += 1
            else:
                content, excerpt_truncated = read_result
                remaining_chars = MAX_EVIDENCE_CHARS - extraction.chars_collected
                if remaining_chars <= 0:
                    extraction.evidence_char_limit_reached = True
                    extraction.files_omitted_by_char_limit += 1
                else:
                    retained_content = content[:remaining_chars]
                    content_truncated = excerpt_truncated or len(retained_content) < len(content)
                    if len(retained_content) < len(content):
                        extraction.evidence_char_limit_reached = True
                    if content_truncated:
                        extraction.files_with_truncated_excerpts += 1
                    extraction.chars_collected += len(retained_content)
                    extraction.sampled[relative] = retained_content
                    if is_important:
                        extraction.important[relative] = retained_content
        if current % PROGRESS_BATCH_SIZE == 0 or current == total:
            _apply_extraction_metrics(metrics, extraction)
            _emit_progress(on_progress, "sampling_evidence", current, total, metrics)
    return extraction


def _is_text_candidate(relative: str) -> bool:
    return (
        Path(relative).suffix.lower() in TEXT_EXTENSIONS
        or Path(relative).name.lower() in IMPORTANT_NAMES
        or _is_config_path(relative)
    )


def _read_text_excerpt(path: Path, char_limit: int) -> tuple[str, bool] | None:
    try:
        with path.open("rb") as handle:
            data = handle.read(MAX_FILE_BYTES)
    except OSError:
        return None
    if b"\x00" in data:
        return None
    content = data.decode("utf-8", errors="replace")
    return content[:char_limit], len(content) > char_limit


def _is_config_path(relative: str) -> bool:
    path = Path(relative)
    if path.name.lower() in CONFIG_NAMES:
        return True
    parts = [part.lower() for part in path.parts]
    return len(parts) >= 3 and parts[:2] == [".github", "workflows"] and path.suffix.lower() in {".yml", ".yaml"}


def _is_test_path(relative: str) -> bool:
    path = Path(relative)
    parts = {part.lower() for part in path.parts[:-1]}
    name = path.name.lower()
    return (
        bool(parts & {"test", "tests", "__tests__", "spec", "specs"})
        or name.startswith("test_")
        or name.endswith("_test.py")
        or ".test." in name
        or ".spec." in name
    )


def _git_evidence(
    root: Path,
) -> tuple[list[str], list[tuple[str, int]], list[str], str | None, str | None, int]:
    def git(*args: str) -> str:
        try:
            completed = subprocess.run(
                ["git", "-C", str(root), "--no-pager", *args],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
                timeout=GIT_TIMEOUT_SECONDS,
            )
        except (OSError, subprocess.TimeoutExpired):
            return ""
        return (completed.stdout or "").strip() if completed.returncode == 0 else ""
    all_messages = [line for line in git("log", "-100", "--format=%s").splitlines() if line]
    messages = all_messages[:20]
    commit_count_text = git("rev-list", "--count", "--max-count=100", "HEAD")
    try:
        commits_inspected = max(0, int(commit_count_text))
    except ValueError:
        commits_inspected = len(all_messages)
    names = git("log", "-100", "--format=%an").splitlines()
    contributors = [name for name, _ in Counter(name for name in names if name).most_common(8)]
    changed = git("log", "-100", "--name-only", "--pretty=format:").splitlines()
    churn = Counter(name for name in changed if name).most_common(12)
    default_branch = git("symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD")
    if default_branch.startswith("origin/"):
        default_branch = default_branch.removeprefix("origin/")
    return (
        messages,
        churn,
        contributors,
        git("rev-parse", "HEAD") or None,
        default_branch or git("branch", "--show-current") or None,
        commits_inspected,
    )


def _load_package_json(path: Path) -> dict[str, object]:
    try:
        if path.is_symlink() or path.stat().st_size > MAX_FILE_BYTES:
            return {}
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _test_commands(package: dict[str, object], files: list[str]) -> list[str]:
    commands: list[str] = []
    file_names = {Path(path).name.lower() for path in files}
    has_test_files = any(_is_test_path(path) for path in files)
    scripts = package.get("scripts")
    if isinstance(scripts, dict):
        for script_name, script in scripts.items():
            if isinstance(script_name, str) and isinstance(script, str) and (
                script_name == "test" or script_name.startswith("test:")
            ):
                commands.append("npm test" if script_name == "test" else f"npm run {script_name}")
    if {"pyproject.toml", "pytest.ini", "setup.cfg", "setup.py"} & file_names and has_test_files:
        commands.append("pytest")
    if "go.mod" in file_names and has_test_files:
        commands.append("go test ./...")
    if "cargo.toml" in file_names and has_test_files:
        commands.append("cargo test")
    if "package.json" in file_names and has_test_files and not any(command.startswith("npm") for command in commands):
        commands.append("npm run test --if-present")
    return list(dict.fromkeys(commands))


def _repository_name(source_url: str, root: Path) -> str:
    try:
        parts = [part for part in urlparse(source_url).path.strip("/").split("/") if part]
        if len(parts) == 2:
            name = parts[-1]
            return name[:-4] if name.lower().endswith(".git") else name
    except (TypeError, ValueError):
        pass
    return root.name
