import type { AgentRole, AnalysisJob, ProgressEvent } from '../types'

const labels: Record<AgentRole, string> = {
  architecture: 'Architecture',
  risk: 'Risk',
  testing: 'Testing',
  history: 'History',
}

const tracePhases = new Set([
  'orchestrating',
  'agent_started',
  'agent_progress',
  'agent_tool_call',
  'firewall_verified',
  'agent_completed',
  'reconciling',
  'reconciled',
])
const roles: AgentRole[] = ['architecture', 'risk', 'testing', 'history']

function selectedEvents(job: AnalysisJob): ProgressEvent[] {
  const candidates = job.events.filter((event) => tracePhases.has(event.phase))
  const selected = new Set<ProgressEvent>()
  for (const role of roles) {
    const roleEvents = candidates.filter((event) => event.role === role)
    const latestTool = [...roleEvents].reverse().find((event) => event.phase === 'agent_tool_call')
    const latestFirewall = [...roleEvents].reverse().find((event) => event.phase === 'firewall_verified')
    if (latestTool) selected.add(latestTool)
    if (latestFirewall) selected.add(latestFirewall)
    if (!latestTool && !latestFirewall) roleEvents.slice(-2).forEach((event) => selected.add(event))
  }
  candidates.filter((event) => !event.role).slice(-4).forEach((event) => selected.add(event))
  return candidates.filter((event) => selected.has(event)).slice(-14).reverse()
}

function traceLabel(event: ProgressEvent): string {
  if (event.phase === 'agent_tool_call') return 'Read-only tool'
  if (event.phase === 'firewall_verified') return 'Citation firewall'
  if (event.phase === 'reconciling' || event.phase === 'reconciled') return 'Master reconciliation'
  if (event.role) return labels[event.role]
  return 'RepoMind'
}

function traceDetail(event: ProgressEvent): string {
  return event.action || event.message
}

function traceMetric(event: ProgressEvent): string | undefined {
  const values = event.metrics
  if (values.claims_verified !== undefined || values.claims_rejected !== undefined) {
    return `${values.claims_verified ?? 0} verified · ${values.claims_rejected ?? 0} withheld`
  }
  if (values.model_tool_calls !== undefined) return `${values.model_tool_calls} model tool call${values.model_tool_calls === 1 ? '' : 's'}`
  if (event.current !== undefined && event.total !== undefined) return `${event.current}/${event.total}`
  return undefined
}

export function ExecutionTrace({ job }: { job: AnalysisJob }) {
  const events = selectedEvents(job)
  const nativeTrace = job.mode === 'native_multi_agent' || job.events.some((event) => event.action === 'dispatching_gpt56_specialists')

  return <section className="execution-trace" aria-label="Recorded specialist activity">
    <div className="execution-trace__heading">
      <div><p className="eyebrow">Recorded activity</p><h3>{nativeTrace ? 'What the GPT-5.6 specialists actually did.' : 'What the evidence specialists actually did.'}</h3></div>
      <span>{events.length ? `${events.length} recent event${events.length === 1 ? '' : 's'}` : 'Awaiting events'}</span>
    </div>
    {events.length ? <ol className="execution-trace__list">{events.map((event, index) => <li className={`execution-trace__event execution-trace__event--${event.phase}`} key={`${event.timestamp ?? index}-${event.phase}-${event.role ?? 'master'}-${index}`}>
      <span className="execution-trace__badge">{traceLabel(event)}</span>
      <p>{traceDetail(event)}</p>
      {traceMetric(event) && <small>{traceMetric(event)}</small>}
    </li>)}</ol> : <p className="execution-trace__empty">No synthetic timer is running. RepoMind will show a tool, worker, or reconciliation event only after it occurs.</p>}
  </section>
}
