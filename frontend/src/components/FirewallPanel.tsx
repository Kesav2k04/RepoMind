import type { AgentRole, AnalysisJob, ProgressEvent } from '../types'

type FirewallTotals = { proposed: number; verified: number; withheld: number; toolCalls: number; native: boolean }

function latestByRole(events: ProgressEvent[], metric: string): number {
  const latest = new Map<AgentRole, number>()
  for (const event of events) {
    if (!event.role || event.metrics[metric] === undefined) continue
    latest.set(event.role, event.metrics[metric])
  }
  return [...latest.values()].reduce((total, value) => total + value, 0)
}

function totals(job: AnalysisJob): FirewallTotals {
  const firewallEvents = job.events.filter((event) => event.phase === 'firewall_verified')
  const native = job.mode === 'native_multi_agent' || firewallEvents.length > 0 || job.events.some((event) => event.action === 'dispatching_gpt56_specialists')
  const streamedProposed = latestByRole(firewallEvents, 'claims_proposed')
  const streamedVerified = latestByRole(firewallEvents, 'claims_verified')
  const streamedWithheld = latestByRole(firewallEvents, 'claims_rejected')
  const streamedToolCalls = latestByRole(job.events.filter((event) => event.role), 'model_tool_calls')
  return {
    native,
    proposed: job.validation.proposedClaims ?? streamedProposed,
    verified: job.validation.validatedFindings ?? streamedVerified,
    withheld: job.validation.rejectedClaims ?? streamedWithheld,
    toolCalls: job.metrics.modelToolCalls || streamedToolCalls,
  }
}

export function FirewallPanel({ job }: { job: AnalysisJob }) {
  const state = totals(job)
  const complete = job.status === 'completed' || job.status === 'complete'
  const title = state.native ? 'Citation firewall' : 'Evidence validation'
  const copy = state.native
    ? 'A GPT-5.6 claim is published only when its quote matches both the bounded checkout and source returned to that specialist by a read-only tool.'
    : 'Evidence Mode did not ask a model to propose claims. Local specialist findings remain bounded and evidence-backed.'

  return <section className={`firewall-panel firewall-panel--${state.native ? 'native' : 'evidence'}`} aria-label={title}>
    <div className="firewall-panel__lead"><div><p className="eyebrow eyebrow--accent">{state.native ? 'Trust boundary' : 'Fallback trust boundary'}</p><h2>{title}</h2><p>{copy}</p></div><span className="firewall-panel__state">{state.native ? 'active' : 'evidence mode'}</span></div>
    <div className="firewall-panel__metrics"><div><strong>{state.proposed || (complete ? 0 : '—')}</strong><span>{state.native ? 'claims proposed' : 'signals considered'}</span></div><div><strong>{state.verified || (complete ? 0 : '—')}</strong><span>{state.native ? 'claims verified' : 'findings published'}</span></div><div><strong>{state.withheld || (complete ? 0 : '—')}</strong><span>{state.native ? 'claims withheld' : 'signals withheld'}</span></div><div><strong>{state.toolCalls || (complete ? 0 : '—')}</strong><span>{state.native ? 'model tool calls' : 'model tool calls'}</span></div></div>
    {job.validation.message && <p className="firewall-panel__note">{job.validation.message}</p>}
  </section>
}
