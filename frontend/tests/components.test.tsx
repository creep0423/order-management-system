import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { OrderItemsTable } from '../src/components/OrderItemsTable'
import { OrderTable } from '../src/components/OrderTable'
import { orderDetail, orderSummaries } from './fixtures'

describe('scrollable order tables', () => {
  it('reaches the named order list overflow region through Tab navigation', async () => {
    const user = userEvent.setup()
    render(<OrderTable orders={orderSummaries} onOpenOrder={vi.fn()} />)

    const region = screen.getByRole('region', { name: 'Orders table' })
    expect(region.tabIndex).toBe(0)
    await user.tab()
    expect(document.activeElement).toBe(region)
    expect(screen.getByRole('columnheader', { name: 'Total before shipping' })).toBeTruthy()
    expect(screen.getAllByText('Shipping quote not requested')).toHaveLength(2)
  })

  it('reaches the named item table region through Tab and supports duplicate business keys', async () => {
    const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => undefined)
    const user = userEvent.setup()
    const repeatedItem = orderDetail.items[0]
    render(<OrderItemsTable items={[repeatedItem, repeatedItem]} />)

    const region = screen.getByRole('region', { name: 'Order items table' })
    expect(region.tabIndex).toBe(0)
    const placeholders = screen.getAllByRole('img', {
      name: 'Medicine bottle product image placeholder',
    })
    expect(placeholders).toHaveLength(2)
    expect(placeholders[0].tagName).toBe('svg')
    expect(placeholders[0].getAttribute('viewBox')).toBe('0 0 48 56')
    await user.tab()
    expect(document.activeElement).toBe(region)
    expect(screen.getAllByText('TEST-SKU-001')).toHaveLength(2)
    expect(
      errorSpy.mock.calls.some((call) => String(call[0]).includes('same key')),
    ).toBe(false)
  })
})
