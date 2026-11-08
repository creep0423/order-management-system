const DEFAULT_API_BASE_URL = 'http://127.0.0.1:8000'

const configuredApiBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim()

export const API_BASE_URL = (
  configuredApiBaseUrl || DEFAULT_API_BASE_URL
).replace(/\/+$/, '')

function buildApiUrl(path: string) {
  return `${API_BASE_URL}/${path.replace(/^\/+/, '')}`
}

export function apiRequest(path: string, options: RequestInit = {}) {
  const headers = new Headers(options.headers)

  if (!headers.has('Accept')) {
    headers.set('Accept', 'application/json')
  }

  return fetch(buildApiUrl(path), {
    ...options,
    credentials: 'omit',
    headers,
  })
}
