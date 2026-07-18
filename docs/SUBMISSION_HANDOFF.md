# RepoMind submission handoff

This file is the single source for final human-supplied Build Week submission fields. Do not replace a placeholder with an estimate, local-only URL, or a claim that cannot be verified publicly.

## Required insertion points

| Field | Value to insert before submission |
| --- | --- |
| Public project video | `REPLACE_WITH_YOUTUBE_URL` |
| Judge-testable live demo | `REPLACE_WITH_DEPLOYMENT_URL` |
| Devpost project | `REPLACE_WITH_DEVPOST_URL` |
| Primary Codex `/feedback` session | `REPLACE_WITH_SESSION_ID` |
| Country of residence | `REPLACE_WITH_COUNTRY` |

## Ready-to-paste project copy

**Project name:** RepoMind

**Tagline:** Before an AI edits unfamiliar code, give it the repository's rules.

**Category:** Developer Tools

**Description:** RepoMind is a change preflight for the moment before a coding agent starts work in an unfamiliar repository. It turns a public GitHub repository into an evidence-backed operating brief: what to read first, where risk sits, what tests matter, and how to verify the change. It creates one bounded evidence pack, lets Architecture, Risk, Testing, and History specialists examine that shared evidence in parallel, then produces a structured `AGENTS.md` and an interactive risk-annotated repository map. Every published finding carries a severity, evidence location, reason, recommendation, confidence, and explicit analysis scope.

RepoMind does not write the ticket fix or replace an IDE. A contributor reviews and can commit its Markdown handoff, then uses that shared repository context in Cursor, Codex, Copilot, or another coding workflow. That portable, evidence-backed handoff—not a standalone dashboard—is the product's durable value.

RepoMind is deliberately conservative: deterministic repository evidence remains authoritative, and partial scans are marked as partial. When configured, GPT-5.6 performs a constrained Master priority pass over already validated finding IDs. It cannot introduce source claims or modify canonical artifacts; if unavailable, the product visibly completes in Evidence Mode.

## Native GPT-5.6 evidence record

Complete this only after a real successful native-mode run is visible in the product. Do not reuse deterministic screenshots.

| Field | Verified value |
| --- | --- |
| `OPENAI_MODEL` reported by the app | `REPLACE_AFTER_SUCCESSFUL_NATIVE_RUN` |
| Execution mode reported by the app | `REPLACE_AFTER_SUCCESSFUL_NATIVE_RUN` |
| UTC timestamp | `REPLACE_AFTER_SUCCESSFUL_NATIVE_RUN` |
| Non-sensitive job identifier | `REPLACE_AFTER_SUCCESSFUL_NATIVE_RUN` |
| Screenshot or video timestamp | `REPLACE_AFTER_SUCCESSFUL_NATIVE_RUN` |
| What GPT changed | `Presentation priority over existing validated findings only` |

## Required disclosures

- Codex was used during development for review, implementation, validation, UI QA, and release preparation.
- The four canonical specialists are deterministic bounded analyses, not hosted repository-browsing agents.
- The hosted GPT-5.6 call is optional and constrained to model-ranked presentation priorities over deterministic finding IDs.
- Evidence Mode screenshots must never be labelled as native GPT output.
- RepoMind accepts public GitHub HTTPS repositories only and never writes back to the analyzed repository.

## Final checks

- [ ] The video is public, under three minutes, and has audio explaining both Codex and GPT-5.6.
- [ ] The live URL opens without local setup and completes a prepared public-repository analysis.
- [ ] The repository, CI, video, live demo, session ID, and Devpost links agree across README and Devpost.
- [ ] A real native-mode run has been captured before any native GPT claim is made.
- [ ] The deterministic fallback is shown or described accurately.
