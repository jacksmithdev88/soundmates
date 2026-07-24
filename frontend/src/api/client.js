const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export async function apiFetch(path, options = {}) {
  const body = options.body
  const isFormData = body instanceof FormData

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    credentials: 'include',
    headers: {
      ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
      ...options.headers,
    },
  })

  if (!response.ok) {
    let message = `Request failed with ${response.status}`

    try {
      const errorPayload = await response.json()
      message = errorPayload?.detail || errorPayload?.message || message
    } catch {
      try {
        message = await response.text()
      } catch {
        message = `Request failed with ${response.status}`
      }
    }

    throw new Error(message)
  }

  if (response.status === 204) {
    return null
  }

  return response.json()
}

export function loginWithSpotify(next) {
  const query = next ? `?next=${encodeURIComponent(next)}` : ''
  window.location.href = `${API_BASE_URL}/spotify/auth/login${query}`
}

export async function logout() {
  return apiFetch('/user/auth/logout', { method: 'POST' })
}
