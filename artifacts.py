"""Deterministic, evidence-backed RepoMind artifacts."""

from __future__ import annotations

from pathlib import PurePosixPath

from repository import RepositorySnapshot
from schemas import AgentReport, RepoNode, RepositoryMap

_RISK_ORDER = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
_RISK_LEGEND = {
    "critical": "Immediate security or correctness concern",
    "high": "Review before changing or releasing",
    "medium": "Change-sensitive or incomplete coverage signal",
    "low": "Maintainability or onboarding concern",
    "info": "Structural repository context",
}


def generate_agents_md(snapshot: RepositorySnapshot, reports: list[AgentReport]) -> str:
    """Create a concise AGENTS.md that contains only traceable repository guidance."""
    report_by_role = {report.role: report for report in reports}
    architecture = report_by_role["architecture"]
    risk = report_by_role["risk"]
    testing = report_by_role["testing"]
    history = report_by_role["history"]
    entry_points = _finding_files(architecture, "architecture-entry-point-candidates")
    high_risks = [finding for finding in risk.findings if finding.severity in {"critical", "high", "medium"}]
    churn_paths = _finding_files(history, "history-churn-paths")

    lines = [
        "# AGENTS.md",
        "",
        "## Repository overview",
        "",
        f"- **Repository:** {snapshot.name}",
        f"- **Primary observed language:** {snapshot.primary_language}",
        f"- **Bounded analysis inventory:** {snapshot.file_count} files", 
        f"- **Architecture signal:** {architecture.summary}",
        "",
        "## Navigation and architecture",
        "",
        "- Read the nearest `AGENTS.md`, `README`, and relevant manifest before editing.",
        "- Keep changes within the smallest relevant module boundary; trace call sites before altering behavior.",
    ]
    if entry_points:
        lines.append("- Verify likely entry points before editing startup behavior: " + ", ".join(f"`{path}`" for path in entry_points[:8]) + ".")
    if snapshot.config_files:
        lines.append("- Key manifests/configuration: " + ", ".join(f"`{path}`" for path in snapshot.config_files[:10]) + ".")

    lines += ["", "## Working rules", ""]
    lines += [
        "- Make focused diffs; do not mix formatting-only rewrites with behavioral changes.",
        "- Do not commit secrets, `.env` files, dependency directories, or generated build output.",
        "- Update tests and documentation whenever public behavior or configuration changes.",
        "- Preserve repository-local formatting and test tooling rather than introducing a parallel stack.",
    ]

    lines += ["", "## Risk-aware areas", ""]
    if high_risks:
        for finding in high_risks[:8]:
            locations = f" Paths: {', '.join(f'`{path}`' for path in finding.files[:4])}." if finding.files else ""
            lines.append(f"- **{finding.severity.upper()} — {finding.title}:** {finding.detail}{locations}")
    else:
        lines.append("- No medium-or-higher deterministic risk signal was detected; still review trust boundaries before changing them.")

    lines += ["", "## Test and verification", ""]
    if snapshot.test_commands:
        lines.extend(f"- Run `{command}` when it applies to the changed area." for command in snapshot.test_commands)
    else:
        lines.append("- Inspect repository documentation and manifests to select a focused verification command before merging.")
    for finding in testing.findings:
        if finding.severity in {"medium", "high", "critical"}:
            lines.append(f"- Address: {finding.title} — {finding.detail}")

    lines += ["", "## Change-sensitive context", ""]
    if churn_paths:
        lines.append("- Recent high-churn paths: " + ", ".join(f"`{path}`" for path in churn_paths[:8]) + ". Review nearby history before changing them.")
    else:
        lines.append("- Recent Git-history signals were limited; inspect local context and nearby commits before broad changes.")
    return "\n".join(lines).strip() + "\n"


def build_repository_map(snapshot: RepositorySnapshot, reports: list[AgentReport]) -> RepositoryMap:
    risk_by_path = _risk_by_path(reports)
    root_nodes: list[RepoNode] = []
    directories = sorted({PurePosixPath(path).parts[0] for path in snapshot.files if len(PurePosixPath(path).parts) > 1})
    for directory in directories[:16]:
        children_paths = [path for path in snapshot.files if path.startswith(f"{directory}/")][:10]
        child_nodes = [
            RepoNode(path=path, kind="file", purpose=_purpose(path), risk=risk_by_path.get(path, "info"))
            for path in children_paths
        ]
        directory_risk = max((child.risk for child in child_nodes), key=lambda value: _RISK_ORDER[value], default="info")
        root_nodes.append(RepoNode(path=f"{directory}/", kind="directory", purpose="Top-level repository boundary.", risk=directory_risk, children=child_nodes))
    root_nodes.extend(
        RepoNode(path=path, kind="file", purpose=_purpose(path), risk=risk_by_path.get(path, "info"))
        for path in snapshot.files if len(PurePosixPath(path).parts) == 1
    )
    markdown_lines = [f"# {snapshot.name} — risk-annotated repository map", ""]
    for node in root_nodes:
        markdown_lines.append(f"- [{node.risk.upper()}] `{node.path}` — {node.purpose}")
        markdown_lines.extend(f"  - [{child.risk.upper()}] `{child.path}` — {child.purpose}" for child in node.children)
    return RepositoryMap(
        overview=f"{snapshot.file_count} bounded-inventory files; primary observed language: {snapshot.primary_language}.",
        nodes=root_nodes,
        risk_legend=_RISK_LEGEND,
        markdown="\n".join(markdown_lines) + "\n",
    )


def _risk_by_path(reports: list[AgentReport]) -> dict[str, str]:
    result: dict[str, str] = {}
    for report in reports:
        for finding in report.findings:
            for path in finding.files:
                current = result.get(path, "info")
                if _RISK_ORDER[finding.severity] > _RISK_ORDER[current]:
                    result[path] = finding.severity
    return result


def _finding_files(report: AgentReport, identifier: str) -> list[str]:
    return [path for finding in report.findings if finding.id == identifier for path in finding.files]


def _purpose(path: str) -> str:
    name = PurePosixPath(path).name.lower()
    if name in {"readme.md", "agents.md"}:
        return "Developer guidance and documentation"
    if "test" in name or "/tests/" in f"/{path.lower()}":
        return "Test coverage"
    if name in {"package.json", "pyproject.toml", "requirements.txt", "go.mod", "cargo.toml"}:
        return "Dependency or build manifest"
    if name.startswith(("main.", "app.", "server.", "index.")):
        return "Likely application entry point"
    return "Repository source or configuration"
