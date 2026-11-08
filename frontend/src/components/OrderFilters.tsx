interface OrderFiltersProps {
  query: string
  status: string
  statuses: string[]
  onQueryChange: (value: string) => void
  onStatusChange: (value: string) => void
  onClear: () => void
}

export function OrderFilters({
  query,
  status,
  statuses,
  onQueryChange,
  onStatusChange,
  onClear,
}: OrderFiltersProps) {
  const hasFilters = query.length > 0 || status.length > 0

  return (
    <section className="filters" aria-label="Order filters">
      <div className="field field--search">
        <label htmlFor="order-search">Search orders</label>
        <input
          id="order-search"
          type="search"
          value={query}
          placeholder="Order number or company"
          autoComplete="off"
          onChange={(event) => onQueryChange(event.target.value)}
        />
      </div>
      <div className="field">
        <label htmlFor="status-filter">Order status</label>
        <select
          id="status-filter"
          value={status}
          onChange={(event) => onStatusChange(event.target.value)}
        >
          <option value="">All statuses</option>
          {statuses.map((availableStatus) => (
            <option key={availableStatus} value={availableStatus}>
              {availableStatus}
            </option>
          ))}
        </select>
      </div>
      <button
        className="button button--ghost filter-clear"
        type="button"
        disabled={!hasFilters}
        onClick={onClear}
      >
        Clear filters
      </button>
    </section>
  )
}
