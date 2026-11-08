export function ProductPlaceholder() {
  return (
    <svg
      className="product-placeholder"
      viewBox="0 0 48 56"
      role="img"
      aria-label="Medicine bottle product image placeholder"
      xmlns="http://www.w3.org/2000/svg"
    >
      <rect className="product-placeholder__cap" x="15" y="3" width="18" height="8" rx="2" />
      <path
        className="product-placeholder__bottle"
        d="M13 11h22v4.2c3.7 1.5 6 5.1 6 9.1v20.2A8.5 8.5 0 0 1 32.5 53h-17A8.5 8.5 0 0 1 7 44.5V24.3c0-4 2.3-7.6 6-9.1V11Z"
      />
      <rect className="product-placeholder__label" x="13" y="25" width="22" height="17" rx="3" />
      <text className="product-placeholder__rx" x="24" y="36.5" textAnchor="middle">
        Rx
      </text>
    </svg>
  )
}
