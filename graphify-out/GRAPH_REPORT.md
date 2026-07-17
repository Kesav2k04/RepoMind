# Graph Report - RepoMind  (2026-07-18)

## Corpus Check
- 31 files · ~13,668 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 327 nodes · 613 edges · 17 communities (16 shown, 1 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 13 edges (avg confidence: 0.55)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `914f3e22`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- api.ts
- RepositorySnapshot
- main.py
- schemas.py
- devDependencies
- repository.py
- compilerOptions
- compilerOptions
- RepoMind
- testing.py
- plugins
- test_orchestration.py
- RepoMind — Final Locked Spec
- OpenAI Build Week Challenge Rules & Requirements
- React + TypeScript + Vite
- tsconfig.json

## God Nodes (most connected - your core abstractions)
1. `RepositorySnapshot` - 43 edges
2. `compilerOptions` - 18 edges
3. `snapshot_repository()` - 17 edges
4. `AgentReport` - 17 edges
5. `Finding` - 16 edges
6. `compilerOptions` - 15 edges
7. `orchestrate_analysis()` - 15 edges
8. `RepoMind` - 12 edges
9. `analyze()` - 11 edges
10. `analyze()` - 11 edges

## Surprising Connections (you probably didn't know these)
- `Job` --uses--> `AnalysisResult`  [INFERRED]
  main.py → schemas.py
- `run_analysis_task()` --indirect_call--> `cleanup_checkout()`  [INFERRED]
  main.py → repository.py
- `run_analysis_task()` --indirect_call--> `snapshot_repository()`  [INFERRED]
  main.py → repository.py
- `generate_agents_md()` --references--> `RepositorySnapshot`  [EXTRACTED]
  artifacts.py → repository.py
- `build_repository_map()` --references--> `RepositorySnapshot`  [EXTRACTED]
  artifacts.py → repository.py

## Import Cycles
- 1-file cycle: `workers/__init__.py -> workers/__init__.py`

## Communities (17 total, 1 thin omitted)

### Community 0 - "api.ts"
Cohesion: 0.12
Nodes (37): apiBase, ApiError, array(), createAnalysis(), endpoint(), extractArtifacts(), fetchArtifact(), getAnalysis() (+29 more)

### Community 1 - "RepositorySnapshot"
Cohesion: 0.11
Nodes (33): RepositorySnapshot, Finding, RepositoryInfo, analyze(), _boundary_finding(), _confidence(), _configuration_finding(), _contains_dependency_signal() (+25 more)

### Community 2 - "main.py"
Cohesion: 0.14
Nodes (18): BaseModel, analysis_events(), get_analysis_status(), get_artifact(), Job, publish(), FastAPI surface for RepoMind's live repository analysis., Run the analysis after the response returns so the UI can subscribe first. (+10 more)

### Community 3 - "schemas.py"
Cohesion: 0.14
Nodes (26): build_repository_map(), _finding_files(), generate_agents_md(), _purpose(), Deterministic, evidence-backed RepoMind artifacts., Create a concise AGENTS.md that contains only traceable repository guidance., _risk_by_path(), _duration_ms() (+18 more)

### Community 4 - "devDependencies"
Cohesion: 0.07
Nodes (29): dependencies, react, react-dom, devDependencies, oxlint, @types/node, @types/react, @types/react-dom (+21 more)

### Community 5 - "repository.py"
Cohesion: 0.12
Nodes (32): _cache_root(), cleanup_checkout(), clone_github_repository(), _collect_file_records(), _extract_content(), _file_priority(), _git_evidence(), _is_config_path() (+24 more)

### Community 6 - "compilerOptions"
Cohesion: 0.08
Nodes (23): compilerOptions, allowArbitraryExtensions, allowImportingTsExtensions, erasableSyntaxOnly, jsx, lib, module, moduleDetection (+15 more)

### Community 7 - "compilerOptions"
Cohesion: 0.10
Nodes (19): compilerOptions, allowImportingTsExtensions, erasableSyntaxOnly, lib, module, moduleDetection, noEmit, noFallthroughCasesInSwitch (+11 more)

### Community 8 - "RepoMind"
Cohesion: 0.11
Nodes (17): API overview, Architecture, Build Week demo flow, Configure the backend, Configure the frontend, Current scope and boundaries, Deployment and submission checklist, License (+9 more)

### Community 9 - "testing.py"
Cohesion: 0.26
Nodes (14): Pattern, analyze(), _contents_by_path(), _files_named(), _has_python_lock(), _matching_paths(), _missing_environment_template_finding(), _missing_lockfile_finding() (+6 more)

### Community 10 - "plugins"
Cohesion: 0.17
Nodes (9): plugins, rules, react/only-export-components, react/rules-of-hooks, $schema, oxc, react, typescript (+1 more)

### Community 11 - "test_orchestration.py"
Cohesion: 0.29
Nodes (7): Runtime configuration for RepoMind.  Configuration is deliberately small for the, Settings, _collect_progress(), Path, Tests for deterministic workers, artifacts, and mocked hosted reconciliation., test_native_reconciliation_uses_configured_model_and_validates_root_output(), test_orchestrate_analysis_uses_four_worker_evidence_fallback()

### Community 12 - "RepoMind — Final Locked Spec"
Cohesion: 0.25
Nodes (7): 5-DAY BUILD PLAN, OpenAI Build Week — Developer Tools Track, PROBLEM STATEMENT, RepoMind — Final Locked Spec, SOLUTION PROVIDED, TECH STACK, WHY THIS SATISFIES JUDGING CRITERIA

### Community 13 - "OpenAI Build Week Challenge Rules & Requirements"
Cohesion: 0.33
Nodes (5): GPT-5.6 Features to Leverage, Judging Criteria (Equally Weighted), Key Information, OpenAI Build Week Challenge Rules & Requirements, Submission Checklist

### Community 14 - "React + TypeScript + Vite"
Cohesion: 0.50
Nodes (3): Expanding the Oxlint configuration, React Compiler, React + TypeScript + Vite

## Knowledge Gaps
- **89 isolated node(s):** `$schema`, `typescript`, `oxc`, `react/rules-of-hooks`, `warn` (+84 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `RepositorySnapshot` connect `RepositorySnapshot` to `test_orchestration.py`, `testing.py`, `schemas.py`, `repository.py`?**
  _High betweenness centrality (0.079) - this node is a cross-community bridge._
- **Why does `snapshot_repository()` connect `repository.py` to `RepositorySnapshot`, `main.py`?**
  _High betweenness centrality (0.021) - this node is a cross-community bridge._
- **Why does `orchestrate_analysis()` connect `schemas.py` to `RepositorySnapshot`, `main.py`, `test_orchestration.py`?**
  _High betweenness centrality (0.018) - this node is a cross-community bridge._
- **What connects `$schema`, `typescript`, `oxc` to the rest of the system?**
  _89 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `api.ts` be split into smaller, more focused modules?**
  _Cohesion score 0.11517165005537099 - nodes in this community are weakly interconnected._
- **Should `RepositorySnapshot` be split into smaller, more focused modules?**
  _Cohesion score 0.10801393728222997 - nodes in this community are weakly interconnected._
- **Should `main.py` be split into smaller, more focused modules?**
  _Cohesion score 0.14333333333333334 - nodes in this community are weakly interconnected._