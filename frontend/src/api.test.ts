import { describe, expect, it } from 'vitest'

import { normalizeJob } from './api'

describe('normalizeJob', () => {
  it('keeps task, firewall, and native-tool metadata from the API contract', () => {
    const job = normalizeJob({
      job_id: 'job_123',
      status: 'completed',
      repository_url: 'https://github.com/acme/demo.git',
      task_description: 'Fix auth session handling.',
      result: {
        repository: { name: 'demo', url: 'https://github.com/acme/demo.git' },
        orchestration: { mode: 'native_multi_agent', model: 'gpt-5.6-unit-test', priority_finding_ids: ['finding-1'] },
        metrics: { files_analyzed: 14, model_tool_calls: 7, model_workers_completed: 4 },
        validation: { proposed_claims: 5, validated_findings: 4, rejected_claims: 1 },
        task_brief: { task_description: 'Fix auth session handling.', priority_finding_ids: ['finding-1'], review_paths: ['src/auth.py'], verification_commands: ['pytest -q'] },
        reports: [],
        reconciliation: { accepted_count: 3, merged_count: 1, deferred_count: 0, decisions: [] },
        repo_map: { nodes: [] },
      },
    })

    expect(job.taskDescription).toBe('Fix auth session handling.')
    expect(job.metrics.modelToolCalls).toBe(7)
    expect(job.metrics.modelWorkersCompleted).toBe(4)
    expect(job.validation).toMatchObject({ proposedClaims: 5, validatedFindings: 4, rejectedClaims: 1 })
    expect(job.taskBrief).toMatchObject({ reviewPaths: ['src/auth.py'], verificationCommands: ['pytest -q'] })
  })
})
