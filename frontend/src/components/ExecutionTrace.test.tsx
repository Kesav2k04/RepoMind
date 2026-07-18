import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { ExecutionTrace } from './ExecutionTrace'
import { nativeJob } from '../test/fixtures'

describe('ExecutionTrace', () => {
  it('renders tool and firewall events recorded by the live analysis', () => {
    render(<ExecutionTrace job={nativeJob()} />)

    expect(screen.getByText('What the GPT-5.6 specialists actually did.')).toBeInTheDocument()
    expect(screen.getByText('read_file · src/auth.py:18-46')).toBeInTheDocument()
    expect(screen.getByText('Firewall verified 1; blocked 0')).toBeInTheDocument()
    expect(screen.getByText('1 verified · 0 withheld')).toBeInTheDocument()
  })
})
