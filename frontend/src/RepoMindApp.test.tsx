import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import RepoMindApp from './RepoMindApp'
import { nativeJob } from './test/fixtures'

const apiMocks = vi.hoisted(() => ({
  createAnalysis: vi.fn(),
  fetchArtifact: vi.fn(),
  getAnalysis: vi.fn(),
  getArtifactUrl: vi.fn((jobId: string, artifact: string) => `/api/analyses/${jobId}/artifacts/${artifact}`),
  openEventStream: vi.fn(() => ({ close: vi.fn() })),
}))

vi.mock('./api', () => apiMocks)

describe('RepoMindApp', () => {
  it('validates the repository URL before starting network work', () => {
    render(<RepoMindApp />)

    const input = screen.getByLabelText('Public GitHub repository to brief')
    fireEvent.change(input, { target: { value: 'not-a-url' } })
    fireEvent.submit(input.closest('form')!)

    expect(screen.getByRole('alert')).toHaveTextContent('Enter a complete public GitHub HTTPS repository URL.')
  })

  it('offers a task-aware demo starting point', () => {
    render(<RepoMindApp />)

    fireEvent.click(screen.getByRole('button', { name: 'Fill Flask example' }))

    expect(screen.getByLabelText('Public GitHub repository to brief')).toHaveValue('https://github.com/pallets/flask')
    expect(screen.getByLabelText(/What are you about to change/)).toHaveValue('Add a focused test around an error-handling change.')
  })

  it('offers focused task starters for a developer about to begin work', () => {
    render(<RepoMindApp />)

    fireEvent.click(screen.getByRole('button', { name: 'Fix a bug' }))

    expect(screen.getByLabelText(/What are you about to change/)).toHaveValue('Fix a regression without changing the public API.')
  })

  it('renders the task handoff and makes Evidence Mode model use explicit', async () => {
    const job = nativeJob({
      mode: 'evidence_fallback',
      events: [],
      reports: [{
        role: 'risk',
        summary: 'Authentication changes need a focused regression test.',
        confidence: 0.92,
        findings: [{
          id: 'native-risk-1',
          severity: 'high',
          title: 'Auth session state has a narrow change boundary',
          detail: 'The session guard is shared by request handling.',
          files: ['src/auth.py'],
          confidence: 0.92,
          evidence: [{ path: 'src/auth.py', lineStart: 18, reason: 'Session state is validated before request routing.' }],
          recommendation: 'Read the guard and its focused test before editing.',
        }],
      }],
    })
    apiMocks.createAnalysis.mockResolvedValueOnce(job)

    render(<RepoMindApp />)
    const repository = screen.getByLabelText('Public GitHub repository to brief')
    fireEvent.change(repository, { target: { value: 'https://github.com/acme/demo' } })
    fireEvent.submit(repository.closest('form')!)

    expect(await screen.findByRole('heading', { name: job.taskBrief?.taskDescription })).toBeInTheDocument()
    expect(screen.getByText('Inspect first')).toBeInTheDocument()
    expect(screen.getByText('Run after editing')).toBeInTheDocument()
    expect(screen.getByText('not used in this mode')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Get AGENTS.md' })).toHaveAttribute('href', '/api/analyses/job_native/artifacts/AGENTS.md')

    const activity = screen.getByText(/Review recorded specialist activity/).closest('details')
    expect(activity).not.toBeNull()
    expect(activity).not.toHaveAttribute('open')
  })
})
