import type { Money } from '../types/orders'
import { formatMoney } from '../utils/formatters'

interface MoneyDisplayProps {
  money: Money
  emphasis?: boolean
}

export function MoneyDisplay({ money, emphasis = false }: MoneyDisplayProps) {
  return (
    <span className={emphasis ? 'money money--emphasis' : 'money'}>
      {formatMoney(money)}
    </span>
  )
}
