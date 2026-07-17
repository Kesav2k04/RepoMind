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
from urllib.parse import urlparse

from schemas import RepositoryInfo
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
CACHE_ROOT_DEFAULT = "D:/dev-cache/repomind/repos"

_GITHUB_OWNER_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37})?$")
_GITHUB_REPOSITORY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")


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

    @property
    def file_count(self) -> int:
        return len(self.files)

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

    def prompt_summary(self) -> dict[str, object]:
        return {
            "name": self.name, "commit": self.commit, "default_branch": self.default_branch,
            "file_count": self.file_count, "languages": dict(self.language_counts.most_common(8)),
            "files": self.files, "config_files": self.config_files, "test_commands": self.test_commands,
            "recent_commit_subjects": self.commit_messages, "high_churn_files": self.churn_files,
            "important_file_contents": self.important_file_contents, "source_samples": self.sampled_contents,
            "evidence_limits": {
                "max_inventory_files": MAX_FILES,
                "max_file_bytes_for_content": MAX_FILE_BYTES,
                "max_total_content_chars": MAX_EVIDENCE_CHARS,
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


async def clone_github_repository(repo_url: str) -> Path:
    """Perform a bounded shallow checkout below the configured D: cache root."""
    canonical = validate_github_url(repo_url)
    cache_root = _cache_root()
    target = Path(tempfile.mkdtemp(prefix="analysis-", dir=cache_root))
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
            timeout=settings.clone_timeout_seconds,
            check=False,
            env=environment,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        shutil.rmtree(target, ignore_errors=True)
        raise RuntimeError("Git clone did not complete within RepoMind's safety limits.") from exc
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip().replace("\n", " ")[-500:]
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
    cache_root = settings.cache_dir.expanduser().resolve()
    if cache_root.drive.upper() != "D:":
        raise RuntimeError("REPOMIND_CACHE_DIR must be located on the D: drive.")
    cache_root.mkdir(parents=True, exist_ok=True)
    return cache_root


def snapshot_repository(root: Path, source_url: str) -> RepositorySnapshot:
    """Extract deterministic evidence without following repository symlinks."""
    root = root.resolve()
    if not root.is_dir():
        raise ValueError("Repository checkout directory does not exist.")
    records = _collect_file_records(root)
    files = [relative for relative, _ in records]
    language_counts: Counter[str] = Counter()
    language_examples: dict[str, str] = {}
    for relative, _ in records:
        language = TEXT_EXTENSIONS.get(Path(relative).suffix.lower())
        if language and language != "Markdown":
            language_counts[language] += 1
            language_examples.setdefault(language, relative)
    important, sampled = _extract_content(root, records)
    messages, churn, contributors, commit, branch = _git_evidence(root)
    package = _load_package_json(root / "package.json")
    return RepositorySnapshot(
        root=root, source_url=source_url, name=_repository_name(source_url, root), commit=commit,
        default_branch=branch, files=files,
        language_counts=language_counts, language_examples=language_examples, important_file_contents=important,
        sampled_contents=sampled, config_files=[path for path in files if _is_config_path(path)][:32],
        commit_messages=messages, churn_files=churn, contributors=contributors,
        test_commands=_test_commands(package, files),
    )


def _collect_file_records(root: Path) -> list[tuple[str, int]]:
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
            except OSError:
                continue
        if len(candidates) >= MAX_DISCOVERED_FILES:
            break
    selected = sorted(candidates, key=lambda item: (_file_priority(item[0]), item[0].lower()))[:MAX_FILES]
    return sorted(selected, key=lambda item: item[0])


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


def _extract_content(root: Path, records: list[tuple[str, int]]) -> tuple[dict[str, str], dict[str, str]]:
    important: dict[str, str] = {}
    sampled: dict[str, str] = {}
    chars_used = 0
    for relative, size in sorted(records, key=lambda item: (_file_priority(item[0]), item[0].lower())):
        if size > MAX_FILE_BYTES or not _is_text_candidate(relative):
            continue
        is_important = Path(relative).name.lower() in IMPORTANT_NAMES
        content = _read_text_excerpt(
            root / relative,
            MAX_IMPORTANT_FILE_CHARS if is_important else MAX_SAMPLE_FILE_CHARS,
        )
        if content is None or chars_used + len(content) > MAX_EVIDENCE_CHARS:
            continue
        chars_used += len(content)
        sampled[relative] = content
        if is_important:
            important[relative] = content
    return important, sampled


def _is_text_candidate(relative: str) -> bool:
    return (
        Path(relative).suffix.lower() in TEXT_EXTENSIONS
        or Path(relative).name.lower() in IMPORTANT_NAMES
        or _is_config_path(relative)
    )


def _read_text_excerpt(path: Path, char_limit: int) -> str | None:
    try:
        with path.open("rb") as handle:
            data = handle.read(MAX_FILE_BYTES)
    except OSError:
        return None
    if b"\x00" in data:
        return None
    return data.decode("utf-8", errors="replace")[:char_limit]


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


def _git_evidence(root: Path) -> tuple[list[str], list[tuple[str, int]], list[str], str | None, str | None]:
    def git(*args: str) -> str:
        try:
            completed = subprocess.run(
                ["git", "-C", str(root), "--no-pager", *args],
                capture_output=True,
                text=True,
                check=False,
                timeout=GIT_TIMEOUT_SECONDS,
            )
        except (OSError, subprocess.TimeoutExpired):
            return ""
        return completed.stdout.strip() if completed.returncode == 0 else ""
    messages = [line for line in git("log", "-100", "--format=%s").splitlines() if line][:20]
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
