# RepoMind submission handoff

This file is the source of truth for final Build Week fields. Add an external artifact only after it is public, correct, and independently opened. Never replace a missing fact with a localhost URL, estimate, or unverified claim.

## Known project links

| Item | Verified link |
| --- | --- |
| Source repository | [github.com/Kesav2k04/RepoMind](https://github.com/Kesav2k04/RepoMind) |
| Devpost project | [repomind-context-before-code](https://devpost.com/software/repomind-context-before-code) |
| CI | [GitHub Actions](https://github.com/Kesav2k04/RepoMind/actions/workflows/ci.yml) |
| Submission rules | [OpenAI Build Week rules](https://openai.devpost.com/rules) |
| Devpost thumbnail | [1500 by 1000 PNG](assets/repomind-devpost-thumbnail.png), prepared from a real Evidence Mode capture with a GPT Image 2 background. |

## Creator-supplied final artifacts

| Field | Add only after verification |
| --- | --- |
| Public project video | `REPLACE_WITH_YOUTUBE_URL` |
| Judge-testable live demo | `REPLACE_WITH_DEPLOYMENT_URL` |
| Primary Codex `/feedback` session | `REPLACE_WITH_SESSION_ID` |
| Native-mode evidence record | Complete the table below after a real successful run. |

Select the creator's actual country of residence in Devpost. Do not copy a guessed value from this repository.

## Ready-to-paste project copy

**Project name:** RepoMind

**Tagline:** Give coding agents cited context before the first edit.

**Category:** Developer Tools

**Description:** RepoMind is a task-first repository preflight for the moment before a coding agent or contributor changes unfamiliar code. Give it a public GitHub repository and a specific change. It returns a cited task brief with files to inspect, risk boundaries to respect, and observed checks to run, plus a structured `AGENTS.md` and evidence-aware repository map.

The product addresses the orientation tax: the exploratory work that consumes context while an agent searches for entry points, conventions, fragile boundaries, and tests. RepoMind does not replace an IDE or write the patch. It gives the next editor reviewable context before the patch so Codex, Cursor, Claude Code, or a human contributor can make a safer first plan.

In GPT-5.6 Native mode, the application launches four independent source specialists for Architecture, Risk, Testing, and History. They can use only bounded read-only tools: `list_files`, `read_file`, `grep`, `git_log`, and `git_blame`. A separate GPT-5.6 root can prioritize, merge, or defer only the finding IDs that pass the citation firewall. RepoMind withholds a Native claim unless its path, line range, quoted source, and same-worker tool provenance validate against the bounded checkout.

If credentials are absent, slow, or invalid, RepoMind visibly completes in deterministic Evidence Mode. This fallback uses bounded local specialists and transparent lexical task matching. It is useful but never presented as Native output. The dashboard, CLI, and stdio MCP server share the same `run_preflight()` pipeline, so the handoff enters a real coding workflow rather than a separate demo path.

## Native GPT-5.6 evidence record

Complete this only after a real successful Native-mode run is visible in the product. Do not reuse deterministic screenshots or mocked tests.

| Field | Verified value |
| --- | --- |
| `OPENAI_MODEL` reported by the app | `REPLACE_AFTER_SUCCESSFUL_NATIVE_RUN` |
| Execution mode reported by the app | `REPLACE_AFTER_SUCCESSFUL_NATIVE_RUN` |
| UTC timestamp | `REPLACE_AFTER_SUCCESSFUL_NATIVE_RUN` |
| Non-sensitive job identifier | `REPLACE_AFTER_SUCCESSFUL_NATIVE_RUN` |
| Screenshot or video timestamp | `REPLACE_AFTER_SUCCESSFUL_NATIVE_RUN` |
| Source tools visibly used | `REPLACE_AFTER_SUCCESSFUL_NATIVE_RUN` |
| Firewall totals: proposed / verified / withheld | `REPLACE_AFTER_SUCCESSFUL_NATIVE_RUN` |
| Root action shown | `Priority, merge, or defer over verified finding IDs only` |

## Required disclosures

- Codex supported repository exploration, architecture review, implementation, test design, failure-mode review, UI QA, release validation, and documentation during development.
- Native mode is an application-orchestrated master and worker flow: four independent GPT-5.6 source specialists plus a separate GPT-5.6 root reconciliation call.
- Source specialists use bounded read-only function tools. The root cannot generate factual claims or artifact text.
- Evidence Mode uses deterministic local specialists and must never be labelled as GPT-native output.
- RepoMind accepts public GitHub HTTPS repositories only and never writes back to the analyzed repository.
- Jobs and dashboard artifacts are in-memory in this Build Week MVP. Use the single-instance deployment topology in [DEPLOYMENT.md](DEPLOYMENT.md).

## Final checks

- [ ] The video is public, under three minutes, and includes audio explaining both Codex and GPT-5.6.
- [ ] The video shows real product behavior and an actual Native-mode tool trace and firewall result if Native claims are made.
- [ ] The live URL opens without local setup and completes a prepared public-repository analysis.
- [ ] The CLI or MCP handoff is shown so the product closes the loop with a coding agent.
- [ ] The repository, CI, video, live demo, session ID, and Devpost links agree across README and Devpost.
- [ ] A real Native-mode run has been captured before any Native GPT claim is made.
- [ ] Evidence Mode is described accurately as a deterministic fallback.
