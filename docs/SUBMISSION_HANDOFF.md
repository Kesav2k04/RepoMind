# RepoMind submission handoff

This is the single source of truth for Build Week fields that must be supplied by a human after they are publicly verifiable. Do not replace a placeholder with an estimate, a localhost address, or a claim that cannot be demonstrated.

## Required insertion points

| Field | Insert only after it exists |
| --- | --- |
| Public project video | `REPLACE_WITH_YOUTUBE_URL` |
| Judge-testable live demo | `REPLACE_WITH_DEPLOYMENT_URL` |
| Devpost project | `REPLACE_WITH_DEVPOST_URL` |
| Primary Codex `/feedback` session | `REPLACE_WITH_SESSION_ID` |
| Country of residence | `REPLACE_WITH_COUNTRY` |

## Ready-to-paste project copy

**Project name:** RepoMind

**Tagline:** Give the next coding agent a cited change preflight, not a blind first edit.

**Category:** Developer Tools

**Description:** RepoMind is a change-preflight agent for the moment before a coding agent or contributor edits an unfamiliar repository. A user supplies a public GitHub repository and the change they intend to make. RepoMind builds one bounded, read-only evidence pack, runs Architecture, Risk, Testing, and History specialists in parallel, and returns a task-scoped brief, a verified `AGENTS.md`, and a risk-annotated repository map.

In Native mode, RepoMind launches four independent GPT-5.6 source specialists with bounded read-only tools (`list_files`, `read_file`, `grep`, `git_log`, and `git_blame`). A separate GPT-5.6 root can prioritize, merge, or defer only the findings that survive the citation firewall. A model claim is withheld unless its path, line range, quoted source, and same-worker tool provenance all validate against the bounded checkout. Model confidence is not trusted; retained confidence is citation-derived. The model cannot invent findings, locations, confidence values, or artifact text.

When OpenAI credentials are absent, slow, or invalid, RepoMind visibly completes in deterministic Evidence Mode. It is a useful fallback, but it is not represented as native GPT output. The CLI and stdio MCP server use the same `run_preflight()` path as the dashboard, letting Codex, Cursor, Claude Code, and humans consume the same reviewed handoff before a change.

RepoMind does not write the fix or replace an IDE. It removes the repeated orientation work that causes agents to touch the wrong files, miss risks, or discover the relevant tests late.

## Native GPT-5.6 evidence record

Complete this only after a real successful Native-mode run is visible in the product. Do not reuse deterministic screenshots.

| Field | Verified value |
| --- | --- |
| `OPENAI_MODEL` reported by the app | `REPLACE_AFTER_SUCCESSFUL_NATIVE_RUN` |
| Execution mode reported by the app | `REPLACE_AFTER_SUCCESSFUL_NATIVE_RUN` |
| UTC timestamp | `REPLACE_AFTER_SUCCESSFUL_NATIVE_RUN` |
| Non-sensitive job identifier | `REPLACE_AFTER_SUCCESSFUL_NATIVE_RUN` |
| Screenshot or video timestamp | `REPLACE_AFTER_SUCCESSFUL_NATIVE_RUN` |
| Source tools visibly used | `REPLACE_AFTER_SUCCESSFUL_NATIVE_RUN` |
| Firewall totals: proposed / verified / withheld | `REPLACE_AFTER_SUCCESSFUL_NATIVE_RUN` |
| Root action shown | `Priority / merge / defer over verified finding IDs only` |

## Required disclosures

- Codex was used during development for architecture review, implementation, validation, UI QA, and release preparation.
- Native mode is an application-orchestrated master/worker flow: four independent GPT-5.6 source specialists plus a separate GPT-5.6 root reconciliation call.
- The source specialists use bounded read-only function tools. The root cannot generate factual claims or artifact text.
- Evidence Mode uses deterministic local specialists and must never be labelled as GPT-native output.
- RepoMind accepts public GitHub HTTPS repositories only and never writes back to the analyzed repository.
- Jobs and dashboard artifacts are in-memory in this Build Week MVP; use the single-instance deployment topology described in `docs/DEPLOYMENT.md`.

## Final checks

- [ ] The video is public, under three minutes, and includes audio explaining both Codex and GPT-5.6.
- [ ] The video shows an actual Native-mode tool trace and firewall result, not a simulated progress state.
- [ ] The live URL opens without local setup and completes a prepared public-repository analysis.
- [ ] The CLI or MCP handoff is shown so the product closes the loop with a coding agent.
- [ ] The repository, CI, video, live demo, session ID, and Devpost links agree across README and Devpost.
- [ ] A real Native-mode run has been captured before any native GPT claim is made.
- [ ] Evidence Mode is described accurately as a deterministic fallback.
