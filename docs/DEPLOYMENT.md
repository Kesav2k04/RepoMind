# Deployment guide

RepoMind is designed for one judge-facing FastAPI process that serves the compiled dashboard and API from the same origin. This intentionally avoids a separate frontend CORS failure during a Build Week demo.

## Runtime requirements

- Outbound access to public GitHub repositories.
- `git` installed in the runtime image.
- A writable transient clone directory.
- One persistent process for the judge session. Jobs and dashboard artifacts are intentionally in-memory in this MVP.

## Environment

| Variable | Demo-safe value | Purpose |
| --- | --- | --- |
| `PORT` | Platform-provided | FastAPI listener |
| `REPOMIND_CACHE_DIR` | `/tmp/repomind/repos` | Ephemeral shallow-clone location |
| `REPOMIND_MAX_CONCURRENT_JOBS` | `2` | Bounds a single demo instance |
| `REPOMIND_CLONE_TIMEOUT_SECONDS` | `120` | Clone deadline |
| `REPOMIND_GPT_TIMEOUT_SECONDS` | `45` | Native GPT deadline before Evidence Mode fallback |
| `OPENAI_MODEL` | Provider-supported model ID | Model used by Native-mode source specialists and root |
| `OPENAI_API_KEY` | Host secret only | Enables Native mode |
| `REPOMIND_CORS_ORIGINS` | Exact public frontend origins | Needed only for a separately hosted frontend |

Never expose `OPENAI_API_KEY` in a frontend build, screenshot, log, README, or repository history.

## Container commands

These commands are for the deployment operator, not a required local test. The image builds the Vite dashboard, includes the shared preflight and native-specialist modules, and serves the frontend and API on one origin.

```bash
docker build -t repomind .
docker run --rm -p 7860:7860 \
  -e REPOMIND_CACHE_DIR=/tmp/repomind/repos \
  -e REPOMIND_MAX_CONCURRENT_JOBS=2 \
  repomind
```

Open `http://localhost:7860/health`. The expected response is `{ "status": "ok", "service": "repomind" }`.

## Judge-demo preflight

1. Confirm the root URL serves the dashboard and `/health` succeeds.
2. Run a prepared public-repository analysis with no API key and verify the UI shows **Evidence Mode** with an honest fallback note.
3. If a key is configured, run one Native-mode analysis and verify it visibly shows four GPT-5.6 specialists, source-tool events, firewall totals, and root reconciliation.
4. Confirm an invalid URL and demo-capacity limit return actionable errors rather than tracebacks.
5. Download both artifacts and use the CLI or MCP server once against the same repository.
6. Record the deployment URL in [the submission handoff](SUBMISSION_HANDOFF.md) only after this path works outside the local network.

## Separate frontend deployments

The container path is preferred. If a platform requires a separate static frontend, build it with `VITE_API_BASE_URL` and set the exact browser origin in `REPOMIND_CORS_ORIGINS`. Verify a real browser request before recording; a healthy API alone does not prove the browser can call it.
