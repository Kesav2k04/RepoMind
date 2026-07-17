import { useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import { createAnalysis, fetchArtifact, getAnalysis, getArtifactUrl, openEventStream } from './api'
import type { AgentRole, AnalysisJob, Finding, FindingSeverity, ProgressEvent, RepositoryMapNode, SpecialistReport } from './types'
import './RepoMind.css'

const AGENTS: Array<{ role: AgentRole; label: string; description: string; glyph: string; defaultAction: string }> = [
  { role: 'architecture', label: 'Architecture', description: 'Maps entry points and boundaries.', glyph: '⌘', defaultAction: 'Finding entry points…' },
  { role: 'risk', label: 'Risk', description: 'Surfaces fragile and exposed areas.', glyph: '!', defaultAction: 'Checking dependencies…' },
  { role: 'testing', label: 'Testing', description: 'Finds verification gaps.', glyph: '✓', defaultAction: 'Discovering tests…' },
  { role: 'history', label: 'History', description: 'Traces churn and change context.', glyph: '↗', defaultAction: 'Reading commits…' },
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

  return <section className="pipeline" aria-label="RepoMind orchestration pipeline">
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
    <div className="finding-row__meta"><span className={severityClass(finding.severity)}>{finding.severity === 'info' ? 'signal' : finding.severity}</span>{confidence !== undefined && <span className="finding-confidence">{confidence}% confidence</span>}</div>
    <div className="finding-row__content"><h4>{finding.title}</h4>{finding.detail && <p>{finding.detail}</p>}{location && <div className="evidence-line"><span>Evidence</span><code>{location}</code></div>}{evidence?.reason && <p className="finding-reason"><strong>Reason:</strong> {evidence.reason}</p>}{evidence?.excerpt && <code className="evidence-excerpt">{evidence.excerpt}</code>}{finding.recommendation && <p className="finding-recommendation">{finding.recommendation}</p>}</div>
  </article>
}

function ReportCard({ report, agent }: { report?: SpecialistReport; agent: (typeof AGENTS)[number] }) {
  const findings = report?.findings ?? []
  return <article className="report-card"><div className="report-card__heading"><span className="agent-glyph" aria-hidden="true">{agent.glyph}</span><div><p className="eyebrow">{agent.label}</p><h3>{report?.summary || agent.description}</h3></div>{report?.confidence !== undefined && <span className="confidence">{Math.round(report.confidence * 100)}% confidence</span>}</div>{findings.length ? <div className="finding-list">{findings.map((finding) => <FindingRow finding={finding} key={finding.id} />)}</div> : <p className="card-empty">No evidence-backed findings published yet.</p>}</article>
}

function MapBranch({ node, depth, onSelect, selectedPath }: { node: RepositoryMapNode; depth: number; onSelect: (node: RepositoryMapNode) => void; selectedPath?: string }) {
  const [expanded, setExpanded] = useState(depth < 1)
  const hasChildren = node.children.length > 0
  return <li className="map-tree__item">
    <div className={`map-tree__row ${selectedPath === node.path ? 'map-tree__row--selected' : ''}`} style={{ paddingLeft: `${depth * 1.05 + .45}rem` }}>
      {hasChildren ? <button type="button" className="tree-toggle" aria-label={`${expanded ? 'Collapse' : 'Expand'} ${node.path}`} onClick={() => setExpanded((value) => !value)}>{expanded ? '−' : '+'}</button> : <span className="tree-leaf" aria-hidden="true">•</span>}
      <button type="button" className="map-tree__name" onClick={() => onSelect(node)}><code>{node.path}</code></button>
      <span className={severityClass(node.risk)}>{node.risk === 'info' ? 'safe' : node.risk}</span>
    </div>
    {hasChildren && expanded && <ul>{node.children.map((child) => <MapBranch node={child} depth={depth + 1} key={`${node.path}/${child.path}`} onSelect={onSelect} selectedPath={selectedPath} />)}</ul>}
  </li>
}

function RepositoryMap({ nodes, overview, markdown }: { nodes: RepositoryMapNode[]; overview?: string; markdown?: string }) {
  const [selected, setSelected] = useState<RepositoryMapNode>()
  if (!nodes.length && !markdown) return <p className="empty-state">The risk-annotated map will appear when reconciliation finishes.</p>
  if (!nodes.length) return <pre className="markdown-fallback">{markdown}</pre>
  return <div className="map-explorer" aria-label="Interactive risk annotated repository map"><p className="map-overview">{overview || 'Select a path to see the evidence-backed repository context.'}</p><div className="map-tree"><ul>{nodes.map((node) => <MapBranch node={node} depth={0} key={node.path} onSelect={setSelected} selectedPath={selected?.path} />)}</ul></div><aside className="map-detail"><p className="eyebrow">Selected path</p><strong>{selected?.path || 'Choose a path'}</strong><p>{selected?.purpose || 'Each color reflects the highest evidence-backed risk attached to that area.'}</p></aside></div>
}

interface AgentsSection { title: string; body: string }
function parseAgentsSections(markdown?: string): AgentsSection[] {
  if (!markdown) return []
  const sections: AgentsSection[] = []
  let current: AgentsSection = { title: 'Overview', body: '' }
  for (const line of markdown.split('\n')) {
    const heading = line.match(/^#{1,3}\s+(.+)$/)
    if (heading) {
      if (current.body.trim() || current.title !== 'Overview') sections.push(current)
      current = { title: heading[1].trim(), body: '' }
    } else current.body += `${line}\n`
  }
  if (current.body.trim() || !sections.length) sections.push(current)
  return sections
}

function AgentsPreview({ markdown }: { markdown?: string }) {
  const sections = useMemo(() => parseAgentsSections(markdown), [markdown])
  const [active, setActive] = useState('Overview')
  useEffect(() => { setActive(sections[0]?.title ?? 'Overview') }, [sections])
  if (!markdown) return <p className="empty-state">Your concise repository guide is being prepared.</p>
  const selected = sections.find((section) => section.title === active) ?? sections[0]
  return <div className="agents-navigator"><div className="agents-tabs" role="tablist" aria-label="AGENTS.md sections">{sections.map((section) => <button type="button" role="tab" aria-selected={section.title === selected?.title} className={section.title === selected?.title ? 'agents-tabs__tab agents-tabs__tab--active' : 'agents-tabs__tab'} onClick={() => setActive(section.title)} key={section.title}>{section.title}</button>)}</div><pre className="agents-preview">{selected?.body.trim() || markdown}</pre></div>
}

function AgentActivity({ job, agent, index }: { job: AnalysisJob; agent: (typeof AGENTS)[number]; index: number }) {
  const report = reportFor(job, agent.role)
  const event = latestEvent(job, agent.role)
  const state = agentState(job, agent.role)
  const action = report ? 'Completed' : event?.action ?? event?.message ?? agent.defaultAction
  const progress = report ? 'Evidence report ready' : metricValue(event) ?? (state === 'queued' ? 'Waiting for evidence' : 'Working from evidence')
  const percent = report ? 100 : event?.percent ?? (event?.current !== undefined && event.total ? Math.round((event.current / event.total) * 100) : undefined)
  return <article className={`agent-card agent-card--${state}`}><span className="agent-card__number">0{index + 1}</span><span className="agent-glyph" aria-hidden="true">{agent.glyph}</span><div className="agent-card__content"><h3>{agent.label}</h3><p className="agent-action">{action}</p><p className="agent-progress">{progress}</p></div>{percent !== undefined && <div className="agent-progressbar" aria-label={`${percent}% complete`}><i style={{ width: `${Math.min(100, Math.max(0, percent))}%` }} /></div>}<span className="step-state" aria-label={state}>{state === 'complete' ? '✓' : <i />}</span></article>
}

function ReconciliationPanel({ job }: { job: AnalysisJob }) {
  const reconciliation = job.reconciliation
  const hasData = job.reports.length > 0 || reconciliation.decisions.length > 0 || job.events.some((event) => event.phase.toLowerCase().includes('reconcil'))
  if (!hasData) return null
  return <section className="reconciliation-panel"><div className="reconciliation-panel__heading"><div><p className="eyebrow eyebrow--accent">Master reconciliation</p><h2>Signals become an engineering decision.</h2></div><div className="decision-counts"><span><strong>{reconciliation.acceptedCount}</strong> accepted</span><span><strong>{reconciliation.mergedCount}</strong> merged</span><span><strong>{reconciliation.deferredCount}</strong> deferred</span></div></div><div className="reconciliation-flow"><div className="agent-opinions">{AGENTS.map((agent) => <div key={agent.role}><span className="agent-glyph" aria-hidden="true">{agent.glyph}</span><p><strong>{agent.label} says</strong>{reportFor(job, agent.role)?.summary || 'Evidence is still arriving.'}</p></div>)}</div><div className="master-merge"><span>✦</span><strong>Master</strong><p>{isComplete(job) ? 'Merged the evidence into the final report.' : 'Comparing specialist evidence.'}</p></div><div className="decision-list">{reconciliation.decisions.length ? reconciliation.decisions.slice(0, 3).map((decision, index) => <article key={`${decision.disposition}-${index}`}><span className={`decision-badge decision-badge--${decision.disposition}`}>{decision.disposition}</span><p>{decision.rationale || `${decision.findingIds.length} finding${decision.findingIds.length === 1 ? '' : 's'} considered`}</p></article>) : <p className="empty-state">The Master will show accepted, merged, and deferred evidence here.</p>}</div></div></section>
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
    <header className="site-header"><a className="brand" href="#top" aria-label="RepoMind home"><span className="brand-mark" aria-hidden="true"><i /><i /><i /></span><span>RepoMind</span></a><p className="header-note"><span className="live-dot" /> Agentic repository intelligence</p></header>
    <section className="hero" id="top"><div><p className="eyebrow eyebrow--accent">OpenAI Build Week · Developer tools</p><h1>Give any GitHub repository an AI engineering review.</h1><p className="hero-lede">RepoMind turns unknown code into safe, usable context—architecture, risks, test strategy, and conventions—before an AI coding agent touches a line.</p></div><div className="hero-story"><p className="eyebrow">Why AGENTS.md matters</p><div><span>Without RepoMind</span><strong>AI starts coding blindly.</strong></div><div className="hero-story__with"><span>With RepoMind</span><strong>AI begins with architecture, risks, tests, and verification.</strong></div></div></section>
    <section className="launch-panel" aria-labelledby="analyze-heading"><div><p className="eyebrow">Start an analysis</p><h2 id="analyze-heading">Bring a public GitHub repository.</h2></div><form className="repo-form" onSubmit={submit}><label htmlFor="repo-url">Repository URL</label><div className="repo-form__controls"><span aria-hidden="true">↗</span><input id="repo-url" type="url" inputMode="url" autoComplete="url" placeholder="https://github.com/owner/repository" value={repoUrl} onChange={(event) => setRepoUrl(event.target.value)} disabled={busy} aria-describedby={error ? 'form-error' : 'repo-hint'} /><button type="submit" disabled={busy}>{isStarting ? 'Launching…' : busy ? 'Analysis running' : 'Analyze repository'}</button></div><p className="form-hint" id="repo-hint">Public repositories only. RepoMind reads a bounded evidence pack and never modifies the source repository.</p></form>{error && <p className="form-error" id="form-error" role="alert">{error}</p>}</section>
    <section className="orchestration-zone" aria-live="polite"><div className="orchestration-zone__heading"><div><p className="eyebrow">Visible orchestration</p><h2>{job ? title : 'A clear path from repository to safe context.'}</h2>{job?.repoUrl && <p className="repository-url">{job.repoUrl}</p>}</div>{job && <div className="session-meta"><span className={`status-chip status-chip--${job.status}`}>{STATUS_LABELS[job.status] ?? job.status}</span><span className={`mode-chip ${job.mode === 'native_multi_agent' ? 'mode-chip--native' : ''}`}>{modeLabel(job.mode)}</span></div>}</div><Pipeline job={job} />{job && <>{job.error && <p className="job-error" role="alert">{job.error}</p>}<div className="evidence-summary"><div><span className="evidence-summary__number">{job.metrics.filesAnalyzed || job.repository?.fileCount || '—'}</span><span>files analyzed</span></div><div><span className="evidence-summary__number">{job.metrics.manifestsFound || '—'}</span><span>manifests</span></div><div><span className="evidence-summary__number">{job.metrics.testsDiscovered || '—'}</span><span>tests discovered</span></div><div><span className="evidence-summary__number">{job.metrics.commitsInspected || '—'}</span><span>commits read</span></div></div><div className="agent-timeline">{AGENTS.map((agent, index) => <AgentActivity job={job} agent={agent} index={index} key={agent.role} />)}</div></>}</section>
    {job && failed && <FailureRecovery job={job} onRetry={retryAnalysis} retrying={isStarting} />}
    {job && <TrustPanel job={job} />}
    {job && <ReconciliationPanel job={job} />}
    {job && (job.reports.length > 0 || complete) && <section className="reports-section"><div className="section-heading"><div><p className="eyebrow">Specialist evidence</p><h2>Every recommendation carries its proof.</h2></div><p className="section-aside">Severity, confidence, evidence path, line number, and reason travel together.</p></div><div className="report-grid">{AGENTS.map((agent) => <ReportCard key={agent.role} agent={agent} report={reportFor(job, agent.role)} />)}</div></section>}
    {job && (complete || mapMarkdown || agentsMarkdown) && <><CompletionSummary job={job} /><section className="artifacts-section"><div className="section-heading"><div><p className="eyebrow">Generated context</p><h2>Artifacts for the next person—or agent—to touch the code.</h2></div>{job.mode && <p className="mode-explainer">{job.mode === 'native_multi_agent' ? 'GPT-5.6 native synthesis is connected.' : 'Evidence Mode is using deterministic reconciliation.'}</p>}</div><div className="artifact-grid"><article className="artifact-card"><div className="artifact-card__top"><div><p className="eyebrow">Repository map</p><h3>Interactive risk topology</h3></div><span className="artifact-icon" aria-hidden="true">⌘</span></div><RepositoryMap nodes={job.artifacts.repoMapNodes} overview={job.artifacts.repoMapOverview} markdown={mapMarkdown} /><div className="legend"><span><i className="severity severity--critical" /> critical</span><span><i className="severity severity--high" /> high</span><span><i className="severity severity--medium" /> medium</span><span><i className="severity severity--info" /> safe</span></div><a className="download-link" href={artifactMap} download>Download repo-map.md <span aria-hidden="true">↓</span></a></article><article className="artifact-card artifact-card--agents"><div className="artifact-card__top"><div><p className="eyebrow">AGENTS.md</p><h3>Agent-ready operating context</h3></div><span className="artifact-icon" aria-hidden="true">✦</span></div><AgentsPreview markdown={agentsMarkdown} /><a className="download-link" href={artifactAgents} download>Download AGENTS.md <span aria-hidden="true">↓</span></a></article></div></section></>}
    <footer className="site-footer"><span>RepoMind / Evidence-first repository intelligence</span><span>Designed for context, not noise.</span></footer>
  </main>
}

export default RepoMindApp
