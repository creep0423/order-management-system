import { describe, expect, it } from 'vitest'

import { formatEta, formatMoney } from '../src/utils/formatters'

describe('formatMoney', () => {
  it('adds the AUD display prefix without numeric conversion', () => {
    expect(formatMoney({ amount: '12345678901234567890.12', currency: 'AUD' })).toBe(
      'A$12345678901234567890.12',
    )
  })

  it('normalizes zero and defensive negative-zero strings for display', () => {
    expect(formatMoney({ amount: '0.00', currency: 'AUD' })).toBe('A$0.00')
    expect(formatMoney({ amount: '-0.00', currency: 'AUD' })).toBe('A$0.00')
  })
})

describe('formatEta', () => {
  it('never echoes raw source markers when no ETA exists', () => {
    expect(formatEta(null, 'nullDays')).toBe('ETA unavailable')
    expect(formatEta(null, 'Unavailable')).toBe('ETA unavailable')
  })

  it('shows the provided ETA verbatim without interpreting zero days', () => {
    expect(formatEta(0, '0Days')).toBe('ETA: 0Days')
    expect(formatEta(10, '10Days')).toBe('ETA: 10Days')
  })

  it('falls back to a neutral label when the raw text is blank', () => {
    expect(formatEta(3, '   ')).toBe('ETA: 3 days')
  })
})
