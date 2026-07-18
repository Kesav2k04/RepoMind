# Graph Report - RepoMind  (2026-07-18)

## Corpus Check
- 33 files · ~88,858 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 515 nodes · 1128 edges · 14 communities (13 shown, 1 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 30 edges (avg confidence: 0.54)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `650334fe`
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
- OpenAI Build Week Challenge Rules & Requirements
- tsconfig.json

## God Nodes (most connected - your core abstractions)
1. `RepositorySnapshot` - 64 edges
2. `AgentReport` - 27 edges
3. `snapshot_repository()` - 24 edges
4. `orchestrate_analysis()` - 23 edges
5. `Finding` - 20 edges
6. `compilerOptions` - 18 edges
7. `analyze()` - 18 edges
8. `evidence_paths()` - 17 edges
9. `bounded_confidence()` - 16 edges
10. `analyze()` - 16 edges

## Surprising Connections (you probably didn't know these)
- `Job` --uses--> `AnalysisResult`  [INFERRED]
  main.py → schemas.py
- `_run_analysis()` --indirect_call--> `cleanup_checkout()`  [INFERRED]
  main.py → repository.py
- `_run_analysis()` --indirect_call--> `snapshot_repository()`  [INFERRED]
  main.py → repository.py
- `FileInventory` --uses--> `EvidenceLocation`  [INFERRED]
  repository.py → schemas.py
- `EvidenceExtraction` --uses--> `EvidenceLocation`  [INFERRED]
  repository.py → schemas.py

## Import Cycles
- 1-file cycle: `workers/__init__.py -> workers/__init__.py`

## Communities (14 total, 1 thin omitted)

### Community 0 - "api.ts"
Cohesion: 0.05
Nodes (83): apiBase, ApiError, array(), boolean(), createAnalysis(), endpoint(), extractArtifacts(), fetchArtifact() (+75 more)

### Community 1 - "RepositorySnapshot"
Cohesion: 0.06
Nodes (77): Number of files retained in this bounded inventory., Whether any repository source was excluded or truncated by safety limits., Return the fixed source-evidence budgets used for this snapshot., RepositorySnapshot, RepositoryInfo, EvidenceLocation, Finding, A concrete source location supporting a finding. (+69 more)

### Community 2 - "main.py"
Cohesion: 0.08
Nodes (35): Exception, FileResponse, analysis_events(), _at_demo_capacity(), _frontend_index(), get_analysis_status(), get_artifact(), Job (+27 more)

### Community 3 - "schemas.py"
Cohesion: 0.06
Nodes (68): AnalysisMetrics, AnalysisScope, build_repository_map(), _finding_files(), _finding_line(), generate_agents_md(), _purpose(), Finding (+60 more)

### Community 4 - "devDependencies"
Cohesion: 0.06
Nodes (35): @fontsource-variable/geist, @fontsource-variable/geist-mono, dependencies, @fontsource-variable/geist, @fontsource-variable/geist-mono, react, react-dom, devDependencies (+27 more)

### Community 5 - "repository.py"
Cohesion: 0.06
Nodes (69): MonkeyPatch, _apply_extraction_metrics(), _bounded_text(), _cache_root(), cleanup_checkout(), clone_github_repository(), _collect_file_records(), count_manifest_files() (+61 more)

### Community 6 - "compilerOptions"
Cohesion: 0.08
Nodes (23): compilerOptions, allowArbitraryExtensions, allowImportingTsExtensions, erasableSyntaxOnly, jsx, lib, module, moduleDetection (+15 more)

### Community 7 - "compilerOptions"
Cohesion: 0.10
Nodes (19): compilerOptions, allowImportingTsExtensions, erasableSyntaxOnly, lib, module, moduleDetection, noEmit, noFallthroughCasesInSwitch (+11 more)

### Community 8 - "RepoMind"
Cohesion: 0.13
Nodes (14): 1. Start the API, 2. Start the dashboard, Architecture, Codex and GPT-5.6 boundaries, From repository to usable context, License, Prerequisites, Quick start (+6 more)

### Community 9 - "test_repository.py"
Cohesion: 0.13
Nodes (20): _cors_origins(), _d_drive_is_available(), _default_cache_dir(), _positive_int(), Path, Runtime configuration for RepoMind.  Configuration is deliberately small for the, Keep the established D: cache only on hosts where that drive exists., Choose the local D: cache when available, otherwise use a portable temp path. (+12 more)

### Community 10 - "plugins"
Cohesion: 0.22
Nodes (8): plugins, rules, react/only-export-components, react/rules-of-hooks, $schema, oxc, typescript, warn

### Community 13 - "OpenAI Build Week Challenge Rules & Requirements"
Cohesion: 0.33
Nodes (5): GPT-5.6 Features to Leverage, Judging Criteria (Equally Weighted), Key Information, OpenAI Build Week Challenge Rules & Requirements, Submission Checklist

## Knowledge Gaps
- **87 isolated node(s):** `$schema`, `typescript`, `oxc`, `react/rules-of-hooks`, `warn` (+82 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `RepositorySnapshot` connect `RepositorySnapshot` to `test_repository.py`, `schemas.py`, `repository.py`?**
  _High betweenness centrality (0.103) - this node is a cross-community bridge._
- **Why does `snapshot_repository()` connect `repository.py` to `RepositorySnapshot`, `main.py`?**
  _High betweenness centrality (0.028) - this node is a cross-community bridge._
- **Why does `orchestrate_analysis()` connect `schemas.py` to `RepositorySnapshot`, `main.py`, `test_repository.py`?**
  _High betweenness centrality (0.025) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `RepositorySnapshot` (e.g. with `EvidenceLocation` and `RepositoryInfo`) actually correct?**
  _`RepositorySnapshot` has 3 INFERRED edges - model-reasoned connections that need verification._
- **What connects `$schema`, `typescript`, `oxc` to the rest of the system?**
  _87 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `api.ts` be split into smaller, more focused modules?**
  _Cohesion score 0.05131578947368421 - nodes in this community are weakly interconnected._
- **Should `RepositorySnapshot` be split into smaller, more focused modules?**
  _Cohesion score 0.05934065934065934 - nodes in this community are weakly interconnected._