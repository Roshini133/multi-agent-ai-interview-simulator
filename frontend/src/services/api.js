// Thin fetch wrapper: unwraps {success, data} and turns {error:{code,message}} into ApiError.
const BASE = import.meta.env.VITE_API_URL || ''
const TOKEN_KEY = 'ais_token'

export class ApiError extends Error {
  constructor(code, message, status, details) {
    super(message)
    this.code = code
    this.status = status
    this.details = details
  }
}

export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (t) => localStorage.setItem(TOKEN_KEY, t),
  clear: () => localStorage.removeItem(TOKEN_KEY),
}

let onUnauthorized = () => {}
export const setUnauthorizedHandler = (fn) => { onUnauthorized = fn }

async function request(path, { method = 'GET', body, form, blob = false, auth = true, signal } = {}) {
  const headers = {}
  const token = tokenStore.get()
  if (auth && token) headers.Authorization = `Bearer ${token}`
  let payload
  if (form) payload = form
  else if (body !== undefined) { headers['Content-Type'] = 'application/json'; payload = JSON.stringify(body) }

  let res
  try {
    res = await fetch(`${BASE}${path}`, { method, headers, body: payload, signal })
  } catch (e) {
    if (e.name === 'AbortError') throw e
    throw new ApiError('network_error', 'Cannot reach the server. Check your connection and that the backend is running.', 0)
  }
  if (blob && res.ok) return res.blob()
  let json = null
  try { json = await res.json() } catch { /* non-JSON */ }
  if (!res.ok || !json?.success) {
    const err = json?.error || {}
    if (res.status === 401 && auth) onUnauthorized()
    throw new ApiError(err.code || 'http_error', err.message || `Request failed (${res.status}).`, res.status, err.details)
  }
  return json.data
}

export const api = {
  register: (b) => request('/api/auth/register', { method: 'POST', body: b, auth: false }),
  login: (b) => request('/api/auth/login', { method: 'POST', body: b, auth: false }),
  me: () => request('/api/auth/me'),
  roles: () => request('/api/interview/roles', { auth: false }),
  status: () => request('/api/system/status', { auth: false }),
  sessions: () => request('/api/interview/'),
  startInterview: (role) => request('/api/interview/start', { method: 'POST', body: { role } }),
  session: (id) => request(`/api/interview/${id}`),
  question: (session_id) => request('/api/interview/question', { method: 'POST', body: { session_id } }),
  next: (session_id) => request('/api/interview/next', { method: 'POST', body: { session_id } }),
  answer: (b) => request('/api/interview/answer', { method: 'POST', body: b }),
  complete: (id) => request(`/api/interview/${id}/complete`, { method: 'POST' }),
  uploadResume: (session_id, file) => {
    const form = new FormData(); form.append('session_id', session_id); form.append('file', file)
    return request('/api/resume/upload', { method: 'POST', form })
  },
  resume: (id) => request(`/api/resume/${id}`),
  voiceStatus: () => request('/api/voice/status', { auth: false }),
  transcribe: (session_id, blob) => {
    const form = new FormData(); form.append('session_id', session_id); form.append('audio', blob, 'answer.webm')
    return request('/api/voice/transcribe', { method: 'POST', form })
  },
  analyzeFrame: (session_id, blob, signal) => {
    const form = new FormData(); form.append('session_id', session_id); form.append('frame', blob, 'f.jpg')
    return request('/api/behavior/analyze', { method: 'POST', form, signal })
  },
  behaviorEvent: (session_id, type) => request('/api/behavior/event', { method: 'POST', body: { session_id, type } }),
  dashboard: (id) => request(`/api/dashboard/${id}`),
  report: (id) => request(`/api/report/${id}`),
  reportPdf: (id) => request(`/api/report/${id}/pdf`, { blob: true }),
}
