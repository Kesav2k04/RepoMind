# Three-minute judge path

RepoMind should make sense before a judge reads implementation details: it is a **verified change preflight for the next coding agent**, not a generic repository dashboard.

1. Read the [README](../README.md) hero and **Monday-morning job**. The product exists to give a coding agent the correct files, risks, and tests before its first edit.
2. Look at the [product loop](../README.md#the-product-loop). One bounded evidence pack fans out to four specialist lenses, passes through a citation firewall, and becomes an `AGENTS.md` plus a risk map.
3. Inspect [recorded orchestration](images/02-orchestration.png) and [findings](images/03-findings.png). The product shows concrete specialist activity and attaches severity, confidence, source location, reason, and recommendation to retained findings.
4. Read [what actually runs](../README.md#what-actually-runs). Native mode is four independent GPT-5.6 source specialists with function tools; the application, not a marketing prompt, launches them in parallel. A separate root only reconciles firewall-verified IDs.
5. Read [the citation firewall](../README.md#citation-firewall). A native claim must prove a path, valid line range, exact quote, and same-worker read-only-tool provenance before it reaches an artifact.
6. Try the [CLI or MCP handoff](../README.md#use-repomind). Both call the same `run_preflight()` pipeline as the dashboard, so agent-native delivery is not a mocked integration.
7. Verify [CI](https://github.com/Kesav2k04/RepoMind/actions/workflows/ci.yml). It runs backend tests plus frontend lint, tests, and build.

## Authentic checked-in evidence

The screenshots and [Flask example](examples/flask/README.md) are authentic **Evidence Mode** runs. They demonstrate the UI, artifact structure, bounded scope disclosure, and deterministic fallback. They are not evidence of a hosted GPT-5.6 run.

## What not to infer

- An absent finding is not a full-repository safety verdict. Bounded or truncated analyses are marked **partial**.
- Evidence Mode is not presented as Native GPT output.
- A public video, live URL, Devpost URL, Codex `/feedback` ID, and timestamped Native-mode capture require final human-supplied links. Until then they remain intentionally absent rather than fabricated.
