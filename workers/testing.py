"""Evidence-first test coverage analysis for RepoMind.

This worker intentionally provides triage, not measured line coverage.  It
uses only the bounded repository inventory and excerpts produced by
``snapshot_repository`` so that its findings remain explainable and safe to
hand to the reconciliation agent.
"""

from __future__ import annotations

from pathlib import PurePosixPath

from repository import RepositorySnapshot
from schemas import AgentReport, Finding


_SOURCE_SUFFIXES = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".c", ".cc", ".cpp",
    ".cs", ".go", ".java", ".kt", ".kts", ".php", ".rb", ".rs", ".swift",
}
_TEST_DIRECTORY_NAMES = {"test", "tests", "__tests__", "spec", "specs"}
_FRAMEWORK_SIGNALS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("pytest", ("pytest",)),
    ("unittest", ("unittest",)),
    ("Jest", ("jest",)),
    ("Vitest", ("vitest",)),
    ("Playwright", ("@playwright/test", "playwright")),
    ("Cypress", ("cypress",)),
    ("Mocha", ("mocha",)),
    ("RSpec", ("rspec",)),
    ("Go testing", ("go test", "testing.t")),
    ("Cargo test", ("cargo test", "#[test]")),
)


def analyze(snapshot: RepositorySnapshot) -> AgentReport:
    """Return bounded test-discovery and test-to-source triage findings.

    A source/test file count is deliberately labelled as triage rather than
    coverage: line and branch coverage require executing a repository's test
    suite, which this worker never does.
    """
    test_files = [path for path in snapshot.files if _is_test_path(path)]
    source_files = [
        path
        for path in snapshot.files
        if _is_source_path(path) and not _is_test_path(path)
    ]
    framework_names = _frameworks(snapshot, test_files)
    evidence_files = _dedupe(test_files[:6] + _test_configuration_files(snapshot)[:4])
    findings: list[Finding] = []

    if test_files:
        findings.append(
            Finding(
                id="testing-test-inventory",
                category="test_inventory",
                title="Conventional test files were discovered",
                detail=(
                    f"RepoMind found {len(test_files)} conventional test file(s) in the "
                    f"bounded repository inventory."
                ),
                severity="info",
                files=test_files[:8],
                recommendation="Use the discovered tests as the first verification path when changing related code.",
            )
        )
    elif source_files:
        findings.append(
            Finding(
                id="testing-no-conventional-tests",
                category="test_gap",
                title="No conventional test files were found",
                detail=(
                    f"RepoMind found {len(source_files)} source file(s) but no files in conventional "
                    "test locations or names in the bounded inventory."
                ),
                severity="medium",
                files=source_files[:8],
                recommendation="Add a focused test suite for the highest-impact entry points before broad refactoring.",
            )
        )

    if framework_names and evidence_files:
        findings.append(
            Finding(
                id="testing-framework-signals",
                category="test_framework",
                title="Test framework signals detected",
                detail=f"Evidence indicates these test frameworks or runners: {', '.join(framework_names)}.",
                severity="info",
                files=evidence_files,
                recommendation="Prefer the existing test tooling and commands when adding coverage.",
            )
        )

    if snapshot.test_commands and evidence_files:
        findings.append(
            Finding(
                id="testing-discovered-commands",
                category="test_command",
                title="Repository test command candidates are available",
                detail="Configured or convention-derived test commands: " + ", ".join(snapshot.test_commands) + ".",
                severity="info",
                files=evidence_files,
                recommendation="Run the applicable command before and after modifying tested behavior.",
            )
        )
    elif test_files:
        findings.append(
            Finding(
                id="testing-no-command-candidate",
                category="test_command",
                title="Test files exist without a detected project test command",
                detail=(
                    "Conventional test files were found, but the bounded manifest/configuration evidence "
                    "did not yield a runnable project-level test command."
                ),
                severity="low",
                files=_dedupe(test_files[:6] + _test_configuration_files(snapshot)[:2]),
                recommendation="Document a single project-level test command in the relevant manifest or contributor guide.",
            )
        )

    if source_files and test_files:
        source_count = len(source_files)
        test_count = len(test_files)
        ratio = test_count / source_count
        if source_count >= 8 and ratio < 0.15:
            findings.append(
                Finding(
                    id="testing-low-test-to-source-triage",
                    category="coverage_triage",
                    title="Test-to-source inventory ratio merits coverage triage",
                    detail=(
                        f"The bounded inventory contains {test_count} test file(s) and {source_count} source "
                        f"file(s) ({ratio:.0%} by file count). This is not measured line or branch coverage."
                    ),
                    severity="low",
                    files=_dedupe(test_files[:4] + source_files[:4]),
                    recommendation="Prioritize tests for public entry points and change-prone source modules, then measure coverage in CI.",
                )
            )

    summary_parts = [
        f"Found {len(test_files)} conventional test file(s)",
        f"across {len(source_files)} source file(s)",
    ]
    if framework_names:
        summary_parts.append("framework signals: " + ", ".join(framework_names))
    elif test_files:
        summary_parts.append("no framework signal was identified from bounded evidence")
    if not source_files and not test_files:
        summary_parts = ["No conventional source or test files were available in the bounded inventory"]

    return AgentReport(
        role="testing",
        label="Test Coverage Analyst",
        summary="; ".join(summary_parts) + ".",
        findings=findings,
        confidence=_confidence(source_files, test_files, framework_names, snapshot.test_commands),
        evidence_count=len(_dedupe(test_files + source_files + _test_configuration_files(snapshot))),
    )


def _is_test_path(path: str) -> bool:
    candidate = PurePosixPath(path)
    parent_names = {part.lower() for part in candidate.parts[:-1]}
    name = candidate.name.lower()
    return (
        bool(parent_names & _TEST_DIRECTORY_NAMES)
        or name.startswith("test_")
        or name.endswith("_test.py")
        or ".test." in name
        or ".spec." in name
    )


def _is_source_path(path: str) -> bool:
    return PurePosixPath(path).suffix.lower() in _SOURCE_SUFFIXES


def _test_configuration_files(snapshot: RepositorySnapshot) -> list[str]:
    names = {
        "package.json", "pyproject.toml", "pytest.ini", "setup.cfg", "setup.py",
        "jest.config.js", "jest.config.ts", "vite.config.ts", "playwright.config.ts",
        "cypress.config.ts", "go.mod", "cargo.toml",
    }
    return [path for path in snapshot.files if PurePosixPath(path).name.lower() in names]


def _frameworks(snapshot: RepositorySnapshot, test_files: list[str]) -> list[str]:
    bounded_text = "\n".join(
        [snapshot.combined_config, snapshot.combined_test_content, "\n".join(snapshot.test_commands)]
    ).lower()
    discovered: list[str] = []
    for name, signals in _FRAMEWORK_SIGNALS:
        if any(signal in bounded_text for signal in signals):
            discovered.append(name)
    if test_files and any(PurePosixPath(path).suffix == ".go" for path in test_files):
        if "Go testing" not in discovered:
            discovered.append("Go testing")
    return discovered


def _confidence(
    source_files: list[str],
    test_files: list[str],
    framework_names: list[str],
    test_commands: list[str],
) -> float:
    evidence_points = int(bool(source_files)) + int(bool(test_files))
    evidence_points += int(bool(framework_names)) + int(bool(test_commands))
    return min(0.95, 0.45 + evidence_points * 0.12)


def _dedupe(paths: list[str]) -> list[str]:
    return list(dict.fromkeys(path for path in paths if path))
