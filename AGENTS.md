# RepoMind agent guide

> This guide was seeded with `repomind preflight` in Evidence Mode on 2026-07-18, then reviewed for this repository. It is durable repository guidance, not a substitute for the task-specific brief produced for each run.

## Purpose

RepoMind is a read-only change-preflight service for unfamiliar public GitHub repositories. It gives a coding agent or contributor a bounded evidence pack, specialist findings, a task brief, `AGENTS.md`, and a risk-annotated map before the first edit.

## Read this first

- Read `README.md` for the user-facing promise and documented execution modes.
- Read the nearest relevant test before changing behavior; tests deliberately contain unsafe fixture snippets to exercise the scanner and are not application-risk findings by themselves.
- Preserve the evidence boundary: absence of a finding is never evidence that an unscanned path is safe.
- Keep user task input temporary. It belongs in the generated task brief, not in permanent repository instructions.

## Architecture

| Area | Responsibility |
| --- | --- |
| `main.py` | FastAPI API, in-memory demo jobs, WebSocket event stream, and same-origin dashboard serving. |
| `preflight.py` | The shared clone -> evidence -> orchestration pipeline used by the dashboard, CLI, and MCP server. Keep all three on this path. |
| `repository.py` | GitHub-only validation, bounded shallow clone, snapshot limits, and checkout cleanup. |
| `master.py` | Chooses Native GPT-5.6 mode or deterministic Evidence Mode, then builds validated artifacts. |
| `native_agents.py` | Four independent GPT-5.6 specialist calls, bounded read-only tools, and the citation firewall. |
| `worker.py` and `workers/` | Deterministic Architecture, Risk, Testing, and History fallback specialists. |
| `artifacts.py` | `AGENTS.md`, repository-map generation, and artifact validation. |
| `repomind_cli.py` / `repomind_mcp.py` | Agent-native adapters over `run_preflight()`. |
| `frontend/` | React/TypeScript dashboard. `RepoMindApp.tsx` composes the session; `api.ts` normalizes the API contract. |

## Execution and trust rules

- Native mode means the application launches four independent GPT-5.6 source specialists in parallel. A separate root may only prioritize, merge, or defer firewall-verified IDs.
- Specialists may use only the bounded read-only toolbelt: `list_files`, `read_file`, `grep`, `git_log`, and `git_blame`. Do not add arbitrary shell execution or repository writes.
- A native claim may publish only when its path exists, its line range is valid, its quote is present in that range, and the same worker read that source through a tool call. Do not relax this provenance rule.
- Model self-confidence is not evidence. Do not fabricate paths, lines, confidence, tool events, source excerpts, or completion states.
- Missing keys, provider errors, malformed output, and deadlines must finish in visibly labelled deterministic Evidence Mode. Never silently present fallback output as GPT-native.
- Evidence Mode task matching is explicit lexical overlap over retained source and verified findings, not a hidden semantic model. Keep that distinction visible in copy and behavior.
- Keep `OPENAI_MODEL` configuration-driven. Never hardcode a model name into runtime behavior.
- Security-pattern checks intentionally ignore conventional test and fixture paths for high-severity findings; fixtures often contain intentionally unsafe snippets. Do not broaden that exclusion to production paths.

## Change protocol

- Make the smallest focused change and preserve `run_preflight()` parity across API, CLI, and MCP.
- Maintain GitHub-only URL validation, clone/content/tool bounds, checkout cleanup, and safe client-facing errors.
- Update schemas, frontend normalization, UI, and tests together when the result contract changes.
- UI activity must derive from recorded progress events. Do not add timer-driven or invented agent narration.
- `info` on the repository map means informational, not safe. Preserve partial-analysis disclosure and evidence labels.
- Treat root `AGENTS.md`, README, deployment docs, MCP/CLI guidance, and submission handoff as part of the product contract when runtime behavior changes.

## Validation

Run the relevant checks before handing off a change:

```powershell
$env:PYTHONPYCACHEPREFIX = 'D:/dev-cache/pycache'
$env:TEMP = 'D:/dev-cache/tmp'
$env:TMP = 'D:/dev-cache/tmp'
python -m pytest -q

Set-Location frontend
$env:NPM_CONFIG_CACHE = 'D:/dev-cache/npm-cache'
npm run lint
npm run test
npm run build
```

For an end-to-end fallback check, run:

```powershell
repomind preflight https://github.com/pallets/flask `
  --task "Add a focused test around an error-handling change." `
  -o .\AGENTS.md
```

Use a real `OPENAI_API_KEY` only to verify Native mode. A mocked test proves contract behavior; it does not prove a live provider run.

## Local workspace hygiene

- Keep caches, clones, temporary output, and build output out of source control. Use `D:/dev-cache/` on this Windows workspace; do not direct caches to `C:/`.
- Never commit `.env`, generated artifacts, `node_modules`, `frontend/dist`, virtual environments, or local `.local/` evidence runs.
- Run the repository graph refresh after code edits when available:

```powershell
python -B -c "from graphify.watch import _rebuild_code; from pathlib import Path; _rebuild_code(Path('.'))"
```
