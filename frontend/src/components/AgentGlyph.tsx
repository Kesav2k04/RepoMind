import type { AgentRole } from '../types'

interface AgentGlyphProps {
  role: AgentRole
  className?: string
}

export function AgentGlyph({ role, className = '' }: AgentGlyphProps) {
  const label = `${role} specialist`

  if (role === 'architecture') {
    return <svg aria-label={label} className={`agent-glyph ${className}`} viewBox="0 0 24 24" fill="none"><path d="M5 5h5v5H5zM14 5h5v5h-5zM9.5 16h5v4h-5zM7.5 10v3h9v-3M12 13v3" stroke="currentColor" strokeWidth="1.65" strokeLinecap="round" strokeLinejoin="round" /></svg>
  }
  if (role === 'risk') {
    return <svg aria-label={label} className={`agent-glyph ${className}`} viewBox="0 0 24 24" fill="none"><path d="M12 3.5 19 6v5.55c0 4.1-2.9 7.73-7 8.95-4.1-1.22-7-4.85-7-8.95V6l7-2.5Z" stroke="currentColor" strokeWidth="1.65" strokeLinejoin="round" /><path d="M12 8v4.4M12 16.2v.05" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" /></svg>
  }
  if (role === 'testing') {
    return <svg aria-label={label} className={`agent-glyph ${className}`} viewBox="0 0 24 24" fill="none"><path d="M9 3v5.4l-3.7 6.38A3.7 3.7 0 0 0 8.5 20h7a3.7 3.7 0 0 0 3.2-5.22L15 8.4V3M7.8 13h8.4M9.5 16l1.5 1.5 3.6-3.6" stroke="currentColor" strokeWidth="1.65" strokeLinecap="round" strokeLinejoin="round" /></svg>
  }
  return <svg aria-label={label} className={`agent-glyph ${className}`} viewBox="0 0 24 24" fill="none"><path d="M12 4a8 8 0 1 1-7.6 10.5M4 4v5h5" stroke="currentColor" strokeWidth="1.65" strokeLinecap="round" strokeLinejoin="round" /><path d="M12 8v4.5l3 1.8" stroke="currentColor" strokeWidth="1.65" strokeLinecap="round" strokeLinejoin="round" /></svg>
}
