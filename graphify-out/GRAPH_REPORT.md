# Graph Report - RepoMind  (2026-07-18)

## Corpus Check
- 40 files · ~107,001 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 561 nodes · 1182 edges · 29 communities (26 shown, 3 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 31 edges (avg confidence: 0.54)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `e8c88ccc`
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
- master.py
- OpenAI Build Week Challenge Rules & Requirements
- RepositorySnapshot
- tsconfig.json
- test_orchestration.py
- orchestrate_analysis
- AGENTS.md
- worker.py
- EvidenceLocation
- Deployment guide
- RepoMind submission handoff
- Quick start
- Demo proof checklist
- AGENTS.md
- JUDGE_PATH.md
- Codex and GPT-5.6 boundaries

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
- `_run_analysis()` --indirect_call--> `snapshot_repository()`  [INFERRED]
  main.py → repository.py
- `FileInventory` --uses--> `RepositoryInfo`  [INFERRED]
  repository.py → schemas.py
- `EvidenceExtraction` --uses--> `EvidenceLocation`  [INFERRED]
  repository.py → schemas.py
- `EvidenceExtraction` --uses--> `RepositoryInfo`  [INFERRED]
  repository.py → schemas.py

## Import Cycles
- 1-file cycle: `workers/__init__.py -> workers/__init__.py`

## Communities (29 total, 3 thin omitted)

### Community 0 - "api.ts"
Cohesion: 0.08
Nodes (35): AgentGlyph(), AgentGlyphProps, BrandMark(), AgentActivity(), AGENTS, AgentsPreview(), AgentsSection, AgentsSectionContent() (+27 more)

### Community 1 - "RepositorySnapshot"
Cohesion: 0.07
Nodes (68): Finding, analyze(), _boundary_finding(), _confidence(), _configuration_finding(), _contains_dependency_signal(), _entry_point_finding(), _entry_point_sort_key() (+60 more)

### Community 2 - "main.py"
Cohesion: 0.07
Nodes (39): Exception, FileResponse, analysis_events(), _at_demo_capacity(), _frontend_index(), get_analysis_status(), get_artifact(), Job (+31 more)

### Community 3 - "schemas.py"
Cohesion: 0.18
Nodes (21): build_repository_map(), _finding_files(), _finding_line(), generate_agents_md(), _purpose(), Finding, Deterministic, evidence-backed RepoMind artifacts., Build a compact, structured map whose risk labels come from real findings. (+13 more)

### Community 4 - "devDependencies"
Cohesion: 0.06
Nodes (35): @fontsource-variable/geist, @fontsource-variable/geist-mono, dependencies, @fontsource-variable/geist, @fontsource-variable/geist-mono, react, react-dom, devDependencies (+27 more)

### Community 5 - "repository.py"
Cohesion: 0.07
Nodes (62): MonkeyPatch, _apply_extraction_metrics(), _bounded_text(), _cache_root(), _collect_file_records(), count_manifest_files(), count_test_files(), _emit_progress() (+54 more)

### Community 6 - "compilerOptions"
Cohesion: 0.08
Nodes (23): compilerOptions, allowArbitraryExtensions, allowImportingTsExtensions, erasableSyntaxOnly, jsx, lib, module, moduleDetection (+15 more)

### Community 7 - "compilerOptions"
Cohesion: 0.10
Nodes (19): compilerOptions, allowImportingTsExtensions, erasableSyntaxOnly, lib, module, moduleDetection, noEmit, noFallthroughCasesInSwitch (+11 more)

### Community 8 - "RepoMind"
Cohesion: 0.18
Nodes (10): Architecture, Deployment readiness, From repository to usable context, Judge access, License, Submission evidence, Trust boundaries and execution modes, Verify locally (+2 more)

### Community 9 - "test_repository.py"
Cohesion: 0.24
Nodes (10): _cors_origins(), _d_drive_is_available(), _default_cache_dir(), _positive_int(), Path, Runtime configuration for RepoMind.  Configuration is deliberately small for the, Keep the established D: cache only on hosts where that drive exists., Choose the local D: cache when available, otherwise use a portable temp path. (+2 more)

### Community 10 - "plugins"
Cohesion: 0.22
Nodes (8): plugins, rules, react/only-export-components, react/rules-of-hooks, $schema, oxc, typescript, warn

### Community 11 - "api.ts"
Cohesion: 0.10
Nodes (51): apiBase, ApiError, array(), boolean(), createAnalysis(), endpoint(), extractArtifacts(), fetchArtifact() (+43 more)

### Community 12 - "master.py"
Cohesion: 0.19
Nodes (17): AnalysisMetrics, BaseModel, _analysis_metrics(), RepoMind's master orchestration and optional native GPT-5.6 reconciliation., Classify deterministic findings without inventing model-only decisions., _reconcile_evidence(), ReconciliationSummary, AnalysisMetrics (+9 more)

### Community 13 - "OpenAI Build Week Challenge Rules & Requirements"
Cohesion: 0.33
Nodes (5): GPT-5.6 Features to Leverage, Judging Criteria (Equally Weighted), Key Information, OpenAI Build Week Challenge Rules & Requirements, Submission Checklist

### Community 14 - "RepositorySnapshot"
Cohesion: 0.12
Nodes (9): AnalysisScope, _analysis_scope(), Explain bounded evidence so absence of a finding is never presented as proof of, Number of files retained in this bounded inventory., Whether any repository source was excluded or truncated by safety limits., Return the fixed source-evidence budgets used for this snapshot., RepositorySnapshot, RepositoryInfo (+1 more)

### Community 17 - "test_orchestration.py"
Cohesion: 0.20
Nodes (13): Accept hosted output only when it refers to known deterministic evidence., _root_final_text(), _validated_priority_finding_ids(), _collect_progress(), _collect_rich_progress(), Path, Tests for deterministic workers, artifacts, and mocked hosted reconciliation., test_native_priority_payload_rejects_unknown_or_duplicate_evidence() (+5 more)

### Community 18 - "orchestrate_analysis"
Cohesion: 0.18
Nodes (13): _duration_ms(), _emit(), _extract_json(), orchestrate_analysis(), ProgressCallback, Ask a hosted root agent to delegate and reconcile evidence-only findings.      T, Send the hosted reconciler a compact inventory, never raw repository excerpts., Keep the public callback compatible with the original three-argument form. (+5 more)

### Community 19 - "AGENTS.md"
Cohesion: 0.20
Nodes (9): Architecture, Change-Sensitive Context, Coding Conventions, Important Files, Overview, Risk Areas, Testing Strategy, Things Not to Touch (+1 more)

### Community 20 - "worker.py"
Cohesion: 0.29
Nodes (9): _publish(), _publish_update(), ProgressCallback, Concurrent deterministic specialist-worker execution., Run the four read-only specialist lenses concurrently against one snapshot., Support both legacy three-argument and enriched progress callbacks., run_specialists(), One concrete activity emitted by a synchronous specialist worker. (+1 more)

### Community 21 - "EvidenceLocation"
Cohesion: 0.22
Nodes (9): _evidence_backed_reports(), _is_evidence_backed(), Finding, Never publish a specialist claim that lacks a valid confidence/evidence pair., FileInventory, The bounded file inventory and the limits encountered while producing it., EvidenceLocation, A concrete source location supporting a finding. (+1 more)

### Community 22 - "Deployment guide"
Cohesion: 0.29
Nodes (5): Container commands, Deployment guide, Environment, Production preflight, Runtime requirements

### Community 23 - "RepoMind submission handoff"
Cohesion: 0.33
Nodes (6): Final checks, Native GPT-5.6 evidence record, Ready-to-paste project copy, RepoMind submission handoff, Required disclosures, Required insertion points

### Community 24 - "Quick start"
Cohesion: 0.33
Nodes (6): 1. Start the API, 2. Start the dashboard, Canonical sample repository, Prerequisites, Quick start, Supported developer environments

### Community 25 - "Demo proof checklist"
Cohesion: 0.40
Nodes (4): Before publishing, Before recording, Demo proof checklist, In the public video

### Community 28 - "Codex and GPT-5.6 boundaries"
Cohesion: 0.67
Nodes (3): Codex and GPT-5.6 boundaries, How Codex accelerated delivery, Key technical decisions

## Knowledge Gaps
- **116 isolated node(s):** `$schema`, `typescript`, `oxc`, `react/rules-of-hooks`, `warn` (+111 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `RepositorySnapshot` connect `RepositorySnapshot` to `RepositorySnapshot`, `schemas.py`, `repository.py`, `master.py`, `test_orchestration.py`, `orchestrate_analysis`, `worker.py`, `EvidenceLocation`?**
  _High betweenness centrality (0.087) - this node is a cross-community bridge._
- **Why does `snapshot_repository()` connect `repository.py` to `main.py`, `RepositorySnapshot`?**
  _High betweenness centrality (0.023) - this node is a cross-community bridge._
- **Why does `orchestrate_analysis()` connect `orchestrate_analysis` to `main.py`, `schemas.py`, `master.py`, `RepositorySnapshot`, `test_orchestration.py`, `worker.py`, `EvidenceLocation`?**
  _High betweenness centrality (0.021) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `RepositorySnapshot` (e.g. with `EvidenceLocation` and `RepositoryInfo`) actually correct?**
  _`RepositorySnapshot` has 3 INFERRED edges - model-reasoned connections that need verification._
- **What connects `$schema`, `typescript`, `oxc` to the rest of the system?**
  _116 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `api.ts` be split into smaller, more focused modules?**
  _Cohesion score 0.07632850241545894 - nodes in this community are weakly interconnected._
- **Should `RepositorySnapshot` be split into smaller, more focused modules?**
  _Cohesion score 0.07182524990744169 - nodes in this community are weakly interconnected._