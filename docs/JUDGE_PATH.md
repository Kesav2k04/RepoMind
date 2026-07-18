# Three-minute judge path

RepoMind should make sense before a judge reads implementation details. It is a cited change preflight for the next coding agent, not another repository dashboard.

## First 30 seconds: the product outcome

1. Read the [README opening](../README.md#why-repomind-exists). The problem is the orientation tax: coding agents waste context locating files, conventions, risks, and checks before the first edit.
2. Open the dashboard screenshot and notice the task input. RepoMind is designed for a concrete change, such as an auth fix or focused test, not broad codebase chat.
3. Read the [task-first handoff](../README.md#why-repomind-exists): cited files to inspect, risk boundaries, observed validation, `AGENTS.md`, and an evidence-aware map.

## Next 90 seconds: verify the technical claim

4. View the [product loop](../README.md#the-product-loop). One bounded evidence pack fans out to Architecture, Risk, Testing, and History specialists, then passes through the citation firewall.
5. Inspect [recorded orchestration](images/02-orchestration.png) and [findings](images/03-findings.png). Retained findings show source location, confidence, reason, and recommendation. Activity comes from recorded progress events, not timers.
6. Read [Execution modes](../README.md#execution-modes). In Native mode, the application launches four independent GPT-5.6 source specialists with bounded function tools and a separate root that reconciles verified IDs only.
7. Read [the citation firewall](../README.md#the-citation-firewall). A Native claim needs a real path, valid line range, exact quote, and same-worker read-only-tool provenance before it reaches an artifact.

## Final minute: verify the handoff and the boundary

8. Open the [Flask example](examples/flask/README.md), its generated [AGENTS.md](examples/flask/AGENTS.md), and [repository map](examples/flask/repository-map.md). These are authentic local Evidence Mode artifacts.
9. Try the [CLI or MCP handoff](../README.md#use-repomind-in-the-coding-loop). Both call the same `run_preflight()` pipeline as the dashboard.
10. Verify [CI](https://github.com/Kesav2k04/RepoMind/actions/workflows/ci.yml). It runs backend tests plus frontend lint, tests, and production build.

## What not to infer

- Evidence Mode is not Native GPT-5.6 output. The checked-in screenshots and Flask example demonstrate the UI, artifact shape, bounded scope disclosure, and deterministic fallback only.
- An absent finding is not a full-repository safety verdict. Bounded or truncated analyses are marked **partial**.
- RepoMind prepares cited context. It does not write the fix, replace an IDE, or guarantee that a change is correct.
- The public video, live URL, Codex `/feedback` ID, and timestamped Native-mode record remain creator-supplied proof until real links exist. See [SUBMISSION_HANDOFF.md](SUBMISSION_HANDOFF.md).
