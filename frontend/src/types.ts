export type AgentRole = 'architecture' | 'risk' | 'testing' | 'history'
export type FindingSeverity = 'critical' | 'high' | 'medium' | 'low' | 'info'
export type ReconciliationDisposition = 'accepted' | 'merged' | 'deferred'

export interface EvidenceLocation {
  path: string
  lineStart?: number
  lineEnd?: number
  excerpt?: string
  reason?: string
}

export interface Finding {
  id: string
  severity: FindingSeverity
  title: string
  detail: string
  files: string[]
  confidence?: number
  evidence: EvidenceLocation[]
  recommendation?: string
}

export interface SpecialistReport {
  role: AgentRole
  label?: string
  summary: string
  findings: Finding[]
  confidence?: number
  evidenceCount?: number
}

export interface ProgressEvent {
  timestamp?: string
  phase: string
  message: string
  role?: AgentRole
  action?: string
  current?: number
  total?: number
  percent?: number
  metrics: Record<string, number>
}

export interface AnalysisMetrics {
  filesAnalyzed: number
  sampledFiles: number
  manifestsFound: number
  testsDiscovered: number
  commitsInspected: number
  findingsPublished: number
  artifactsGenerated: number
  durationMs: number
  partialAnalysis?: boolean
  discoveredFiles?: number
  skippedFiles?: number
  contentTruncated?: boolean
}

export type AnalysisScopeStatus = 'complete' | 'partial' | 'unknown'

/**
 * Coverage metadata is optional so the UI remains compatible with older API
 * responses. `unknown` deliberately avoids implying that a bounded scan saw
 * every repository file.
 */
export interface AnalysisScope {
  status: AnalysisScopeStatus
  filesAvailable?: number
  filesSelected?: number
  filesExcluded?: number
  characterLimit?: number
  reasons: string[]
}

/** Evidence/artifact validation metadata supplied by newer API versions. */
export interface ValidationSummary {
  artifactsValidated?: boolean
  validatedFindings?: number
  rejectedClaims?: number
  message?: string
}

export interface ReconciliationDecision {
  disposition: ReconciliationDisposition
  findingIds: string[]
  rationale: string
}

export interface ReconciliationSummary {
  acceptedCount: number
  mergedCount: number
  deferredCount: number
  decisions: ReconciliationDecision[]
}

export interface RepositoryMapNode {
  path: string
  kind: 'directory' | 'file'
  purpose: string
  risk: FindingSeverity
  children: RepositoryMapNode[]
}

export interface ArtifactBundle {
  agentsMd?: string
  repoMap?: string
  repoMapNodes: RepositoryMapNode[]
  repoMapOverview?: string
}

export interface RepositoryInfo {
  name?: string
  url?: string
  primaryLanguage?: string
  fileCount?: number
}

export interface AnalysisJob {
  jobId: string
  status: string
  repoUrl?: string
  repositoryName?: string
  repository?: RepositoryInfo
  mode?: string
  model?: string
  summary?: string
  error?: string
  reports: SpecialistReport[]
  agentStatus: Partial<Record<AgentRole, string>>
  events: ProgressEvent[]
  metrics: AnalysisMetrics
  analysisScope: AnalysisScope
  validation: ValidationSummary
  reconciliation: ReconciliationSummary
  artifacts: ArtifactBundle
}

export interface JobEvent {
  job?: AnalysisJob
  progress?: ProgressEvent
  type?: string
}
