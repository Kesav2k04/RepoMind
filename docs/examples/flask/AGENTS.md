# AGENTS.md

## Overview

- **Repository:** flask
- **Primary observed language:** Python
- **Bounded analysis inventory:** 236 files
- **Architecture signal:** Architecture Mapper inspected 236 captured files; the primary observed language is Python. Evidence covers languages, frameworks, entry points, module boundaries, configuration.

## Architecture

- Read the nearest `AGENTS.md`, `README`, and relevant manifest before editing.
- Keep changes within the smallest relevant module boundary; trace call sites before altering behavior.
- Verify likely entry points before editing startup behavior: `src/flask/__main__.py`, `src/flask/app.py`, `src/flask/sansio/app.py`, `tests/test_apps/cliapp/app.py`, `tests/test_apps/helloworld/wsgi.py`.
- Key manifests/configuration: `.github/workflows/lock.yaml`, `.github/workflows/pre-commit.yaml`, `.github/workflows/publish.yaml`, `.github/workflows/tests.yaml`, `.github/workflows/zizmor.yaml`, `.gitignore`, `README.md`, `docs/Makefile`, `examples/celery/README.md`, `examples/celery/pyproject.toml`.
- **Analysis scope:** Partial. RepoMind retained bounded evidence only; treat unscanned or truncated files as unknown rather than safe.

## Important Files

- `src/flask/__main__.py` - Repository source or configuration.
- `src/flask/app.py` - Likely application entry point.
- `src/flask/sansio/app.py` - Likely application entry point.
- `tests/test_apps/cliapp/app.py` - Test coverage.
- `tests/test_apps/helloworld/wsgi.py` - Test coverage.
- `.github/workflows/lock.yaml` - Repository source or configuration.
- `.github/workflows/pre-commit.yaml` - Repository source or configuration.
- `.github/workflows/publish.yaml` - Repository source or configuration.
- `.github/workflows/tests.yaml` - Test coverage.
- `.github/workflows/zizmor.yaml` - Repository source or configuration.
- `.gitignore` - Repository source or configuration.
- `README.md` - Developer guidance and documentation.

## Risk Areas

- No medium-or-higher deterministic risk signal was detected; still review trust boundaries before changing them.

## Testing Strategy

- Run `pytest` when it applies to the changed area.

## Things Not to Touch

- Do not broaden changes in recent high-churn paths without reviewing nearby commits: `CHANGES.rst`, `uv.lock`, `pyproject.toml`, `.github/workflows/tests.yaml`, `.pre-commit-config.yaml`.

## Coding Conventions

- Make focused diffs; do not mix formatting-only rewrites with behavioral changes.
- Do not commit secrets, `.env` files, dependency directories, or generated build output.
- Update tests and documentation whenever public behavior or configuration changes.
- Preserve repository-local formatting and test tooling rather than introducing a parallel stack.

## Verification Checklist

- [ ] Re-read the closest entry point, manifest, and call sites affected by the change.
- [ ] Run the focused repository test command or explain why one is unavailable.
- [ ] Check changed configuration for secret exposure and dependency reproducibility.
- [ ] Update relevant tests and documentation, then inspect the final diff for unrelated changes.

## Change-Sensitive Context

- Recent high-churn paths: `CHANGES.rst`, `uv.lock`, `pyproject.toml`, `.github/workflows/tests.yaml`, `.pre-commit-config.yaml`. Review nearby history before changing them.
