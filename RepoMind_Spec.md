# RepoMind — Final Locked Spec
## OpenAI Build Week — Developer Tools Track

**Dates:** July 16 (Current). Submission closes July 21, 5pm PT.

## PROBLEM STATEMENT
Every AI coding agent works better on a repo when it has a well-written `AGENTS.md` — a file describing conventions, architecture, danger zones, and test practices. Writing a good one requires reading the whole codebase from several angles at once (architecture, dependency risk, test coverage, history). This is exactly when to use Codex/GPT-5.6 multi-agent mode: "exploring separate parts of a large codebase."

## SOLUTION PROVIDED
**RepoMind**: Point it at any GitHub repo. A root agent spawns four bounded, parallel subagents, each reading the *same* codebase through a different lens:
1. **Architecture Mapper** — entry points, module boundaries, data flows.
2. **Risk Auditor** — fragile dependencies, unhandled edge cases.
3. **Test Coverage Analyst** — tested vs untested code, flaky tests.
4. **History Archaeologist** — mines commit messages and PR descriptions for tribal knowledge.

The root agent reconciles findings and produces:
- **`AGENTS.md`** — ready to drop into the repo for an agent to consume.
- **A risk-annotated repo map** — human-readable presentation of findings.

## WHY THIS SATISFIES JUDGING CRITERIA
- **Technological Implementation:** Uses genuine Codex/GPT-5.6 multi-agent primitives in parallel, not just API calls. Reconciliation step is non-trivial. Output is a native Codex concept.

## TECH STACK
- **Backend**: Python 3.11 + FastAPI, OpenAI Agents SDK / Codex SDK, GitHub API. No database.
- **Frontend**: Single-page React app (WebSocket for live progress).

## 5-DAY BUILD PLAN
- **Day 1:** Root agent + subagent scaffolding. Architecture Mapper working end-to-end.
- **Day 2:** Remaining 3 subagents. Parallel execution confirmed.
- **Day 3:** Reconciliation logic + `AGENTS.md` generation. (Cut History Archaeologist if behind).
- **Day 4:** Frontend, connect to backend.
- **Day 5:** Final demo repo, record video, write README, get `/feedback` session ID, submit.
