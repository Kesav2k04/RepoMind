# RepoMind — Devpost Submission Pack

Use this document to complete the OpenAI Build Week Devpost entry accurately. It contains ready-to-paste project text, verified repository assets, and the remaining user-supplied fields. Do not submit until the three required placeholders below contain real values.

## Project metadata

- **Name:** RepoMind — Context Before Code
- **Tagline:** Evidence-backed repository context for people and coding agents.
- **Category:** Developer Tools
- **Repository:** https://github.com/Kesav2k04/RepoMind
- **License:** MIT
- **Built with:** Python, FastAPI, React, TypeScript, Vite, WebSockets, Git, OpenAI API, GPT-5.6, Codex

## Required before submission

- **Public YouTube video (<3 minutes, with audio):** `REPLACE_WITH_PUBLIC_YOUTUBE_URL`
- **Primary Codex `/feedback` session ID:** `REPLACE_WITH_REAL_SESSION_ID`
- **Country of residence:** `REPLACE_WITH_YOUR_COUNTRY`
- **Judge-testable deployment URL (recommended for this developer tool):** `REPLACE_WITH_DEPLOYED_URL`

Never replace these values with placeholders, estimates, or a generated URL in Devpost.

## Description

### Context before code

Coding agents and new contributors often begin with incomplete repository context. They need to rediscover architecture, conventions, risky paths, tests, and recent change history while already making changes. RepoMind gives the next human or coding agent an evidence-backed briefing before that first edit.

Enter a public GitHub HTTPS URL and RepoMind creates two reusable artifacts:

- `AGENTS.md` with repository-specific architecture, important files, risk areas, testing signals, coding conventions, and a verification checklist.
- An interactive, risk-annotated repository map for navigating where to work carefully.

RepoMind makes the journey visible: a bounded shallow clone becomes an evidence pack; Architecture, Risk, Testing, and History specialists review it in parallel; a Master reconciles their signals; then validated artifacts are rendered and downloadable.

Every published finding shows severity, confidence, recommendation, and source evidence. RepoMind explicitly marks a scan as partial when a discovery, file-selection, or evidence budget is reached, so the absence of a finding is never presented as proof that a repository is safe.

### Technical implementation

The dashboard uses React, TypeScript, and Vite. A FastAPI backend creates a bounded shallow Git clone, collects a deterministic evidence snapshot, runs four read-only specialist workers concurrently, and streams progress over WebSocket events.

Canonical findings and artifacts remain deterministic and evidence-validated. Unsupported paths, line numbers, severities, and claims are withheld instead of being presented as trusted context.

When `OPENAI_API_KEY` is configured, GPT-5.6’s Multi-agent capability is used only for the Master reconciliation of the bounded specialist inventory. The response is constrained to prioritizing known finding IDs; canonical artifacts remain evidence-generated. When the key is unavailable, the provider is slow, or output fails validation, RepoMind visibly switches to **Evidence Mode · Deterministic** rather than pretending that model output was used.

### Codex and GPT-5.6

Codex accelerated the implementation, testing, refinement, visual polish, and review of RepoMind. It is not a hidden runtime dependency.

GPT-5.6 is a narrowly scoped, optional runtime collaborator for Master reconciliation. The evidence layer remains authoritative so the product stays attributable and useful even if the hosted provider is unavailable.

### How judges can test it

See the root README for setup, deployment configuration, supported platforms, environment variables, validation commands, and the three-minute demo script. Start with a public GitHub repository such as `https://github.com/fastapi/fastapi`.

## Video narration

Use the three-minute script in the README. Record the actual UI and state the mode truthfully:

- Say **GPT-5.6 Native · Connected** only when a live native run visibly completes.
- Otherwise say **Evidence Mode · Deterministic** and show the fallback label.
- The audio must explicitly cover how Codex helped build the project and how GPT-5.6 is used at runtime.

## Screenshot inventory

All screenshots are authentic local Playwright captures of a completed fallback analysis of FastAPI. They must not be relabelled as a GPT-connected run.

| Asset | Evidence shown |
| --- | --- |
| `docs/images/01-home.png` | Value proposition, before/after story, and public-repository entry point. |
| `docs/images/02-orchestration.png` | Evidence pack, four visible specialists, pipeline, and live execution state. |
| `docs/images/03-findings.png` | Evidence-backed specialist findings with confidence, severity, location, reason, and recommendation. |
| `docs/images/04-reconciliation.png` | Master decisions: accepted, merged, and deferred. |
| `docs/images/05-artifacts.png` | Structured AGENTS.md and interactive risk map. |
| `docs/images/06-complete.png` | Full end-to-end finished experience and bounded-analysis disclosure. |
