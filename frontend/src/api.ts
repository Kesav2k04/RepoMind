import type { AgentRole, AnalysisJob, Finding, JobEvent, ProgressEvent, SpecialistReport } from './types'

const apiBase = (import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000').replace(/\/$/, '')

export class ApiError extends Error {
  readonly status: number

  constructor(message: string, status = 0) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

function endpoint(path: string): string {
  return `${apiBase}${path}`
}

function record(value: unknown): Record<string, unknown> {
  return typeof value === 'object' && value !== null ? value as Record<string, unknown> : {}
}

function string(value: unknown): string | undefined {
  return typeof value === 'string' ? value : undefined
}

function array(value: unknown): unknown[] {
  return Array.isArray(value) ? value : []
}

async function readError(response: Response): Promise<string> {
  try {
    const body: unknown = await response.json()
    const detail = record(body).detail ?? record(body).message ?? record(body).error
    if (typeof detail === 'string') return detail
  } catch {
    // A plain-text response is handled below.
  }
  return response.statusText || 'The repository service returned an unexpected error.'
}

function normalizeSeverity(value: unknown): Finding['severity'] {
  const candidate = string(value)?.toLowerCase()
  return candidate === 'critical' || candidate === 'high' || candidate === 'medium' || candidate === 'low' || candidate === 'info'
    ? candidate
    : 'info'
}

function normalizeFinding(value: unknown, index: number): Finding {
  const source = record(value)
  return {
    id: string(source.id) ?? `finding-${index}`,
    severity: normalizeSeverity(source.severity),
    title: string(source.title) ?? 'Untitled signal',
    detail: string(source.detail) ?? string(source.description) ?? '',
    files: array(source.files ?? source.paths).filter((path): path is string => typeof path === 'string'),
    recommendation: string(source.recommendation),
  }
}

function normalizeReport(value: unknown): SpecialistReport {
  const source = record(value)
  const role = string(source.role)
  return {
    role: role === 'architecture' || role === 'risk' || role === 'testing' || role === 'history' ? role : 'architecture',
    label: string(source.label),
    summary: string(source.summary) ?? '',
    findings: array(source.findings).map(normalizeFinding),
    confidence: typeof source.confidence === 'number' ? source.confidence : undefined,
  }
}

function normalizeProgressEvent(value: unknown): ProgressEvent | undefined {
  const source = record(value)
  const phase = string(source.phase)
  const message = string(source.message)
  if (!phase || !message) return undefined
  const role = string(source.role)
  return {
    phase,
    message,
    timestamp: string(source.timestamp),
    role: role === 'architecture' || role === 'risk' || role === 'testing' || role === 'history' ? role : undefined,
  }
}

function extractArtifacts(source: Record<string, unknown>, result: Record<string, unknown>): AnalysisJob['artifacts'] {
  const artifacts = record(source.artifacts)
  const repoMap = record(result.repo_map ?? source.repo_map)
  return {
    agentsMd: string(result.agents_md) ?? string(artifacts.agents_md) ?? string(artifacts.agentsMd) ?? string(source.agents_md) ?? string(source.agentsMd),
    repoMap: string(repoMap.markdown) ?? string(artifacts.repo_map_markdown) ?? string(artifacts.repoMap) ?? string(source.repo_map_markdown) ?? string(source.repoMap),
  }
}

export function normalizeJob(value: unknown): AnalysisJob {
  const source = record(value)
  const result = record(source.result ?? source.analysis_result)
  const repository = record(result.repository ?? source.repository)
  const orchestration = record(result.orchestration ?? source.orchestration)
  const reports = array(result.reports ?? source.reports ?? source.agent_reports).map(normalizeReport)
  const statuses = record(source.agent_status ?? source.agentStatus)
  const agentStatus = Object.fromEntries(
    (['architecture', 'risk', 'testing', 'history'] as AgentRole[])
      .filter((role) => typeof statuses[role] === 'string')
      .map((role) => [role, String(statuses[role])]),
  ) as Partial<Record<AgentRole, string>>

  return {
    jobId: string(source.job_id) ?? string(source.jobId) ?? string(source.id) ?? '',
    status: string(source.status) ?? 'queued',
    repoUrl: string(source.repository_url) ?? string(source.repo_url) ?? string(source.repoUrl),
    repositoryName: string(repository.name) ?? string(source.repository_name) ?? string(source.repositoryName) ?? string(source.repo_name),
    mode: string(orchestration.mode) ?? string(source.mode) ?? string(source.execution_mode) ?? string(source.analysis_mode),
    model: string(orchestration.model),
    summary: string(result.summary) ?? string(source.summary) ?? string(source.executive_summary),
    error: string(source.error) ?? string(source.detail),
    reports,
    agentStatus,
    events: array(source.events).map(normalizeProgressEvent).filter((event): event is ProgressEvent => Boolean(event)),
    artifacts: extractArtifacts(source, result),
  }
}

export async function createAnalysis(repoUrl: string): Promise<AnalysisJob> {
  const response = await fetch(endpoint('/api/analyze'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ repo_url: repoUrl }),
  })
  if (!response.ok) throw new ApiError(await readError(response), response.status)
  const normalized = normalizeJob(await response.json())
  if (!normalized.jobId) throw new ApiError('The repository service did not return an analysis ID.')
  return normalized
}

export async function getAnalysis(jobId: string): Promise<AnalysisJob> {
  const response = await fetch(endpoint(`/api/analyze/${encodeURIComponent(jobId)}`))
  if (!response.ok) throw new ApiError(await readError(response), response.status)
  return normalizeJob(await response.json())
}

export function getArtifactUrl(jobId: string, artifactName: 'AGENTS.md' | 'repo-map.md'): string {
  return endpoint(`/api/analyze/${encodeURIComponent(jobId)}/artifacts/${encodeURIComponent(artifactName)}`)
}

export async function fetchArtifact(jobId: string, artifactName: 'AGENTS.md' | 'repo-map.md'): Promise<string> {
  const response = await fetch(getArtifactUrl(jobId, artifactName))
  if (!response.ok) throw new ApiError(await readError(response), response.status)
  return response.text()
}

function webSocketEndpoint(jobId: string): string {
  const url = new URL(apiBase)
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
  url.pathname = `${url.pathname.replace(/\/$/, '')}/api/analyze/${encodeURIComponent(jobId)}/events`
  return url.toString()
}

export function openEventStream(jobId: string, onEvent: (event: JobEvent) => void): WebSocket {
  const stream = new WebSocket(webSocketEndpoint(jobId))
  stream.onmessage = (message) => {
    try {
      const source = record(JSON.parse(String(message.data)))
      const candidate = record(source.job ?? source.analysis ?? source.data)
      if (Object.keys(candidate).length > 0 && (candidate.job_id || candidate.jobId || candidate.id)) {
        onEvent({ type: string(source.type) ?? string(source.event), job: normalizeJob(candidate) })
        return
      }
      const progress = normalizeProgressEvent(source)
      if (progress) onEvent({ type: 'progress', progress })
    } catch {
      // Polling remains the compatibility fallback if the stream is malformed.
    }
  }
  return stream
}