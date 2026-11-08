# Order Management System Frontend

> 中文完整说明见仓库根目录 `README.md`；本文件是前端子目录的补充说明（English）。

This directory contains the Phase 5 read-only order management frontend plus the Phase 6 Batch I coordinated Tracking contract and UI. It loads order data from the existing FastAPI v1 API; it does not create, edit, or delete orders.

## Implemented functionality

- Order list with order-number and company search, order-status filtering, clear filters, D-030 `Total before shipping`, and `Shipping quote not requested` semantics.
- Order detail views for customer, shipping address, product, quantity, and internal tracking-group information.
- API-supplied AUD Money display, including the order subtotal, GST amount, shipment fee, and order total. Money amounts remain decimal strings in the browser and are not recalculated by the frontend.
- Explicit Shipping Quote status and limitation messaging.
- Tracking cards that distinguish available, unavailable, D-031 mapping unresolved, unsupported, unknown raw status, a successful response with no real events, and an order with no unique tracking group.
- Initial, list, and detail loading states; empty and search-empty states; not-found, disconnected, and API error states; and retry actions.
- Responsive layouts, semantic HTML, keyboard-accessible actions and horizontally scrollable tables, visible focus styles, and ARIA status announcements.
- SPA navigation for list, detail, Back/Forward, direct detail access, and refresh-compatible history state.

Tracking Group IDs are internal order associations. They are not carrier tracking events or Package IDs. The UI displays only API-validated Provider facts; it does not derive status from descriptions or invent events/ETA. Per D-031, a tracking card may show a null provider only for `unavailable / CARRIER_MAPPING_UNRESOLVED`, rendered as `Tracking unavailable — carrier mapping could not be resolved.`; that state is never shown as `Tracking not requested`. An empty `tracking_results` array is rendered as `No tracking groups` and only means the order has no unique tracking group.

## Technology stack

- Frontend: React 19, TypeScript 7 in strict mode, Vite 8, and Oxlint.
- Frontend tests: Vitest, React Testing Library, Testing Library User Event, and JSDOM.
- Backend API: Python 3.13, FastAPI, Pydantic 2, and Python `Decimal`, with validated JSON files as the current read-only data source.

## Local development

Run these commands from the repository root on Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload
npm.cmd run dev --prefix frontend
```

The frontend defaults to `http://127.0.0.1:8000` for the API. `VITE_API_BASE_URL` may select another approved API origin; it must not contain credentials. The Vite development server normally runs at `http://localhost:5173` or `http://127.0.0.1:5173`.

## Validation commands

Run the frontend checks from the repository root:

```powershell
npm.cmd run test --prefix frontend
frontend\node_modules\.bin\tsc.cmd -p frontend\tsconfig.app.json --noEmit --incremental false
npm.cmd run typecheck:test --prefix frontend
npm.cmd run build --prefix frontend
npm.cmd run lint --prefix frontend
npm.cmd ls --prefix frontend --depth=0
npm.cmd audit --prefix frontend --audit-level=high
```

`npm.cmd run check --prefix frontend` runs the frontend tests, test TypeScript check, production build, and lint in sequence. The production build also runs the application TypeScript project build.

Run the backend regression checks from the repository root:

```powershell
.\.venv\Scripts\python.exe -m pytest -v
.\.venv\Scripts\ruff.exe check backend
.\.venv\Scripts\ruff.exe format --check backend
.\.venv\Scripts\python.exe -m pip check
```

## Shipping Quote limitation (D-015)

The Shipping Quote Integration is not implemented in Phase 5. The current API contract returns:

- `status = "unsupported"`
- `reason_code = "SHIPPING_QUOTE_NOT_IMPLEMENTED"`
- `quoted_fee = null`
- `applied_fee = {"amount":"0.00","currency":"AUD"}`
- `checked_at` as a runtime UTC-aware datetime indicating when the system performed this check

The `AUD 0.00` applied fee is the deterministic fallback amount used by the current pricing flow. It does not mean that a carrier quoted a zero fee, and it does not mean shipping is free. `quoted_fee = null` confirms that no real carrier quote is available.

`unsupported` means the integration has not been implemented. It is different from `unavailable`, which is reserved for an implemented capability that cannot return a valid result for a particular request. Real Shipping Quote Integration belongs to Phase 6.

The frontend can display validated Tracking results. The default backend injects a Tracking Service but has no approved Configuration Release, Mapping or credentials, so it returns one D-031 `unavailable / CARRIER_MAPPING_UNRESOLVED` result per unique tracking group and never makes a live carrier call. Real carrier tracking and quotation remain unimplemented, and the D-015 fallback is never treated as an available quote.
