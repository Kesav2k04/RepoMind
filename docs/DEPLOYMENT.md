# Deployment guide

RepoMind is deployable as one FastAPI process that serves the built dashboard and API from the same origin. This is the intended Build Week topology: one short-lived, judge-facing demo instance with bounded analysis capacity.

## Runtime requirements

- Outbound access to public GitHub repositories.
- `git` installed in the runtime image. The included [Dockerfile](../Dockerfile) installs it.
- A writable transient clone directory.
- One persistent process for the judge session; jobs and artifacts are intentionally in-memory.

## Environment

| Variable | Demo-safe value | Purpose |
| --- | --- | --- |
| `PORT` | Platform-provided port | FastAPI listener |
| `REPOMIND_CACHE_DIR` | `/tmp/repomind/repos` | Ephemeral shallow-clone location |
| `REPOMIND_MAX_CONCURRENT_JOBS` | `2` | Bounded demo capacity |
| `REPOMIND_CLONE_TIMEOUT_SECONDS` | `120` | Clone deadline |
| `REPOMIND_GPT_TIMEOUT_SECONDS` | `45` | Native GPT deadline before fallback |
| `OPENAI_MODEL` | Provider-supported model ID | Optional hosted priority pass |
| `OPENAI_API_KEY` | Set only in host secret storage | Enables native mode |

Do not expose `OPENAI_API_KEY` in the frontend build, README, screenshots, or repository history.

## Container commands

These commands are provided for the deployment operator; they are not required for local judging.

```bash
docker build -t repomind .
docker run --rm -p 7860:7860 \
  -e REPOMIND_CACHE_DIR=/tmp/repomind/repos \
  -e REPOMIND_MAX_CONCURRENT_JOBS=2 \
  repomind
```

Open `http://localhost:7860/health`; the expected response is `{ "status": "ok", "service": "repomind" }`.

## Production preflight

1. Confirm the root URL serves the dashboard and the health endpoint succeeds.
2. Run one Flask analysis without an API key and verify the UI labels **Evidence Mode · Deterministic**.
3. If a key is configured, run one native analysis and verify the UI shows **GPT-5.6 Native · Connected** and only model-ranked validated priorities.
4. Confirm an invalid URL and capacity limit show actionable errors rather than tracebacks.
5. Record the final deployment URL in [the submission handoff](SUBMISSION_HANDOFF.md).

For a separately hosted frontend, build it with `VITE_API_BASE_URL` and configure the exact public browser origins in `REPOMIND_CORS_ORIGINS`. The same-origin container path is preferred for the Build Week demo because it removes that browser integration variable.
