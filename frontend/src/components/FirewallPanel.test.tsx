import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { FirewallPanel } from './FirewallPanel'
import { nativeJob } from '../test/fixtures'

describe('FirewallPanel', () => {
  it('makes the verified and withheld claim counts visible', () => {
    render(<FirewallPanel job={nativeJob()} />)

    expect(screen.getByRole('region', { name: 'Citation firewall' })).toBeInTheDocument()
    expect(screen.getByText('claims proposed')).toBeInTheDocument()
    expect(screen.getByText('claims verified')).toBeInTheDocument()
    expect(screen.getByText('claims withheld')).toBeInTheDocument()
    expect(screen.getByText('model tool calls')).toBeInTheDocument()
    expect(screen.getByText('Evidence firewall verified 4 of 5 proposed claims; 1 was withheld.')).toBeInTheDocument()
  })
})
