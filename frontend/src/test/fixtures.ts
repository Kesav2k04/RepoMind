import type { AnalysisJob } from '../types'

export function nativeJob(overrides: Partial<AnalysisJob> = {}): AnalysisJob {
  return {
    jobId: 'job_native',
    status: 'completed',
    repoUrl: 'https://github.com/acme/demo.git',
    taskDescription: 'Fix the auth-session race without changing the public API.',
    repositoryName: 'demo',
    repository: { name: 'demo', url: 'https://github.com/acme/demo.git', primaryLanguage: 'Python', fileCount: 14 },
    mode: 'native_multi_agent',
    model: 'gpt-5.6-unit-test',
    priorityFindingIds: ['native-risk-1'],
    reports: [],
    agentStatus: {},
    events: [
      { phase: 'orchestrating', message: 'RepoMind dispatched source specialists.', action: 'dispatching_gpt56_specialists', metrics: {} },
      { phase: 'agent_tool_call', message: 'Architecture used read_file.', role: 'architecture', action: 'read_file · src/auth.py:18-46', current: 1, total: 12, metrics: { model_tool_calls: 1 } },
      { phase: 'firewall_verified', message: 'Evidence firewall verified 1 claim.', role: 'architecture', action: 'Firewall verified 1; blocked 0', current: 4, total: 4, metrics: { claims_proposed: 1, claims_verified: 1, claims_rejected: 0, model_tool_calls: 1 } },
      { phase: 'reconciling', message: 'GPT-5.6 root is reconciling verified reports.', action: 'reconciling_verified_reports', metrics: { claims_verified: 4, claims_rejected: 1 } },
    ],
    metrics: {
      filesAnalyzed: 14,
      sampledFiles: 8,
      manifestsFound: 2,
      testsDiscovered: 3,
      commitsInspected: 12,
      findingsPublished: 4,
      artifactsGenerated: 2,
      durationMs: 4200,
      modelToolCalls: 7,
      modelWorkersCompleted: 4,
    },
    analysisScope: { status: 'complete', reasons: [] },
    validation: {
      artifactsValidated: true,
      proposedClaims: 5,
      validatedFindings: 4,
      rejectedClaims: 1,
      message: 'Evidence firewall verified 4 of 5 proposed claims; 1 was withheld.',
    },
    taskBrief: {
      taskDescription: 'Fix the auth-session race without changing the public API.',
      priorityFindingIds: ['native-risk-1'],
      reviewPaths: ['src/auth.py'],
      verificationCommands: ['pytest -q'],
    },
    reconciliation: { acceptedCount: 3, mergedCount: 1, deferredCount: 0, decisions: [] },
    artifacts: { agentsMd: '# AGENTS.md\n', repoMap: '# demo\n', repoMapNodes: [] },
    ...overrides,
  }
}
