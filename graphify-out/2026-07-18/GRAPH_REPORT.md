# Graph Report - RepoMind  (2026-07-18)

## Corpus Check
- 33 files · ~23,139 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 516 nodes · 1114 edges · 20 communities (19 shown, 1 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 30 edges (avg confidence: 0.54)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `5c3d9393`
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
- test_repository.py
- plugins
- RepositorySnapshot
- RepoMind — Final Locked Spec
- OpenAI Build Week Challenge Rules & Requirements
- React + TypeScript + Vite
- tsconfig.json
- artifacts.py
- AgentReport
- worker.py

## God Nodes (most connected - your core abstractions)
1. `RepositorySnapshot` - 64 edges
2. `AgentReport` - 27 edges
3. `snapshot_repository()` - 24 edges
4. `orchestrate_analysis()` - 23 edges
5. `Finding` - 20 edges
6. `compilerOptions` - 18 edges
7. `analyze()` - 18 edges
8. `evidence_paths()` - 17 edges
9. `RepoMind` - 17 edges
10. `bounded_confidence()` - 16 edges

## Surprising Connections (you probably didn't know these)
- `Job` --uses--> `AnalysisResult`  [INFERRED]
  main.py → schemas.py
- `_run_analysis()` --indirect_call--> `snapshot_repository()`  [INFERRED]
  main.py → repository.py
- `RepositorySnapshot` --uses--> `EvidenceLocation`  [INFERRED]
  repository.py → schemas.py
- `RepositorySnapshot` --uses--> `RepositoryInfo`  [INFERRED]
  repository.py → schemas.py
- `WorkerUpdate` --uses--> `RepositorySnapshot`  [INFERRED]
  workers/_shared.py → repository.py

## Import Cycles
- 1-file cycle: `workers/__init__.py -> workers/__init__.py`

## Communities (20 total, 1 thin omitted)

### Community 0 - "api.ts"
Cohesion: 0.06
Nodes (78): apiBase, ApiError, array(), boolean(), createAnalysis(), endpoint(), extractArtifacts(), fetchArtifact() (+70 more)

### Community 1 - "RepositorySnapshot"
Cohesion: 0.07
Nodes (68): Finding, analyze(), _boundary_finding(), _confidence(), _configuration_finding(), _contains_dependency_signal(), _entry_point_finding(), _entry_point_sort_key() (+60 more)

### Community 2 - "main.py"
Cohesion: 0.09
Nodes (30): Exception, analysis_events(), _at_demo_capacity(), get_analysis_status(), get_artifact(), Job, publish(), FastAPI surface for RepoMind's live repository analysis. (+22 more)

### Community 3 - "schemas.py"
Cohesion: 0.15
Nodes (24): AnalysisMetrics, AnalysisScope, BaseModel, _analysis_metrics(), _analysis_scope(), _duration_ms(), _emit(), orchestrate_analysis() (+16 more)

### Community 4 - "devDependencies"
Cohesion: 0.06
Nodes (31): dependencies, react, react-dom, devDependencies, oxlint, @types/node, @types/react, @types/react-dom (+23 more)

### Community 5 - "repository.py"
Cohesion: 0.09
Nodes (45): _apply_extraction_metrics(), _bounded_text(), _collect_file_records(), count_manifest_files(), count_test_files(), _emit_progress(), evidence_location(), EvidenceExtraction (+37 more)

### Community 6 - "compilerOptions"
Cohesion: 0.08
Nodes (23): compilerOptions, allowArbitraryExtensions, allowImportingTsExtensions, erasableSyntaxOnly, jsx, lib, module, moduleDetection (+15 more)

### Community 7 - "compilerOptions"
Cohesion: 0.10
Nodes (19): compilerOptions, allowImportingTsExtensions, erasableSyntaxOnly, lib, module, moduleDetection, noEmit, noFallthroughCasesInSwitch (+11 more)

### Community 8 - "RepoMind"
Cohesion: 0.08
Nodes (23): 1. Configure and start the backend, 2. Configure and start the frontend, `AGENTS.md`, API summary, Architecture, Current scope, Deploying a judge-accessible demo, Evidence and trust boundaries (+15 more)

### Community 9 - "test_repository.py"
Cohesion: 0.10
Nodes (32): MonkeyPatch, _cache_root(), _git_evidence(), Return UI-ready, evidence-backed counts for this bounded snapshot., Validate a public GitHub URL and return a canonical clone URL., Create and resolve the configured cache root with an actionable error., validate_github_url(), _cors_origins() (+24 more)

### Community 10 - "plugins"
Cohesion: 0.22
Nodes (8): plugins, rules, react/only-export-components, react/rules-of-hooks, $schema, oxc, typescript, warn

### Community 11 - "RepositorySnapshot"
Cohesion: 0.13
Nodes (15): Number of files retained in this bounded inventory., Whether any repository source was excluded or truncated by safety limits., Return the fixed source-evidence budgets used for this snapshot., RepositorySnapshot, RepositoryInfo, _collect_progress(), _collect_rich_progress(), Path (+7 more)

### Community 12 - "RepoMind — Final Locked Spec"
Cohesion: 0.25
Nodes (7): 5-DAY BUILD PLAN, OpenAI Build Week — Developer Tools Track, PROBLEM STATEMENT, RepoMind — Final Locked Spec, SOLUTION PROVIDED, TECH STACK, WHY THIS SATISFIES JUDGING CRITERIA

### Community 13 - "OpenAI Build Week Challenge Rules & Requirements"
Cohesion: 0.33
Nodes (5): GPT-5.6 Features to Leverage, Judging Criteria (Equally Weighted), Key Information, OpenAI Build Week Challenge Rules & Requirements, Submission Checklist

### Community 14 - "React + TypeScript + Vite"
Cohesion: 0.50
Nodes (3): Expanding the Oxlint configuration, React Compiler, React + TypeScript + Vite

### Community 17 - "artifacts.py"
Cohesion: 0.15
Nodes (22): build_repository_map(), _finding_files(), _finding_line(), generate_agents_md(), _purpose(), Finding, Deterministic, evidence-backed RepoMind artifacts., Build a compact, structured map whose risk labels come from real findings. (+14 more)

### Community 18 - "AgentReport"
Cohesion: 0.16
Nodes (15): _evidence_backed_reports(), _extract_json(), _is_evidence_backed(), Finding, Ask a hosted root agent to delegate and reconcile evidence-only findings.      T, Accept hosted output only when it refers to known deterministic evidence., Send the hosted reconciler a compact inventory, never raw repository excerpts., Never publish a specialist claim that lacks a valid confidence/evidence pair. (+7 more)

### Community 19 - "worker.py"
Cohesion: 0.29
Nodes (9): _publish(), _publish_update(), ProgressCallback, Concurrent deterministic specialist-worker execution., Run the four read-only specialist lenses concurrently against one snapshot., Support both legacy three-argument and enriched progress callbacks., run_specialists(), One concrete activity emitted by a synchronous specialist worker. (+1 more)

## Knowledge Gaps
- **101 isolated node(s):** `$schema`, `typescript`, `oxc`, `react/rules-of-hooks`, `warn` (+96 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `RepositorySnapshot` connect `RepositorySnapshot` to `RepositorySnapshot`, `schemas.py`, `repository.py`, `test_repository.py`, `artifacts.py`, `AgentReport`, `worker.py`?**
  _High betweenness centrality (0.100) - this node is a cross-community bridge._
- **Why does `snapshot_repository()` connect `repository.py` to `test_repository.py`, `main.py`, `RepositorySnapshot`?**
  _High betweenness centrality (0.025) - this node is a cross-community bridge._
- **Why does `orchestrate_analysis()` connect `schemas.py` to `main.py`, `RepositorySnapshot`, `artifacts.py`, `AgentReport`, `worker.py`?**
  _High betweenness centrality (0.021) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `RepositorySnapshot` (e.g. with `EvidenceLocation` and `RepositoryInfo`) actually correct?**
  _`RepositorySnapshot` has 3 INFERRED edges - model-reasoned connections that need verification._
- **What connects `$schema`, `typescript`, `oxc` to the rest of the system?**
  _101 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `api.ts` be split into smaller, more focused modules?**
  _Cohesion score 0.05643513789581205 - nodes in this community are weakly interconnected._
- **Should `RepositorySnapshot` be split into smaller, more focused modules?**
  _Cohesion score 0.07182524990744169 - nodes in this community are weakly interconnected._