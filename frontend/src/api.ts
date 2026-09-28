// Everything the frontend needs to talk to the FastAPI backend.
// The types mirror backend/app/schemas.py.

export const STATUSES = ['saved', 'applied', 'interview', 'offer', 'rejected'] as const
export type Status = (typeof STATUSES)[number]

export interface Profile {
  name: string
  cv_text: string
  chunk_count: number
}

export interface Match {
  skill: string
  importance: 'must' | 'nice'
  matched: boolean
  note: string
  evidence: string[]
  similarity: number
}

export interface Application {
  id: number
  company: string
  role: string
  job_url: string
  job_text: string
  status: Status
  match_score: number
  matches: Match[]
  tailored_cv: string
  cover_letter: string
  notes: string
  created_at: string
  updated_at: string
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, init)
  if (!response.ok) {
    // FastAPI puts the error message in "detail"
    const body = await response.json().catch(() => null)
    const detail = body?.detail
    const message = typeof detail === 'string' ? detail : Array.isArray(detail) ? detail[0]?.msg : null
    throw new Error(message ?? `Request failed (${response.status})`)
  }
  return response.status === 204 ? (undefined as T) : response.json()
}

const json = (method: string, body: unknown): RequestInit => ({
  method,
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
})

export const api = {
  health: () => request<{ status: string; demo_mode: boolean }>('/health'),

  getProfile: () => request<Profile>('/profile'),
  saveProfile: (cv_text: string, name = '') => request<Profile>('/profile', json('PUT', { cv_text, name })),
  uploadCv: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return request<Profile>('/profile/upload', { method: 'POST', body: form })
  },

  listApplications: () => request<Application[]>('/applications'),
  getApplication: (id: number) => request<Application>(`/applications/${id}`),
  analyze: (job: { job_url?: string; job_text?: string }) =>
    request<Application>('/applications/analyze', json('POST', job)),
  updateApplication: (id: number, changes: Partial<Application>) =>
    request<Application>(`/applications/${id}`, json('PATCH', changes)),
  deleteApplication: (id: number) => request<void>(`/applications/${id}`, { method: 'DELETE' }),
}
