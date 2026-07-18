# Graph Report - RepoMind  (2026-07-18)

## Corpus Check
- 33 files · ~104,244 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 518 nodes · 1135 edges · 18 communities (17 shown, 1 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 30 edges (avg confidence: 0.54)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `2c3db2dd`
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
- api.ts
- normalizeJob
- OpenAI Build Week Challenge Rules & Requirements
- test_orchestration.py
- tsconfig.json
- getAnalysis

## God Nodes (most connected - your core abstractions)
1. `RepositorySnapshot` - 64 edges
2. `AgentReport` - 27 edges
3. `snapshot_repository()` - 24 edges
4. `orchestrate_analysis()` - 23 edges
5. `Finding` - 20 edges
6. `compilerOptions` - 18 edges
7. `analyze()` - 18 edges
8. `evidence_paths()` - 17 edges
9. `normalizeJob()` - 16 edges
10. `bounded_confidence()` - 16 edges

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

## Communities (18 total, 1 thin omitted)

### Community 0 - "api.ts"
Cohesion: 0.08
Nodes (31): BrandMark(), AgentActivity(), AGENTS, AgentsPreview(), AgentsSection, AgentsSectionContent(), agentState(), CompletionSummary() (+23 more)

### Community 1 - "RepositorySnapshot"
Cohesion: 0.06
Nodes (79): Number of files retained in this bounded inventory., Whether any repository source was excluded or truncated by safety limits., Return the fixed source-evidence budgets used for this snapshot., RepositorySnapshot, RepositoryInfo, EvidenceLocation, Finding, A concrete source location supporting a finding. (+71 more)

### Community 2 - "main.py"
Cohesion: 0.08
Nodes (35): Exception, FileResponse, analysis_events(), _at_demo_capacity(), _frontend_index(), get_analysis_status(), get_artifact(), Job (+27 more)

### Community 3 - "schemas.py"
Cohesion: 0.06
Nodes (67): AnalysisMetrics, AnalysisScope, build_repository_map(), _finding_files(), _finding_line(), generate_agents_md(), _purpose(), Finding (+59 more)

### Community 4 - "devDependencies"
Cohesion: 0.06
Nodes (35): @fontsource-variable/geist, @fontsource-variable/geist-mono, dependencies, @fontsource-variable/geist, @fontsource-variable/geist-mono, react, react-dom, devDependencies (+27 more)

### Community 5 - "repository.py"
Cohesion: 0.08
Nodes (51): _apply_extraction_metrics(), _bounded_text(), _cache_root(), cleanup_checkout(), clone_github_repository(), _collect_file_records(), count_manifest_files(), count_test_files() (+43 more)

### Community 6 - "compilerOptions"
Cohesion: 0.08
Nodes (23): compilerOptions, allowArbitraryExtensions, allowImportingTsExtensions, erasableSyntaxOnly, jsx, lib, module, moduleDetection (+15 more)

### Community 7 - "compilerOptions"
Cohesion: 0.10
Nodes (19): compilerOptions, allowImportingTsExtensions, erasableSyntaxOnly, lib, module, moduleDetection, noEmit, noFallthroughCasesInSwitch (+11 more)

### Community 8 - "RepoMind"
Cohesion: 0.14
Nodes (13): 1. Start the API, 2. Start the dashboard, Architecture, Codex and GPT-5.6 boundaries, From repository to usable context, License, Prerequisites, Quick start (+5 more)

### Community 9 - "test_repository.py"
Cohesion: 0.11
Nodes (28): MonkeyPatch, Return UI-ready, evidence-backed counts for this bounded snapshot., Validate a public GitHub URL and return a canonical clone URL., validate_github_url(), _cors_origins(), _d_drive_is_available(), _default_cache_dir(), _positive_int() (+20 more)

### Community 10 - "plugins"
Cohesion: 0.22
Nodes (8): plugins, rules, react/only-export-components, react/rules-of-hooks, $schema, oxc, typescript, warn

### Community 11 - "api.ts"
Cohesion: 0.11
Nodes (24): apiBase, ApiError, roles, webSocketEndpoint(), AgentGlyph(), AgentGlyphProps, AgentRole, AnalysisJob (+16 more)

### Community 12 - "normalizeJob"
Cohesion: 0.25
Nodes (24): array(), boolean(), extractArtifacts(), isRole(), lineNumber(), normalizeAnalysisScope(), normalizeDecision(), normalizeEvidence() (+16 more)

### Community 13 - "OpenAI Build Week Challenge Rules & Requirements"
Cohesion: 0.33
Nodes (5): GPT-5.6 Features to Leverage, Judging Criteria (Equally Weighted), Key Information, OpenAI Build Week Challenge Rules & Requirements, Submission Checklist

### Community 14 - "test_orchestration.py"
Cohesion: 0.27
Nodes (10): _collect_progress(), _collect_rich_progress(), Path, Tests for deterministic workers, artifacts, and mocked hosted reconciliation., test_native_priority_payload_rejects_unknown_or_duplicate_evidence(), test_native_reconciliation_timeout_returns_fast_evidence_fallback(), test_native_reconciliation_uses_configured_model_and_validates_root_output(), test_orchestrate_analysis_uses_four_worker_evidence_fallback() (+2 more)

### Community 17 - "getAnalysis"
Cohesion: 0.47
Nodes (6): createAnalysis(), endpoint(), fetchArtifact(), getAnalysis(), getArtifactUrl(), readError()

## Knowledge Gaps
- **87 isolated node(s):** `$schema`, `typescript`, `oxc`, `react/rules-of-hooks`, `warn` (+82 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `RepositorySnapshot` connect `RepositorySnapshot` to `test_repository.py`, `schemas.py`, `repository.py`, `test_orchestration.py`?**
  _High betweenness centrality (0.102) - this node is a cross-community bridge._
- **Why does `snapshot_repository()` connect `repository.py` to `RepositorySnapshot`, `main.py`, `test_repository.py`?**
  _High betweenness centrality (0.027) - this node is a cross-community bridge._
- **Why does `orchestrate_analysis()` connect `schemas.py` to `RepositorySnapshot`, `main.py`, `test_orchestration.py`?**
  _High betweenness centrality (0.025) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `RepositorySnapshot` (e.g. with `EvidenceLocation` and `RepositoryInfo`) actually correct?**
  _`RepositorySnapshot` has 3 INFERRED edges - model-reasoned connections that need verification._
- **What connects `$schema`, `typescript`, `oxc` to the rest of the system?**
  _87 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `api.ts` be split into smaller, more focused modules?**
  _Cohesion score 0.08414634146341464 - nodes in this community are weakly interconnected._
- **Should `RepositorySnapshot` be split into smaller, more focused modules?**
  _Cohesion score 0.057971014492753624 - nodes in this community are weakly interconnected._