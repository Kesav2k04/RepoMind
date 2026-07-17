import type {
  AgentRole,
  AnalysisJob,
  AnalysisMetrics,
  AnalysisScope,
  EvidenceLocation,
  Finding,
  FindingSeverity,
  JobEvent,
  ProgressEvent,
  ReconciliationDisposition,
  ReconciliationSummary,
  RepositoryMapNode,
  SpecialistReport,
  ValidationSummary,
} from './types'

const apiBase = (import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000').replace(/\/$/, '')
const roles: AgentRole[] = ['architecture', 'risk', 'testing', 'history']

export class ApiError extends Error {
  readonly status: number

  constructor(message: string, status = 0) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

function endpoint(path: string): string { return `${apiBase}${path}` }
function record(value: unknown): Record<string, unknown> { return typeof value === 'object' && value !== null ? value as Record<string, unknown> : {} }
function string(value: unknown): string | undefined { return typeof value === 'string' ? value : undefined }
function array(value: unknown): unknown[] { return Array.isArray(value) ? value : [] }
function strings(value: unknown): string[] { return array(value).filter((item): item is string => typeof item === 'string' && item.trim().length > 0) }
function number(value: unknown, fallback = 0): number { return typeof value === 'number' && Number.isFinite(value) ? value : fallback }
function optionalNumber(value: unknown): number | undefined { return typeof value === 'number' && Number.isFinite(value) ? value : undefined }
function boolean(value: unknown): boolean | undefined { return typeof value === 'boolean' ? value : undefined }
function probability(value: unknown): number | undefined {
  const candidate = optionalNumber(value)
  return candidate !== undefined && candidate >= 0 && candidate <= 1 ? candidate : undefined
}
function lineNumber(value: unknown): number | undefined {
  const candidate = optionalNumber(value)
  return candidate !== undefined && Number.isInteger(candidate) && candidate > 0 ? candidate : undefined
}
function isRole(value: unknown): value is AgentRole { return typeof value === 'string' && roles.includes(value as AgentRole) }

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

function normalizeSeverity(value: unknown): FindingSeverity {
  const candidate = string(value)?.toLowerCase()
  return candidate === 'critical' || candidate === 'high' || candidate === 'medium' || candidate === 'low' || candidate === 'info' ? candidate : 'info'
}

function normalizeEvidence(value: unknown): EvidenceLocation | undefined {
  const source = record(value)
  const path = string(source.path) ?? string(source.file)
  if (!path) return undefined
  const lineStart = lineNumber(source.line_start ?? source.lineStart ?? source.line)
  const candidateLineEnd = lineNumber(source.line_end ?? source.lineEnd)
  return {
    path,
    lineStart,
    lineEnd: candidateLineEnd !== undefined && (lineStart === undefined || candidateLineEnd >= lineStart) ? candidateLineEnd : undefined,
    excerpt: string(source.excerpt),
    reason: string(source.reason),
  }
}

function normalizeFinding(value: unknown, index: number): Finding {
  const source = record(value)
  return {
    id: string(source.id) ?? `finding-${index}`,
    severity: normalizeSeverity(source.severity),
    title: string(source.title) ?? 'Untitled signal',
    detail: string(source.detail) ?? string(source.description) ?? '',
    files: array(source.files ?? source.paths).filter((path): path is string => typeof path === 'string'),
    confidence: probability(source.confidence),
    evidence: array(source.evidence).map(normalizeEvidence).filter((item): item is EvidenceLocation => Boolean(item)),
    recommendation: string(source.recommendation),
  }
}

function normalizeReport(value: unknown): SpecialistReport {
  const source = record(value)
  const role = string(source.role)
  return {
    role: isRole(role) ? role : 'architecture',
    label: string(source.label),
    summary: string(source.summary) ?? '',
    findings: array(source.findings).map(normalizeFinding),
    confidence: probability(source.confidence),
    evidenceCount: optionalNumber(source.evidence_count ?? source.evidenceCount),
  }
}

function normalizeMetrics(value: unknown): AnalysisMetrics {
  const source = record(value)
  return {
    filesAnalyzed: number(source.files_analyzed ?? source.filesAnalyzed),
    sampledFiles: number(source.sampled_files ?? source.sampledFiles),
    manifestsFound: number(source.manifests_found ?? source.manifestsFound),
    testsDiscovered: number(source.tests_discovered ?? source.testsDiscovered),
    commitsInspected: number(source.commits_inspected ?? source.commitsInspected),
    findingsPublished: number(source.findings_published ?? source.findingsPublished),
    artifactsGenerated: number(source.artifacts_generated ?? source.artifactsGenerated, 2),
    durationMs: number(source.duration_ms ?? source.durationMs),
    partialAnalysis: boolean(source.partial_analysis ?? source.partialAnalysis),
    discoveredFiles: optionalNumber(source.discovered_files ?? source.discoveredFiles),
    skippedFiles: optionalNumber(source.skipped_files ?? source.skippedFiles),
    contentTruncated: boolean(source.content_truncated ?? source.contentTruncated),
  }
}

function normalizeAnalysisScope(source: Record<string, unknown>, result: Record<string, unknown>, metrics: AnalysisMetrics): AnalysisScope {
  const scope = {
    ...record(source.coverage),
    ...record(source.analysis_scope ?? source.analysisScope),
    ...record(result.coverage),
    ...record(result.analysis_scope ?? result.analysisScope),
  }
  const filesAvailable = optionalNumber(scope.files_available ?? scope.filesAvailable ?? scope.total_files ?? scope.totalFiles ?? scope.files_discovered ?? scope.filesDiscovered) ?? metrics.discoveredFiles
  const filesSelected = optionalNumber(scope.selected_files ?? scope.selectedFiles)
  const filesExcluded = optionalNumber(scope.files_excluded ?? scope.filesExcluded ?? scope.files_excluded_by_selection ?? scope.filesExcludedBySelection ?? scope.files_omitted ?? scope.filesOmitted ?? scope.files_skipped ?? scope.filesSkipped) ?? metrics.skippedFiles
  const truncated = boolean(scope.partial ?? scope.is_partial ?? scope.isPartial ?? scope.truncated ?? scope.was_truncated) || metrics.partialAnalysis || metrics.contentTruncated
  const label = string(scope.status)?.toLowerCase()
  const partialStatus = label === 'partial' || label === 'truncated' || label === 'bounded' || label === 'sampled'
  const completeStatus = label === 'complete' || label === 'full' || label === 'complete_scan' || label === 'full_scan'
  const inferredPartial = (filesExcluded !== undefined && filesExcluded > 0) || (filesAvailable !== undefined && filesAvailable > metrics.filesAnalyzed)
  return {
    status: truncated || partialStatus || inferredPartial ? 'partial' : completeStatus ? 'complete' : 'unknown',
    filesAvailable,
    filesSelected,
    filesExcluded,
    characterLimit: optionalNumber(scope.character_limit ?? scope.characterLimit ?? scope.max_total_content_chars ?? scope.maxTotalContentChars),
    reasons: [...new Set([
      ...strings(source.partial_reasons ?? source.partialReasons),
      ...strings(result.partial_reasons ?? result.partialReasons),
      ...strings(scope.reasons ?? scope.partial_reasons ?? scope.partialReasons),
      ...[string(scope.reason) ?? string(scope.message) ?? string(scope.note)].filter((item): item is string => Boolean(item)),
    ])],
  }
}

function normalizeValidation(source: Record<string, unknown>, result: Record<string, unknown>): ValidationSummary {
  const validation = {
    ...record(source.validation),
    ...record(source.artifact_validation ?? source.artifactValidation),
    ...record(result.validation),
    ...record(result.artifact_validation ?? result.artifactValidation),
  }
  const status = string(validation.status)?.toLowerCase()
  return {
    artifactsValidated: boolean(validation.artifacts_validated ?? validation.artifactsValidated ?? validation.validated) ?? (status === 'validated' ? true : undefined),
    validatedFindings: optionalNumber(validation.validated_findings ?? validation.validatedFindings ?? validation.findings_validated ?? validation.findingsValidated),
    rejectedClaims: optionalNumber(validation.rejected_claims ?? validation.rejectedClaims),
    message: string(validation.message) ?? string(validation.note),
  }
}

function normalizeDecision(value: unknown) {
  const source = record(value)
  const disposition = string(source.disposition)
  const normalized: ReconciliationDisposition = disposition === 'accepted' || disposition === 'merged' || disposition === 'deferred' ? disposition : 'deferred'
  return {
    disposition: normalized,
    findingIds: array(source.finding_ids ?? source.findingIds).filter((item): item is string => typeof item === 'string'),
    rationale: string(source.rationale) ?? '',
  }
}

function normalizeReconciliation(value: unknown): ReconciliationSummary {
  const source = record(value)
  return {
    acceptedCount: number(source.accepted_count ?? source.acceptedCount),
    mergedCount: number(source.merged_count ?? source.mergedCount),
    deferredCount: number(source.deferred_count ?? source.deferredCount),
    decisions: array(source.decisions).map(normalizeDecision),
  }
}

function normalizeMapNode(value: unknown): RepositoryMapNode | undefined {
  const source = record(value)
  const path = string(source.path)
  if (!path) return undefined
  return {
    path,
    kind: source.kind === 'file' ? 'file' : 'directory',
    purpose: string(source.purpose) ?? '',
    risk: normalizeSeverity(source.risk),
    children: array(source.children).map(normalizeMapNode).filter((item): item is RepositoryMapNode => Boolean(item)),
  }
}

function normalizeProgressEvent(value: unknown): ProgressEvent | undefined {
  const source = record(value)
  const phase = string(source.phase)
  const message = string(source.message)
  if (!phase || !message) return undefined
  const eventMetrics = record(source.metrics)
  const metrics = Object.fromEntries(Object.entries(eventMetrics).filter(([, item]) => typeof item === 'number' && Number.isFinite(item))) as Record<string, number>
  return {
    phase,
    message,
    timestamp: string(source.timestamp),
    role: isRole(source.role) ? source.role : undefined,
    action: string(source.action),
    current: optionalNumber(source.current),
    total: optionalNumber(source.total),
    percent: optionalNumber(source.percent),
    metrics,
  }
}

function extractArtifacts(source: Record<string, unknown>, result: Record<string, unknown>): AnalysisJob['artifacts'] {
  const artifacts = record(source.artifacts)
  const repoMap = record(result.repo_map ?? source.repo_map)
  return {
    agentsMd: string(result.agents_md) ?? string(artifacts.agents_md) ?? string(artifacts.agentsMd) ?? string(source.agents_md) ?? string(source.agentsMd),
    repoMap: string(repoMap.markdown) ?? string(artifacts.repo_map_markdown) ?? string(artifacts.repoMap) ?? string(source.repo_map_markdown) ?? string(source.repoMap),
    repoMapNodes: array(repoMap.nodes ?? artifacts.repo_map_nodes ?? artifacts.repoMapNodes).map(normalizeMapNode).filter((item): item is RepositoryMapNode => Boolean(item)),
    repoMapOverview: string(repoMap.overview),
  }
}

export function normalizeJob(value: unknown): AnalysisJob {
  const source = record(value)
  const result = record(source.result ?? source.analysis_result)
  const repository = record(result.repository ?? source.repository)
  const orchestration = record(result.orchestration ?? source.orchestration)
  const reports = array(result.reports ?? source.reports ?? source.agent_reports).map(normalizeReport)
  const statuses = record(source.agent_status ?? source.agentStatus)
  const agentStatus = Object.fromEntries(roles.filter((role) => typeof statuses[role] === 'string').map((role) => [role, String(statuses[role])])) as Partial<Record<AgentRole, string>>

  const metrics = normalizeMetrics(result.metrics ?? source.metrics)
  return {
    jobId: string(source.job_id) ?? string(source.jobId) ?? string(source.id) ?? '',
    status: string(source.status) ?? 'queued',
    repoUrl: string(source.repository_url) ?? string(source.repo_url) ?? string(source.repoUrl),
    repositoryName: string(repository.name) ?? string(source.repository_name) ?? string(source.repositoryName) ?? string(source.repo_name),
    repository: {
      name: string(repository.name),
      url: string(repository.url),
      primaryLanguage: string(repository.primary_language ?? repository.primaryLanguage),
      fileCount: optionalNumber(repository.file_count ?? repository.fileCount),
    },
    mode: string(orchestration.mode) ?? string(source.mode) ?? string(source.execution_mode) ?? string(source.analysis_mode),
    model: string(orchestration.model),
    summary: string(result.summary) ?? string(source.summary) ?? string(source.executive_summary),
    error: string(source.error) ?? string(source.detail),
    reports,
    agentStatus,
    events: array(source.events).map(normalizeProgressEvent).filter((event): event is ProgressEvent => Boolean(event)),
    metrics,
    analysisScope: normalizeAnalysisScope(source, result, metrics),
    validation: normalizeValidation(source, result),
    reconciliation: normalizeReconciliation(result.reconciliation ?? source.reconciliation),
    artifacts: extractArtifacts(source, result),
  }
}

export async function createAnalysis(repoUrl: string): Promise<AnalysisJob> {
  const response = await fetch(endpoint('/api/analyze'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ repo_url: repoUrl }) })
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

export function getArtifactUrl(jobId: string, artifactName: 'AGENTS.md' | 'repo-map.md'): string { return endpoint(`/api/analyze/${encodeURIComponent(jobId)}/artifacts/${encodeURIComponent(artifactName)}`) }

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
      const progress = normalizeProgressEvent(source.progress ?? source)
      if (progress) onEvent({ type: string(source.type) ?? 'progress', progress })
    } catch {
      // Polling remains the compatibility fallback if the stream is malformed.
    }
  }
  return stream
}
