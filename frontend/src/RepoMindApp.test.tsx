import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import RepoMindApp from './RepoMindApp'

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

    fireEvent.click(screen.getByRole('button', { name: 'Use Flask demo' }))

    expect(screen.getByLabelText('Public GitHub repository to brief')).toHaveValue('https://github.com/pallets/flask')
    expect(screen.getByLabelText(/What are you about to change/)).toHaveValue('Add a focused test around an error-handling change.')
  })
})
