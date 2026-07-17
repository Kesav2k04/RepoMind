import { useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import { ApiError, createAnalysis, fetchArtifact, getAnalysis, getArtifactUrl, openEventStream } from './api'
import type { AgentRole, AnalysisJob, Finding, SpecialistReport } from './types'
import './RepoMind.css'

const AGENTS: Array<{ role: AgentRole; label: string; description: string; glyph: string }> = [
  { role: 'architecture', label: 'Architecture', description: 'Maps entry points and boundaries.', glyph: '⌘' },
  { role: 'risk', label: 'Risk', description: 'Surfaces fragile and exposed areas.', glyph: '!' },
  { role: 'testing', label: 'Test coverage', description: 'Finds verification gaps.', glyph: '✓' },
  { role: 'history', label: 'History', description: 'Traces churn and change context.', glyph: '↗' },
]

const STATUS_LABELS: Record<string, string> = { queued: 'Queued', pending: 'Queued', running: 'Analyzing', reconciling: 'Reconciling', completed: 'Complete', complete: 'Complete', failed: 'Needs attention' }

function reportFor(job: AnalysisJob, role: AgentRole): SpecialistReport | undefined { return job.reports.find((report) => report.role === role) }
function modeLabel(mode?: string): string { return mode === 'native_multi_agent' ? 'Native multi-agent' : 'Evidence fallback' }
function severityClass(severity: Finding['severity']): string { return `severity severity--${severity}` }

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

function agentState(job: AnalysisJob, role: AgentRole): string {
  if (reportFor(job, role)) return 'complete'
  if (job.status === 'queued') return 'queued'
  if (job.status === 'failed') return 'failed'
  return job.agentStatus[role] ?? (job.events.some((event) => event.role === role) ? 'working' : 'queued')
}

function latestProgress(job: AnalysisJob): string | undefined {
  return job.events.at(-1)?.message
}

function RepositoryMap({ markdown }: { markdown?: string }) {
  const lines = useMemo(() => (markdown ?? '').split('\n').map((line) => {
    const result = line.match(/^(\s*)[-*+]\s+(?:\[(critical|high|medium|low|info)\]\s*)?`?([^`\n]+?)`?\s*(?:[-–—:].*)?$/i)
    return result ? { depth: Math.floor(result[1].replace(/\t/g, '  ').length / 2), severity: result[2]?.toLowerCase(), path: result[3].trim() } : undefined
  }).filter(Boolean).slice(0, 32), [markdown]) as Array<{ depth: number; severity?: string; path: string }>
  if (!markdown) return <p className="empty-state">The risk-annotated map will appear when reconciliation finishes.</p>
  return <div className="map-view" aria-label="Risk annotated repository map">{lines.length ? lines.map((line, index) => <div className="map-row" key={`${line.path}-${index}`} style={{ paddingLeft: `${line.depth * 1.1}rem` }}><span className="tree-branch" aria-hidden="true">{line.depth ? '└' : '⌞'}</span><code>{line.path}</code>{line.severity && <span className={severityClass(line.severity as Finding['severity'])}>{line.severity}</span>}</div>) : <pre className="markdown-fallback">{markdown}</pre>}</div>
}

function FindingRow({ finding }: { finding: Finding }) {
  return <article className="finding-row"><span className={severityClass(finding.severity)}>{finding.severity === 'info' ? 'signal' : finding.severity}</span><div><h4>{finding.title}</h4>{finding.detail && <p>{finding.detail}</p>}{finding.files.length > 0 && <div className="file-tags">{finding.files.slice(0, 3).map((file) => <code key={file}>{file}</code>)}</div>}</div></article>
}

function ReportCard({ report, agent }: { report?: SpecialistReport; agent: (typeof AGENTS)[number] }) {
  const findings = report?.findings.slice(0, 3) ?? []
  return <article className="report-card"><div className="report-card__heading"><span className="agent-glyph" aria-hidden="true">{agent.glyph}</span><div><p className="eyebrow">{agent.label}</p><h3>{report?.summary || agent.description}</h3></div>{report?.confidence !== undefined && <span className="confidence">{Math.round(report.confidence * 100)}%</span>}</div>{findings.length ? <div className="finding-list">{findings.map((finding) => <FindingRow finding={finding} key={finding.id} />)}</div> : <p className="card-empty">No evidence-backed findings published yet.</p>}</article>
}

function RepoMindApp() {
  const [repoUrl, setRepoUrl] = useState('')
  const [job, setJob] = useState<AnalysisJob>()
  const [agentsMarkdown, setAgentsMarkdown] = useState<string>()
  const [mapMarkdown, setMapMarkdown] = useState<string>()
  const [isStarting, setIsStarting] = useState(false)
  const [error, setError] = useState<string>()
  const complete = job?.status === 'completed' || job?.status === 'complete'
  const failed = job?.status === 'failed'
  const jobId = job?.jobId

  useEffect(() => {
    if (!jobId || complete || failed) return undefined
    let active = true
    const poll = async () => {
      try { const next = await getAnalysis(jobId); if (active) setJob(next) }
      catch (pollError) { if (active && pollError instanceof ApiError && pollError.status >= 500) setError(pollError.message) }
    }
    const interval = window.setInterval(() => { void poll() }, 1800)
    void poll()
    return () => { active = false; window.clearInterval(interval) }
  }, [jobId, complete, failed])

  useEffect(() => {
    if (!jobId || complete || failed) return undefined
    const stream = openEventStream(jobId, (event) => {
      if (event.job) { setJob(event.job); return }
      if (event.progress) {
        const progress = event.progress
        setJob((current) => {
          if (!current || current.jobId !== jobId) return current
          const duplicate = current.events.some((item) => item.timestamp === progress.timestamp && item.phase === progress.phase && item.role === progress.role)
          return duplicate ? current : { ...current, events: [...current.events, progress] }
        })
      }
    })
    return () => stream.close()
  }, [jobId, complete, failed])

  useEffect(() => {
    if (!jobId || !complete || !job) return undefined
    let active = true
    void Promise.all([
      job.artifacts.agentsMd ? Promise.resolve(job.artifacts.agentsMd) : fetchArtifact(jobId, 'AGENTS.md'),
      job.artifacts.repoMap ? Promise.resolve(job.artifacts.repoMap) : fetchArtifact(jobId, 'repo-map.md'),
    ]).then(([agents, map]) => { if (active) { setAgentsMarkdown(agents); setMapMarkdown(map) } }).catch((artifactError: unknown) => {
      if (active) setError(artifactError instanceof Error ? artifactError.message : 'Could not load generated artifacts.')
    })
    return () => { active = false }
  }, [jobId, complete, job])

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const urlError = validatePublicGitHubUrl(repoUrl)
    if (urlError) { setError(urlError); return }
    setError(undefined); setAgentsMarkdown(undefined); setMapMarkdown(undefined); setIsStarting(true)
    try { setJob(await createAnalysis(repoUrl.trim())) }
    catch (requestError) { setError(requestError instanceof Error ? requestError.message : 'The analysis could not be started.') }
    finally { setIsStarting(false) }
  }

  const busy = isStarting || Boolean(job && !complete && !failed)
  const artifactAgents = job ? getArtifactUrl(job.jobId, 'AGENTS.md') : '#'
  const artifactMap = job ? getArtifactUrl(job.jobId, 'repo-map.md') : '#'
  return <main className="repomind-shell">
    <header className="site-header"><a className="brand" href="#top" aria-label="RepoMind home"><span className="brand-mark" aria-hidden="true"><i></i><i></i><i></i></span><span>RepoMind</span></a><p className="header-note"><span className="live-dot"></span> Agentic repository intelligence</p></header>
    <section className="hero" id="top"><div><p className="eyebrow eyebrow--accent">OpenAI Build Week project</p><h1>Turn an unfamiliar codebase into an informed next move.</h1><p className="hero-lede">Four specialized agents trace a repository’s architecture, risk, tests, and history—then reconcile the evidence into context future coding agents can use.</p></div><div className="hero-console" aria-label="Analysis workflow"><div className="console-topline"><span>REPOSITORY INTELLIGENCE</span><span>01 / 01</span></div><div className="console-flow"><span className="console-node">repo</span><span>→</span><span className="console-node console-node--active">evidence</span><span>→</span><span className="console-node">action</span></div><p>Grounded findings. Shareable engineering context.</p></div></section>
    <section className="launch-panel" aria-labelledby="analyze-heading"><div><p className="eyebrow">Start an analysis</p><h2 id="analyze-heading">Bring a public GitHub repository.</h2></div><form className="repo-form" onSubmit={submit}><label htmlFor="repo-url">Repository URL</label><div className="repo-form__controls"><span aria-hidden="true">↗</span><input id="repo-url" type="url" inputMode="url" autoComplete="url" placeholder="https://github.com/owner/repository" value={repoUrl} onChange={(event) => setRepoUrl(event.target.value)} disabled={busy} aria-describedby={error ? 'form-error' : 'repo-hint'} /><button type="submit" disabled={busy}>{isStarting ? 'Launching…' : busy ? 'Analysis running' : 'Analyze repository'}</button></div><p className="form-hint" id="repo-hint">Public repositories only. RepoMind reads a bounded evidence pack and never modifies the source repository.</p></form>{error && <p className="form-error" id="form-error" role="alert">{error}</p>}</section>
    {job ? <section className="analysis-zone" aria-live="polite"><div className="section-heading"><div><p className="eyebrow">Analysis session</p><h2>{job.repositoryName || job.repoUrl || 'Repository analysis'}</h2></div><div className="session-meta"><span className={`status-chip status-chip--${job.status}`}>{STATUS_LABELS[job.status] ?? job.status}</span>{job.mode && <span className="mode-chip">{modeLabel(job.mode)}</span>}</div></div>{job.error && <p className="job-error" role="alert">{job.error}</p>}<div className="agent-timeline">{AGENTS.map((agent, index) => { const done = Boolean(reportFor(job, agent.role)); const state = agentState(job, agent.role); return <div className="agent-step" key={agent.role}><article className={`agent-card agent-card--${state}`}><span className="agent-card__number">0{index + 1}</span><span className="agent-glyph" aria-hidden="true">{agent.glyph}</span><div><h3>{agent.label}</h3><p>{done ? 'Evidence report ready' : state === 'queued' ? 'Waiting for evidence' : 'Reviewing repository'}</p></div><span className="step-state" aria-label={state}>{done ? '✓' : <i />}</span></article>{index < AGENTS.length - 1 && <span className="timeline-link" aria-hidden="true" />}</div> })}</div><div className="reconciliation-line"><span className={complete ? 'reconcile-icon reconcile-icon--done' : 'reconcile-icon'}>âœ¦</span><p><strong>{complete ? 'Reconciliation complete.' : 'Reconciliation waits for specialist evidence.'}</strong> {job.summary || latestProgress(job) || 'The final pass deduplicates findings and builds agent-ready artifacts.'}</p></div></section> : <section className="value-strip" aria-label="What RepoMind analyzes">{AGENTS.map((agent) => <div key={agent.role}><span className="agent-glyph" aria-hidden="true">{agent.glyph}</span><p><strong>{agent.label}</strong>{agent.description}</p></div>)}</section>}
    {job && (job.reports.length > 0 || complete) && <section className="reports-section"><div className="section-heading"><div><p className="eyebrow">Specialist evidence</p><h2>Findings worth carrying forward.</h2></div><p className="section-aside">Every meaningful signal is anchored to a repository path.</p></div><div className="report-grid">{AGENTS.map((agent) => <ReportCard key={agent.role} agent={agent} report={reportFor(job, agent.role)} />)}</div></section>}
    {job && (complete || mapMarkdown || agentsMarkdown) && <section className="artifacts-section"><div className="section-heading"><div><p className="eyebrow">Generated context</p><h2>Artifacts for the next person—or agent—to touch the code.</h2></div>{job.mode && <p className="mode-explainer">Built with <strong>{modeLabel(job.mode).toLowerCase()}</strong>.</p>}</div><div className="artifact-grid"><article className="artifact-card"><div className="artifact-card__top"><div><p className="eyebrow">Repository map</p><h3>Risk-annotated topology</h3></div><span className="artifact-icon" aria-hidden="true">⌘</span></div><RepositoryMap markdown={mapMarkdown} /><div className="legend"><span><i className="severity severity--critical"></i> critical</span><span><i className="severity severity--high"></i> high</span><span><i className="severity severity--medium"></i> medium</span></div><a className="download-link" href={artifactMap} download>Download repo-map.md <span aria-hidden="true">↓</span></a></article><article className="artifact-card artifact-card--agents"><div className="artifact-card__top"><div><p className="eyebrow">AGENTS.md</p><h3>Agent-ready operating context</h3></div><span className="artifact-icon" aria-hidden="true">✦</span></div>{agentsMarkdown ? <pre className="agents-preview">{agentsMarkdown}</pre> : <p className="empty-state">Your concise repository guide is being prepared.</p>}<a className="download-link" href={artifactAgents} download>Download AGENTS.md <span aria-hidden="true">↓</span></a></article></div></section>}
    <footer className="site-footer"><span>RepoMind / Evidence-first repository intelligence</span><span>Designed for context, not noise.</span></footer>
  </main>
}

export default RepoMindApp
