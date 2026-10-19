/**
 * 统一 API 客户端。
 * 关键点：401 自动刷新 token 并重放原请求；刷新也失败才登出。
 */
const BASE = import.meta.env.VITE_API_BASE || ''

let accessToken = localStorage.getItem('mcfit_access') || ''
let refreshToken = localStorage.getItem('mcfit_refresh') || ''
let onUnauthorized = null

export function setTokens(a, r) {
  accessToken = a || ''
  refreshToken = r || ''
  if (a) localStorage.setItem('mcfit_access', a)
  else localStorage.removeItem('mcfit_access')
  if (r) localStorage.setItem('mcfit_refresh', r)
  else localStorage.removeItem('mcfit_refresh')
}

export function getAccess() {
  return accessToken
}

export function onAuthFailure(cb) {
  onUnauthorized = cb
}

async function parse(res) {
  const text = await res.text()
  if (!text) return null
  try {
    return JSON.parse(text)
  } catch {
    return { detail: text }
  }
}

async function doRefresh() {
  if (!refreshToken) return false
  try {
    const res = await fetch(`${BASE}/api/v1/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    })
    if (!res.ok) return false
    const data = await res.json()
    setTokens(data.access_token, data.refresh_token)
    return true
  } catch {
    return false
  }
}

async function request(path, { method = 'GET', body, retry = true } = {}) {
  const headers = { 'Content-Type': 'application/json' }
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`

  let res
  try {
    res = await fetch(`${BASE}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch {
    throw new Error('网络连接失败，请确认后端已启动（默认 http://127.0.0.1:8000）')
  }

  if (res.status === 401 && retry && refreshToken) {
    if (await doRefresh()) return request(path, { method, body, retry: false })
    setTokens('', '')
    onUnauthorized && onUnauthorized()
  }

  const data = await parse(res)
  if (!res.ok) {
    const msg = data?.detail || `请求失败 (${res.status})`
    throw new Error(Array.isArray(msg) ? msg[0]?.msg || '请求失败' : msg)
  }
  return data
}

export const api = {
  get: (p) => request(p),
  post: (p, body) => request(p, { method: 'POST', body }),
  put: (p, body) => request(p, { method: 'PUT', body }),
  del: (p) => request(p, { method: 'DELETE' }),

  health: () => request('/health'),
}