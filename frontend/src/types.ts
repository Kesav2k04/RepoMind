export type AgentRole = 'architecture' | 'risk' | 'testing' | 'history'
export type FindingSeverity = 'critical' | 'high' | 'medium' | 'low' | 'info'

export interface Finding {
  id: string
  severity: FindingSeverity
  title: string
  detail: string
  files: string[]
  recommendation?: string
}

export interface SpecialistReport {
  role: AgentRole
  label?: string
  summary: string
  findings: Finding[]
  confidence?: number
}

export interface ProgressEvent {
  timestamp?: string
  phase: string
  message: string
  role?: AgentRole
}

export interface ArtifactBundle {
  agentsMd?: string
  repoMap?: string
}

export interface AnalysisJob {
  jobId: string
  status: string
  repoUrl?: string
  repositoryName?: string
  mode?: string
  model?: string
  summary?: string
  error?: string
  reports: SpecialistReport[]
  agentStatus: Partial<Record<AgentRole, string>>
  events: ProgressEvent[]
  artifacts: ArtifactBundle
}

export interface JobEvent {
  job?: AnalysisJob
  progress?: ProgressEvent
  type?: string
}