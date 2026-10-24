export type ScanStatus = 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED'

export interface Project { id: number; name: string; created_at: string }

export interface Finding {
  file: string
  line: number
  symbol: string
  change_type: string
  explanation: string
  suggested_fix: string
  cited_ids: string[]
  confidence: number
  status: 'VERIFIED' | 'UNVERIFIED' | 'UNSUPPORTED_CLAIM'
  reject_reason: string | null
  source_urls: string[]
  patch: string | null
}

export interface UpdatedFile {
  path: string
  content: string
  diff: string
  auto_fixed: number[]
  llm_fixed: number[]
  manual: number[]
}

export interface ScanResult {
  findings: Finding[]
  rejected: Finding[]
  updated_files?: UpdatedFile[]
  files_scanned: number
  file_errors: Record<string, string>
  refs_found: number
  latency_s: number
  llm_calls: number
}

export interface Scan {
  id: number
  project_id: number
  status: ScanStatus
  from_version: string
  to_version: string
  provider: string
  retriever: string
  source_name: string
  findings_count: number
  error: string | null
  created_at: string
  finished_at: string | null
}

export interface ScanDetail extends Scan {
  result: ScanResult | null
  sources: { path: string; content: string }[]
}

export interface Meta {
  versions: string[]
  providers: string[]
  retrievers: string[]
  default: { from: string; to: string }
}

const TOKEN_KEY = 'codemigrate.token'

export function getToken(): string | null {
  try { return localStorage.getItem(TOKEN_KEY) } catch { return null }
}

export function setToken(token: string | null) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token)
    else localStorage.removeItem(TOKEN_KEY)
  } catch { /* storage unavailable: token lives only in memory for this tab */ }
}

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  const token = getToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)
  if (init.body && typeof init.body === 'string') headers.set('Content-Type', 'application/json')
  const res = await fetch(path, { ...init, headers })
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
    } catch { /* non-JSON error body */ }
    if (res.status === 401) setToken(null)
    throw new ApiError(res.status, detail)
  }
  return res.json() as Promise<T>
}

export const api = {
  register: (email: string, password: string) =>
    request('/api/auth/register', { method: 'POST', body: JSON.stringify({ email, password }) }),
  login: async (email: string, password: string) => {
    const form = new URLSearchParams({ username: email, password })
    const out = await request<{ access_token: string }>('/api/auth/token', { method: 'POST', body: form })
    setToken(out.access_token)
  },
  me: () => request<{ id: number; email: string }>('/api/auth/me'),
  meta: () => request<Meta>('/api/meta'),
  projects: () => request<Project[]>('/api/projects'),
  createProject: (name: string) =>
    request<Project>('/api/projects', { method: 'POST', body: JSON.stringify({ name }) }),
  createScan: (projectId: number, body: object) =>
    request<Scan>(`/api/projects/${projectId}/scans`, { method: 'POST', body: JSON.stringify(body) }),
  uploadScan: (projectId: number, form: FormData) =>
    request<Scan>(`/api/projects/${projectId}/scans/upload`, { method: 'POST', body: form }),
  scans: () => request<Scan[]>('/api/scans'),
  scan: (id: number) => request<ScanDetail>(`/api/scans/${id}`),
  results: (split = 'test') => request<{
    split: string
    comparison: Record<string, string | number>[]
    ablations: Record<string, string | number>[]
    figures: string[]
    meta: Record<string, unknown> | null
  }>(`/api/results?split=${split}`),
}

export async function download(path: string, filename: string) {
  const token = getToken()
  const res = await fetch(path, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
  if (!res.ok) throw new ApiError(res.status, res.statusText)
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}
