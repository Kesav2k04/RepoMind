import { useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import { createAnalysis, fetchArtifact, getAnalysis, getArtifactUrl, openEventStream } from './api'
import type { AgentRole, AnalysisJob, Finding, FindingSeverity, ProgressEvent, RepositoryMapNode, SpecialistReport } from './types'
import { AgentGlyph } from './components/AgentGlyph'
import { BrandMark } from './components/BrandMark'
import './RepoMind.css'

const AGENTS: Array<{ role: AgentRole; label: string; description: string; defaultAction: string }> = [
  { role: 'architecture', label: 'Architecture', description: 'Maps entry points and boundaries.', defaultAction: 'Finding entry points…' },
  { role: 'risk', label: 'Risk', description: 'Surfaces fragile and exposed areas.', defaultAction: 'Checking dependencies…' },
  { role: 'testing', label: 'Testing', description: 'Finds verification gaps.', defaultAction: 'Discovering tests…' },
  { role: 'history', label: 'History', description: 'Traces churn and change context.', defaultAction: 'Reading commits…' },
]

const STATUS_LABELS: Record<string, string> = {
  queued: 'Queued', pending: 'Queued', running: 'Analyzing', reconciling: 'Reconciling', completed: 'Complete', complete: 'Complete', failed: 'Needs attention',
}

function reportFor(job: AnalysisJob, role: AgentRole): SpecialistReport | undefined { return job.reports.find((report) => report.role === role) }
function modeLabel(mode?: string): string { return mode === 'native_multi_agent' ? 'GPT-5.6 Native · Connected' : mode ? 'Evidence Mode · Deterministic' : 'Mode resolving' }
function severityClass(severity: FindingSeverity): string { return `severity severity--${severity}` }
function isComplete(job?: AnalysisJob): boolean { return job?.status === 'completed' || job?.status === 'complete' }
function isFailed(job?: AnalysisJob): boolean { return job?.status === 'failed' }
function hasFindingEvidence(finding: Finding): boolean { return finding.evidence.some((item) => item.path.trim().length > 0) }

function validatePublicGitHubUrl(value: string): string | undefined {
  try {
    const url = new URL(value.trim())
    const path = url.pathname.split('/').filter(Boolean)
    if (url.protocol !== 'https:' || url.hostname.toLowerCase() !== 'github.com' || path.length !== 2 || url.search || url.hash || url.username || url.password || url.port) {
      return 'Enter a public GitHub HTTPS repository URL, such as https://github.com/owner/repository.'
    }
    return undefined
  } catch {
    return 'Enter a complete public GitHub HTTPS repository URL.'
  }
}

function latestEvent(job: AnalysisJob, role?: AgentRole): ProgressEvent | undefined {
  return [...job.events].reverse().find((event) => role ? event.role === role : true)
}

function agentState(job: AnalysisJob, role: AgentRole): string {
  if (reportFor(job, role)) return 'complete'
  if (job.status === 'failed') return 'failed'
  const explicit = job.agentStatus[role]
  if (explicit) return explicit.toLowerCase().includes('complete') ? 'complete' : explicit.toLowerCase().includes('fail') ? 'failed' : 'working'
  return latestEvent(job, role) ? 'working' : 'queued'
}

function formatDuration(milliseconds: number): string {
  if (!milliseconds) return '—'
  return milliseconds >= 60_000 ? `${Math.round(milliseconds / 1_000 / 60)}m ${Math.round((milliseconds / 1_000) % 60)}s` : `${Math.max(1, Math.round(milliseconds / 1_000))}s`
}

function repositoryLabel(job?: AnalysisJob): string {
  const knownName = job?.repositoryName || job?.repository?.name
  if (knownName) return knownName
  try {
    const finalPath = new URL(job?.repoUrl ?? '').pathname.split('/').filter(Boolean).pop()
    if (finalPath) return finalPath.replace(/\.git$/i, '')
  } catch {
    // The submitted URL is validated before a job exists; retain a neutral label for malformed legacy jobs.
  }
  return 'Repository analysis'
}

function metricValue(event?: ProgressEvent): string | undefined {
  if (!event) return undefined
  if (event.current !== undefined && event.total !== undefined) return `${event.current}/${event.total}`
  if (event.percent !== undefined) return `${event.percent}%`
  const metrics = Object.entries(event.metrics)
  if (metrics.length) return `${metrics[0][1]} ${metrics[0][0].replaceAll('_', ' ')}`
  return undefined
}

function evidenceActivity(job: AnalysisJob): string {
  const event = latestEvent(job)
  const raw = event?.action || event?.message || event?.phase || ''
  const normalized = raw.toLowerCase()
  if (normalized.includes('clone')) return 'Cloning source'
  if (normalized.includes('inventor') || normalized.includes('index')) return 'Indexing files'
  if (normalized.includes('sample') || normalized.includes('evidence')) return 'Capturing evidence'
  if (normalized.includes('history') || normalized.includes('commit')) return 'Reading history'
  if (normalized.includes('reconcil') || normalized.includes('master')) return 'Reconciling signals'
  if (raw) return raw.replaceAll('_', ' ')
  return job.status === 'queued' || job.status === 'pending' ? 'Queued safely' : 'Preparing evidence'
}

function EvidenceMetric({ value, label, pending, complete }: { value: number; label: string; pending: string; complete: boolean }) {
  const observed = value > 0 || complete
  return <div className={observed ? '' : 'evidence-summary__metric--pending'}>
    <span className="evidence-summary__number">{observed ? value : pending}</span>
    <span>{observed ? label : `${label} · in progress`}</span>
  </div>
}

type PipelineState = 'waiting' | 'working' | 'complete' | 'failed'

function PipelineStage({ label, detail, state, children }: { label: string; detail: string; state: PipelineState; children?: React.ReactNode }) {
  return <div className={`pipeline-stage pipeline-stage--${state}`}>
    <span className="pipeline-stage__dot" aria-hidden="true" />
    <div><strong>{label}</strong><span>{detail}</span>{children}</div>
  </div>
}

function Pipeline({ job }: { job?: AnalysisJob }) {
  const complete = isComplete(job)
  const failed = isFailed(job)
  const evidenceEvent = job?.events.find((event) => ['cloning', 'indexing', 'evidence'].some((phase) => event.phase.toLowerCase().includes(phase)))
  const hasEvidence = Boolean(evidenceEvent || job?.metrics.filesAnalyzed)
  const masterEvent = job?.events.find((event) => ['reconcil', 'master', 'artifact'].some((phase) => event.phase.toLowerCase().includes(phase)))
  const activeRoles = job ? AGENTS.filter((agent) => agentState(job, agent.role) !== 'queued').length : 0
  const artifactsDone = complete && Boolean(job?.artifacts.agentsMd || job?.artifacts.repoMap || job?.artifacts.repoMapNodes.length)
  const completedRoles = job?.reports.length ?? 0
  const decisions = job?.reconciliation.decisions.length ?? 0
  const evidenceState: PipelineState = hasEvidence ? (activeRoles ? 'complete' : 'working') : failed ? 'failed' : 'waiting'
  const masterState: PipelineState = complete ? 'complete' : failed ? 'failed' : masterEvent || completedRoles > 0 ? 'working' : 'waiting'

  const isActive = Boolean(job && !complete && !failed)

  return <section className={`pipeline ${isActive ? 'pipeline--active' : ''}`} aria-label="RepoMind orchestration pipeline">
    <PipelineStage label="Repository" detail={job ? 'Source received' : 'Paste a public GitHub URL'} state={job ? 'complete' : 'waiting'} />
    <span className="pipeline-arrow" aria-hidden="true">→</span>
    <PipelineStage label="Evidence Pack" detail={hasEvidence ? `${job?.metrics.filesAnalyzed || evidenceEvent?.metrics.files_analyzed || 'Bounded'} files indexed` : failed ? 'Evidence pack unavailable' : 'Manifests, tests, history'} state={evidenceState} />
    <span className="pipeline-arrow" aria-hidden="true">→</span>
    <div className="pipeline-specialists">
      <span className="pipeline-specialists__label">4 specialists · parallel evidence reviews</span>
      <div>{AGENTS.map((agent) => {
        const state = job ? agentState(job, agent.role) : 'waiting'
        return <span className={`mini-agent mini-agent--${state}`} key={agent.role}>{agent.label}</span>
      })}</div>
    </div>
    <span className="pipeline-arrow" aria-hidden="true">→</span>
    <PipelineStage label="Master Reconciliation" detail={complete ? `${decisions || 'Evidence'} decisions recorded` : failed ? 'Stopped safely; no unsupported synthesis' : masterEvent?.action ?? masterEvent?.message ?? (completedRoles ? `Comparing ${completedRoles}/4 specialist reports` : 'Compares and resolves evidence')} state={masterState} />
    <span className="pipeline-arrow" aria-hidden="true">→</span>
    <PipelineStage label="AGENTS.md + Map" detail={artifactsDone ? 'Validated context ready' : failed ? 'Not generated' : 'Agent context + risk map'} state={artifactsDone ? 'complete' : failed ? 'failed' : 'waiting'} />
  </section>
}

function TrustPanel({ job }: { job: AnalysisJob }) {
  const scope = job.analysisScope ?? { status: 'unknown' as const, reasons: [] }
  const evidenceFindings = job.reports.flatMap((report) => report.findings).filter(hasFindingEvidence).length
  const unsupportedFindings = job.reports.flatMap((report) => report.findings).length - evidenceFindings
  const scopeTitle = scope.status === 'partial' ? 'Partial analysis' : scope.status === 'complete' ? 'Coverage recorded' : 'Coverage not reported'
  const scopeCopy = scope.status === 'partial'
    ? `RepoMind reviewed ${scope.filesSelected ?? job.metrics.filesAnalyzed ?? 'a bounded set of'} selected file${scope.filesSelected === 1 ? '' : 's'} and excluded ${scope.filesExcluded ?? 'some'} file${scope.filesExcluded === 1 ? '' : 's'} or content after reaching a safety bound. Absence of a finding is not a clean bill of health.`
    : scope.status === 'complete'
      ? 'The API reported the scan coverage for this run. Findings remain limited to returned repository evidence.'
      : 'This API response does not report coverage details. Findings are limited to returned repository evidence; absence of a finding is not a clean bill of health.'
  const artifactStatus = job.validation?.artifactsValidated === true
    ? 'Validated against returned evidence'
    : job.validation?.artifactsValidated === false
      ? 'Withheld: validation did not pass'
      : 'Validation status not reported'

  return <aside className={`trust-panel trust-panel--${scope.status} ${job.validation?.artifactsValidated === false ? 'trust-panel--artifacts-withheld' : ''}`} aria-label="Evidence and coverage status">
    <div className="trust-panel__lead"><span className="trust-panel__mark" aria-hidden="true">{scope.status === 'partial' ? '!' : scope.status === 'complete' ? '✓' : 'i'}</span><div><p className="eyebrow">Evidence trust</p><h3>{scopeTitle}</h3><p>{scopeCopy}</p></div></div>
    {scope.reasons.length > 0 && <p className="trust-panel__reasons"><strong>Scope note:</strong> {scope.reasons.join(' · ')}</p>}
    <div className="trust-panel__facts"><span><strong>{evidenceFindings}</strong> sourced finding{evidenceFindings === 1 ? '' : 's'}</span><span><strong>{unsupportedFindings}</strong> unsupported signal{unsupportedFindings === 1 ? '' : 's'}</span><span><strong>Artifacts</strong> {artifactStatus}</span></div>
  </aside>
}

function FindingRow({ finding }: { finding: Finding }) {
  const evidence = finding.evidence.find((item) => item.path.trim().length > 0)
  const evidenceBacked = hasFindingEvidence(finding)
  const confidence = evidenceBacked && finding.confidence !== undefined ? Math.round(finding.confidence * 100) : undefined
  const location = evidence ? `${evidence.path}${evidence.lineStart ? ` · line ${evidence.lineStart}${evidence.lineEnd && evidence.lineEnd !== evidence.lineStart ? `–${evidence.lineEnd}` : ''}` : ' · file-level evidence'}` : finding.files[0]
  if (!evidenceBacked) return <article className="finding-row finding-row--unverified">
    <div className="finding-row__meta"><span className={severityClass(finding.severity)}>{finding.severity === 'info' ? 'signal' : finding.severity}</span></div>
    <div className="finding-row__content"><h4>{finding.title}</h4>{finding.detail && <p>{finding.detail}</p>}<p className="finding-unverified"><strong>Evidence unavailable:</strong> this signal is not included in the trusted recommendation set.</p></div>
  </article>
  return <article className="finding-row">
    <div className="finding-row__meta"><span className={severityClass(finding.severity)}>{finding.severity === 'info' ? 'signal' : finding.severity}</span>{confidence !== undefined && <span className="finding-confidence">{confidence}% evidence confidence</span>}</div>
    <div className="finding-row__content"><h4>{finding.title}</h4>{finding.detail && <p>{finding.detail}</p>}{location && <div className="evidence-line"><span>Evidence</span><code>{location}</code></div>}{evidence?.reason && <p className="finding-reason"><strong>Reason:</strong> {evidence.reason}</p>}{evidence?.excerpt && <code className="evidence-excerpt">{evidence.excerpt}</code>}{finding.recommendation && <p className="finding-recommendation">{finding.recommendation}</p>}</div>
  </article>
}

function ReportCard({ report, agent }: { report?: SpecialistReport; agent: (typeof AGENTS)[number] }) {
  const findings = report?.findings ?? []
  return <article className="report-card"><div className="report-card__heading"><AgentGlyph role={agent.role} /><div><p className="eyebrow">{agent.label}</p><h3>{report?.summary || agent.description}</h3></div>{report?.confidence !== undefined && <span className="confidence">{Math.round(report.confidence * 100)}% confidence</span>}</div>{findings.length ? <div className="finding-list">{findings.map((finding) => <FindingRow finding={finding} key={finding.id} />)}</div> : <p className="card-empty">No evidence-backed findings published yet.</p>}</article>
}

function NativePriorities({ job }: { job: AnalysisJob }) {
  const findingById = new Map(job.reports.flatMap((report) => report.findings).map((finding) => [finding.id, finding]))
  const priorities = job.priorityFindingIds.map((id) => findingById.get(id)).filter((finding): finding is Finding => Boolean(finding))
  if (job.mode !== 'native_multi_agent') return null
  if (!priorities.length) return <aside className="native-priorities native-priorities--empty" aria-label="GPT-5.6 evidence-bound priorities">
    <div><p className="eyebrow eyebrow--accent">GPT-5.6 native synthesis</p><h3>No additional priorities nominated</h3><p>GPT-5.6 reviewed the validated inventory but returned no presentation priorities. Canonical artifacts and deterministic decisions remain unchanged.</p></div>
  </aside>
  return <aside className="native-priorities" aria-label="GPT-5.6 evidence-bound priorities">
    <div><p className="eyebrow eyebrow--accent">GPT-5.6 native synthesis</p><h3>Model-ranked priorities</h3><p>The model selected and ordered existing evidence-backed signals. It did not create findings, paths, line numbers, or artifact content.</p></div>
    <ol>{priorities.map((finding, index) => {
      const evidence = finding.evidence.find((item) => item.path.trim().length > 0)
      const location = evidence ? `${evidence.path}${evidence.lineStart ? ` · line ${evidence.lineStart}` : ''}` : finding.files[0]
      return <li key={finding.id}><span className="native-priorities__rank">{String(index + 1).padStart(2, '0')}</span><div><strong>{finding.title}</strong><p><span className={severityClass(finding.severity)}>{finding.severity === 'info' ? 'signal' : finding.severity}</span>{location && <code>{location}</code>}</p></div></li>
    })}</ol>
  </aside>
}

function ReviewBrief({ job }: { job: AnalysisJob }) {
  const severityRank: Record<FindingSeverity, number> = { critical: 0, high: 1, medium: 2, low: 3, info: 4 }
  const findings = job.reports.flatMap((report) => report.findings).filter(hasFindingEvidence)
  const findingById = new Map(findings.map((finding) => [finding.id, finding]))
  const modelPriority = job.mode === 'native_multi_agent'
    ? job.priorityFindingIds.map((id) => findingById.get(id)).find((finding): finding is Finding => Boolean(finding))
    : undefined
  const finding = modelPriority ?? [...findings].sort((left, right) => severityRank[left.severity] - severityRank[right.severity] || (right.confidence ?? 0) - (left.confidence ?? 0))[0]
  if (!finding) return null
  const evidence = finding.evidence.find((item) => item.path.trim().length > 0)
  const location = evidence ? `${evidence.path}${evidence.lineStart ? ` · line ${evidence.lineStart}` : ' · file-level evidence'}` : finding.files[0]
  const confidence = finding.confidence === undefined ? undefined : Math.round(finding.confidence * 100)
  return <aside className="review-brief" aria-label="Recommended first review signal">
    <div className="review-brief__meta"><p className="eyebrow eyebrow--accent">Start here</p><span>{modelPriority ? 'GPT-5.6 presentation priority' : 'Highest deterministic severity'}</span></div>
    <div className="review-brief__signal"><span className={severityClass(finding.severity)}>{finding.severity === 'info' ? 'signal' : finding.severity}</span><div><h3>{finding.title}</h3><p>{finding.recommendation || finding.detail}</p>{location && <code>Evidence · {location}{confidence !== undefined ? ` · ${confidence}% evidence confidence` : ''}</code>}</div></div>
    <p className="review-brief__scope">A recommended review starting point, not a complete repository verdict. Inspect the linked evidence and the analysis scope before changing code.</p>
  </aside>
}

function MapBranch({ node, depth, onSelect, selectedPath }: { node: RepositoryMapNode; depth: number; onSelect: (node: RepositoryMapNode) => void; selectedPath?: string }) {
  const [expanded, setExpanded] = useState(depth < 1)
  const hasChildren = node.children.length > 0
  return <li className="map-tree__item">
    <div className={`map-tree__row ${selectedPath === node.path ? 'map-tree__row--selected' : ''}`} style={{ paddingLeft: `${depth * 1.05 + .45}rem` }}>
      {hasChildren ? <button type="button" className="tree-toggle" aria-label={`${expanded ? 'Collapse' : 'Expand'} ${node.path}`} onClick={() => setExpanded((value) => !value)}>{expanded ? '−' : '+'}</button> : <span className="tree-leaf" aria-hidden="true">•</span>}
      <button type="button" className="map-tree__name" aria-pressed={selectedPath === node.path} onClick={() => onSelect(node)}><code>{node.path}</code></button>
      <span className={severityClass(node.risk)}>{node.risk === 'info' ? 'safe' : node.risk}</span>
    </div>
    {hasChildren && expanded && <ul>{node.children.map((child) => <MapBranch node={child} depth={depth + 1} key={`${node.path}/${child.path}`} onSelect={onSelect} selectedPath={selectedPath} />)}</ul>}
  </li>
}

function RepositoryMap({ nodes, overview, markdown }: { nodes: RepositoryMapNode[]; overview?: string; markdown?: string }) {
  const [selected, setSelected] = useState<RepositoryMapNode>()
  const preferredNode = useMemo(() => {
    const severityOrder: Record<FindingSeverity, number> = { critical: 0, high: 1, medium: 2, low: 3, info: 4 }
    const flatten = (items: RepositoryMapNode[]): RepositoryMapNode[] => items.flatMap((item) => [item, ...flatten(item.children)])
    return flatten(nodes).sort((left, right) => severityOrder[left.risk] - severityOrder[right.risk])[0]
  }, [nodes])

  useEffect(() => {
    if (!preferredNode) return
    setSelected((current) => {
      if (!current) return preferredNode
      const exists = (items: RepositoryMapNode[]): boolean => items.some((item) => item.path === current.path || exists(item.children))
      return exists(nodes) ? current : preferredNode
    })
  }, [nodes, preferredNode])

  const activeNode = selected ?? preferredNode
  if (!nodes.length && !markdown) return <p className="empty-state">The risk-annotated map will appear when reconciliation finishes.</p>
  if (!nodes.length) return <pre className="markdown-fallback">{markdown}</pre>
  return <div className="map-explorer" aria-label="Interactive risk annotated repository map"><p className="map-overview">{overview || 'The highest-risk evidence-backed path is selected first; choose any path to inspect its context.'}</p><div className="map-tree"><ul>{nodes.map((node) => <MapBranch node={node} depth={0} key={node.path} onSelect={setSelected} selectedPath={activeNode?.path} />)}</ul></div><aside className="map-detail" aria-live="polite"><p className="eyebrow">Selected path</p><strong>{activeNode?.path || 'Path unavailable'}</strong><p>{activeNode?.purpose || 'Each color reflects the highest evidence-backed risk attached to that area.'}</p></aside></div>
}

interface AgentsSection { title: string; body: string }
function parseAgentsSections(markdown?: string): AgentsSection[] {
  if (!markdown) return []
  const sections: AgentsSection[] = []
  let current: AgentsSection = { title: 'Overview', body: '' }
  for (const line of markdown.split('\n')) {
    const heading = line.match(/^#{1,3}\s+(.+)$/)
    if (heading) {
      // A document-level `# AGENTS.md` heading has no useful panel body. Do
      // not turn it into the initially selected empty tab.
      if (current.body.trim()) sections.push(current)
      current = { title: heading[1].trim(), body: '' }
    } else current.body += `${line}\n`
  }
  if (current.body.trim() || !sections.length) sections.push(current)
  return sections
}

function plainMarkdown(value: string): string {
  return value
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/^[-*]\s+/, '')
    .trim()
}

function AgentsSectionContent({ body }: { body: string }) {
  const lines = body.split('\n').map((line) => line.trim()).filter(Boolean)
  return <div className="agents-content">{lines.map((line, index) => {
    const isBullet = /^[-*]\s+/.test(line)
    return <p className={isBullet ? 'agents-content__item' : 'agents-content__text'} key={`${index}-${line}`}>{plainMarkdown(line)}</p>
  })}</div>
}

function AgentsPreview({ markdown }: { markdown?: string }) {
  const sections = useMemo(() => parseAgentsSections(markdown), [markdown])
  const [activeIndex, setActiveIndex] = useState(0)
  useEffect(() => { setActiveIndex(0) }, [sections])
  if (!markdown) return <p className="empty-state">Your concise repository guide is being prepared.</p>
  const selected = sections[activeIndex] ?? sections[0]
  const onTabKeyDown = (event: React.KeyboardEvent<HTMLButtonElement>, index: number) => {
    let nextIndex = index
    if (event.key === 'ArrowRight') nextIndex = (index + 1) % sections.length
    else if (event.key === 'ArrowLeft') nextIndex = (index - 1 + sections.length) % sections.length
    else if (event.key === 'Home') nextIndex = 0
    else if (event.key === 'End') nextIndex = sections.length - 1
    else return
    event.preventDefault()
    setActiveIndex(nextIndex)
    document.getElementById(`agents-tab-${nextIndex}`)?.focus()
  }
  return <div className="agents-navigator"><div className="agents-tabs" role="tablist" aria-label="AGENTS.md sections">{sections.map((section, index) => <button type="button" id={`agents-tab-${index}`} role="tab" tabIndex={index === activeIndex ? 0 : -1} aria-selected={index === activeIndex} aria-controls={`agents-panel-${index}`} className={index === activeIndex ? 'agents-tabs__tab agents-tabs__tab--active' : 'agents-tabs__tab'} onKeyDown={(event) => onTabKeyDown(event, index)} onClick={() => setActiveIndex(index)} key={`${section.title}-${index}`}>{section.title}</button>)}</div><div id={`agents-panel-${activeIndex}`} role="tabpanel" aria-labelledby={`agents-tab-${activeIndex}`} className="agents-preview">{selected?.body.trim() ? <AgentsSectionContent body={selected.body} /> : <AgentsSectionContent body={markdown} />}</div></div>
}

function AgentActivity({ job, agent, index }: { job: AnalysisJob; agent: (typeof AGENTS)[number]; index: number }) {
  const report = reportFor(job, agent.role)
  const event = latestEvent(job, agent.role)
  const state = agentState(job, agent.role)
  const action = report ? 'Completed' : event?.action ?? event?.message ?? (state === 'queued' ? 'Waiting for evidence pack…' : agent.defaultAction)
  const progress = report ? 'Evidence report ready' : metricValue(event) ?? (state === 'queued' ? 'Waiting for evidence' : 'Working from evidence')
  const percent = report ? 100 : event?.percent ?? (event?.current !== undefined && event.total ? Math.round((event.current / event.total) * 100) : undefined)
  const stateLabel = state === 'complete' ? 'Report ready' : state === 'working' ? 'Working from evidence' : state === 'failed' ? 'Stopped safely' : 'Awaiting evidence'
  const liveDetail = event?.phase?.replaceAll('_', ' ') ?? 'specialist review'

  return <article className={`agent-card agent-card--${state}`} aria-label={`${agent.label}: ${stateLabel}`}>
    <span className="agent-card__number">0{index + 1}</span>
    <div className="agent-card__glyph-wrap"><AgentGlyph role={agent.role} />{state === 'working' && <span className="agent-card__activity-ring" aria-hidden="true" />}</div>
    <div className="agent-card__content"><h3>{agent.label}</h3><p className="agent-action">{action}</p><p className="agent-progress">{progress}</p></div>
    <div className="agent-card__status" aria-live="polite"><span className="agent-card__status-dot" aria-hidden="true" />{state === 'working' ? `Live · ${liveDetail}` : stateLabel}</div>
    {percent !== undefined && <div className="agent-progressbar" aria-label={`${percent}% complete`}><i style={{ width: `${Math.min(100, Math.max(0, percent))}%` }} /></div>}
    <span className="step-state" aria-hidden="true">{state === 'complete' ? '✓' : <i />}</span>
  </article>
}

function ReconciliationPanel({ job }: { job: AnalysisJob }) {
  const reconciliation = job.reconciliation
  const hasData = job.reports.length > 0 || reconciliation.decisions.length > 0 || job.events.some((event) => event.phase.toLowerCase().includes('reconcil'))
  const leadDecision = reconciliation.decisions.find((decision) => decision.disposition === 'accepted' || decision.disposition === 'merged') ?? reconciliation.decisions[0]
  const contributorLabels = leadDecision ? AGENTS.filter((agent) => reportFor(job, agent.role)?.findings.some((finding) => leadDecision.findingIds.includes(finding.id))).map((agent) => agent.label) : []
  const masterSummary = isComplete(job)
    ? leadDecision
      ? leadDecision.rationale || `${leadDecision.findingIds.length} evidence-backed finding${leadDecision.findingIds.length === 1 ? '' : 's'} resolved.`
      : 'No conflicting evidence was found; validated specialist signals were carried forward as independent context.'
    : 'Comparing specialist evidence.'
  const decisionStats = [
    { label: 'accepted', value: reconciliation.acceptedCount },
    { label: 'merged', value: reconciliation.mergedCount },
    { label: 'deferred', value: reconciliation.deferredCount },
  ].filter((item) => item.value > 0)
  if (!hasData) return null
  return <section className="reconciliation-panel"><div className="reconciliation-panel__heading"><div><p className="eyebrow eyebrow--accent">Master reconciliation</p><h2>Signals become an engineering decision.</h2></div><div className="decision-counts">{decisionStats.length ? decisionStats.map((item) => <span key={item.label}><strong>{item.value}</strong> {item.label}</span>) : <span><strong>Clear</strong> no conflict</span>}</div></div><div className="reconciliation-flow"><div className="agent-opinions">{AGENTS.map((agent) => <div key={agent.role}><AgentGlyph role={agent.role} /><p><strong>{agent.label} says</strong>{reportFor(job, agent.role)?.summary || 'Evidence is still arriving.'}</p></div>)}</div><div className="master-merge"><span>✦</span><strong>Master</strong><p>{masterSummary}</p>{leadDecision && <small>{contributorLabels.length ? contributorLabels.join(' + ') : 'Specialist evidence'} · {leadDecision.findingIds.length} finding{leadDecision.findingIds.length === 1 ? '' : 's'} considered</small>}</div><div className="decision-list">{reconciliation.decisions.length ? reconciliation.decisions.slice(0, 3).map((decision, index) => <article key={`${decision.disposition}-${index}`}><span className={`decision-badge decision-badge--${decision.disposition}`}>{decision.disposition}</span><p>{decision.rationale || `${decision.findingIds.length} finding${decision.findingIds.length === 1 ? '' : 's'} considered`}</p></article>) : <p className="empty-state">The Master will show accepted, merged, and deferred evidence here.</p>}</div></div><NativePriorities job={job} /></section>
}

function CompletionSummary({ job }: { job: AnalysisJob }) {
  if (!isComplete(job)) return null
  const metrics = job.metrics
  const findings = metrics.findingsPublished || job.reports.reduce((total, report) => total + report.findings.length, 0)
  return <section className="completion-summary" aria-live="polite"><span className="completion-summary__check">✓</span><div><p className="eyebrow">Analysis complete</p><h2>Context is ready for the next coding agent.</h2><p>{metrics.filesAnalyzed || job.repository?.fileCount || 'Bounded'} files analyzed <i>·</i> 4 specialists <i>·</i> {findings} findings <i>·</i> {metrics.artifactsGenerated || 2} artifacts <i>·</i> {formatDuration(metrics.durationMs)}</p></div></section>
}

function FailureRecovery({ job, onRetry, retrying }: { job: AnalysisJob; onRetry: () => void; retrying: boolean }) {
  const detail = job.error || 'RepoMind stopped before it could produce a trusted evidence pack.'
  return <section className="failure-recovery" role="alert" aria-live="assertive"><div><p className="eyebrow">Analysis paused safely</p><h2>Nothing unsupported was presented as a finding.</h2><p>{detail}</p><p className="failure-recovery__hint">Check that the repository is public and reachable, then retry. RepoMind will create a new read-only analysis request.</p></div><button type="button" onClick={onRetry} disabled={retrying || !job.repoUrl}>{retrying ? 'Retrying…' : 'Retry this repository'}</button></section>
}

function RepoMindApp() {
  const [repoUrl, setRepoUrl] = useState('')
  const [job, setJob] = useState<AnalysisJob>()
  const [agentsMarkdown, setAgentsMarkdown] = useState<string>()
  const [mapMarkdown, setMapMarkdown] = useState<string>()
  const [isStarting, setIsStarting] = useState(false)
  const [error, setError] = useState<string>()
  const complete = isComplete(job)
  const failed = isFailed(job)
  const jobId = job?.jobId
  const artifactsWithheld = job?.validation?.artifactsValidated === false

  useEffect(() => {
    if (!jobId || complete || failed) return undefined
    let active = true
    const poll = async () => {
      try {
        const next = await getAnalysis(jobId)
        if (active) { setJob(next); setError(undefined) }
      } catch (pollError) {
        if (active) setError(pollError instanceof Error ? `Connection issue: ${pollError.message}. RepoMind will keep trying.` : 'Connection issue while checking analysis progress. RepoMind will keep trying.')
      }
    }
    const interval = window.setInterval(() => { void poll() }, 1_800)
    void poll()
    return () => { active = false; window.clearInterval(interval) }
  }, [jobId, complete, failed])

  useEffect(() => {
    if (!jobId || complete || failed) return undefined
    const stream = openEventStream(jobId, (event) => {
      if (event.job) { setJob(event.job); return }
      const progress = event.progress
      if (!progress) return
      setJob((current) => {
        if (!current || current.jobId !== jobId) return current
        const duplicate = current.events.some((item) => item.timestamp === progress.timestamp && item.phase === progress.phase && item.role === progress.role && item.action === progress.action && item.percent === progress.percent)
        return duplicate ? current : { ...current, events: [...current.events, progress] }
      })
    })
    return () => stream.close()
  }, [jobId, complete, failed])

  useEffect(() => {
    if (!jobId || !complete || !job || artifactsWithheld) return undefined
    let active = true
    void Promise.all([
      job.artifacts.agentsMd ? Promise.resolve(job.artifacts.agentsMd) : fetchArtifact(jobId, 'AGENTS.md'),
      job.artifacts.repoMap ? Promise.resolve(job.artifacts.repoMap) : fetchArtifact(jobId, 'repo-map.md'),
    ]).then(([agents, map]) => { if (active) { setAgentsMarkdown(agents); setMapMarkdown(map) } }).catch((artifactError: unknown) => {
      if (active) setError(artifactError instanceof Error ? artifactError.message : 'Could not load generated artifacts.')
    })
    return () => { active = false }
  }, [jobId, complete, job, artifactsWithheld])

  async function startAnalysis(candidateUrl: string) {
    const urlError = validatePublicGitHubUrl(candidateUrl)
    if (urlError) { setError(urlError); return }
    const normalizedUrl = candidateUrl.trim()
    setError(undefined); setAgentsMarkdown(undefined); setMapMarkdown(undefined); setIsStarting(true); setJob(undefined)
    try { setJob(await createAnalysis(normalizedUrl)) }
    catch (requestError) { setError(requestError instanceof Error ? requestError.message : 'The analysis could not be started.') }
    finally { setIsStarting(false) }
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    void startAnalysis(repoUrl)
  }

  function retryAnalysis() {
    const retryUrl = job?.repoUrl ?? repoUrl
    if (!retryUrl) return
    setRepoUrl(retryUrl)
    void startAnalysis(retryUrl)
  }

  const busy = isStarting || Boolean(job && !complete && !failed)
  const artifactAgents = job ? getArtifactUrl(job.jobId, 'AGENTS.md') : '#'
  const artifactMap = job ? getArtifactUrl(job.jobId, 'repo-map.md') : '#'
  const title = repositoryLabel(job)

  return <main className="repomind-shell">
    <header className="site-header"><a className="brand" href="#top" aria-label="RepoMind home"><BrandMark /><span>RepoMind</span></a><p className="header-note"><span className="header-note__dot" aria-hidden="true" /> Evidence-first change preflight</p></header>
    <section className="hero" id="top"><div><p className="eyebrow eyebrow--accent">Change preflight for coding agents</p><h1>Before you delegate a ticket, give the agent the repository’s rules.</h1><p className="hero-lede">RepoMind turns an unfamiliar repository into a checked operating brief: what to read first, where risk sits, what tests matter, and how to verify the change—before the first edit.</p><div className="hero-proof" aria-label="RepoMind change-preflight outcomes"><span>Read first</span><span>Avoid risky paths</span><span>Verify the change</span></div></div><aside className="hero-story" aria-label="How RepoMind helps a change handoff"><p className="eyebrow">Monday-morning handoff</p><div><span>Ticket: fix a race condition in auth</span><strong>RepoMind does not write the fix.</strong></div><div className="hero-story__with"><span>Before the agent starts</span><strong>Give it observed architecture, risk boundaries, test signals, and a verification checklist.</strong></div><div className="hero-story__trace" aria-label="Repository evidence becomes an agent handoff"><span>Repository</span><i aria-hidden="true" /><span>Evidence</span><i aria-hidden="true" /><strong>AGENTS.md</strong></div></aside></section>
    <section className="launch-panel" aria-labelledby="analyze-heading"><div><p className="eyebrow">Create a change preflight</p><h2 id="analyze-heading">Brief the repository before the ticket.</h2><p>Download the evidence-backed handoff, add it beside the code, then let your IDE agent begin with shared constraints.</p></div><form className="repo-form" onSubmit={submit}><label htmlFor="repo-url">Public GitHub repository to brief</label><div className="repo-form__controls"><span aria-hidden="true">⌁</span><input id="repo-url" type="url" inputMode="url" autoComplete="url" placeholder="https://github.com/owner/repository" value={repoUrl} onChange={(event) => setRepoUrl(event.target.value)} disabled={busy} aria-describedby={error ? 'form-error' : 'repo-hint'} /><button type="submit" disabled={busy}>{isStarting ? 'Launching…' : busy ? 'Analysis running' : 'Create preflight'}</button></div><div className="form-assist"><p className="form-hint" id="repo-hint">Public repositories only. RepoMind reads a bounded evidence pack and never modifies the source repository.</p><button type="button" className="repo-form__example" onClick={() => setRepoUrl('https://github.com/pallets/flask')} disabled={busy}>Use Flask demo</button></div></form>{error && <p className="form-error" id="form-error" role="alert">{error}</p>}</section>
    <section className="orchestration-zone" aria-live="polite"><div className="orchestration-zone__heading"><div><p className="eyebrow">Visible orchestration</p><h2>{job ? title : 'A brief your IDE agent can use—not another dashboard to watch.'}</h2>{job?.repoUrl && <p className="repository-url">{job.repoUrl}</p>}</div>{job && <div className="session-meta"><span className={`status-chip status-chip--${job.status}`}>{STATUS_LABELS[job.status] ?? job.status}</span><span className={`mode-chip ${job.mode === 'native_multi_agent' ? 'mode-chip--native' : ''}`}>{modeLabel(job.mode)}</span></div>}</div><Pipeline job={job} />{job && <>{job.error && <p className="job-error" role="alert">{job.error}</p>}{complete || job.metrics.filesAnalyzed > 0 || job.metrics.manifestsFound > 0 || job.metrics.testsDiscovered > 0 || job.metrics.commitsInspected > 0 ? <div className="evidence-summary"><EvidenceMetric value={job.metrics.filesAnalyzed || job.repository?.fileCount || 0} label="files analyzed" pending={evidenceActivity(job)} complete={complete} /><EvidenceMetric value={job.metrics.manifestsFound} label="manifests" pending={evidenceActivity(job)} complete={complete} /><EvidenceMetric value={job.metrics.testsDiscovered} label="test files found" pending={evidenceActivity(job)} complete={complete} /><EvidenceMetric value={job.metrics.commitsInspected} label="commits read" pending={evidenceActivity(job)} complete={complete} /></div> : <div className="evidence-summary evidence-summary--pending"><div className="evidence-summary__stage"><span className="evidence-summary__number">{evidenceActivity(job)}</span><span>Evidence pack · in progress</span></div><p>RepoMind will publish counts only after it has observed bounded repository evidence.</p></div>}<div className="agent-timeline">{AGENTS.map((agent, index) => <AgentActivity job={job} agent={agent} index={index} key={agent.role} />)}</div></>}</section>
    {job && failed && <FailureRecovery job={job} onRetry={retryAnalysis} retrying={isStarting} />}
    {job && <TrustPanel job={job} />}
    {job && <ReconciliationPanel job={job} />}
    {job && (job.reports.length > 0 || complete) && <section className="reports-section"><div className="section-heading"><div><p className="eyebrow">Specialist evidence</p><h2>Every recommendation carries its proof.</h2></div><p className="section-aside">Severity, confidence, evidence path, line number, and reason travel together. Confidence reflects captured-evidence support—not a guarantee that unscanned code is safe.</p></div><ReviewBrief job={job} /><div className="report-grid">{AGENTS.map((agent) => <ReportCard key={agent.role} agent={agent} report={reportFor(job, agent.role)} />)}</div></section>}
    {job && (complete || mapMarkdown || agentsMarkdown) && <><CompletionSummary job={job} /><section className="artifacts-section"><div className="section-heading"><div><p className="eyebrow">Take the brief back to the codebase</p><h2>Artifacts for the next person—or agent—to touch the code.</h2></div>{job.mode && <p className="mode-explainer">{job.mode === 'native_multi_agent' ? 'GPT-5.6 native synthesis is connected.' : 'Evidence Mode is using deterministic reconciliation.'}</p>}</div><div className="artifact-grid"><article className="artifact-card"><div className="artifact-card__top"><div><p className="eyebrow">Repository map</p><h3>Interactive risk topology</h3></div><span className="artifact-icon" aria-hidden="true">⌘</span></div><RepositoryMap nodes={job.artifacts.repoMapNodes} overview={job.artifacts.repoMapOverview} markdown={mapMarkdown} /><div className="legend"><span><i className="severity severity--critical" /> critical</span><span><i className="severity severity--high" /> high</span><span><i className="severity severity--medium" /> medium</span><span><i className="severity severity--info" /> safe</span></div><a className="download-link" href={artifactMap} download>Download repo-map.md <span aria-hidden="true">↓</span></a></article><article className="artifact-card artifact-card--agents"><div className="artifact-card__top"><div><p className="eyebrow">AGENTS.md</p><h3>Agent-ready operating context</h3></div><span className="artifact-icon" aria-hidden="true">✦</span></div><AgentsPreview markdown={agentsMarkdown} /><a className="download-link" href={artifactAgents} download>Download AGENTS.md <span aria-hidden="true">↓</span></a></article></div></section></>}
    <footer className="site-footer"><span>RepoMind / Evidence-first change preflight</span><span>Complements your IDE; it does not replace it.</span></footer>
  </main>
}

export default RepoMindApp
