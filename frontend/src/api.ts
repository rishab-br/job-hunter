import type { DashboardSummary, GitHubIntelData, Job, Application, OfferEvaluation, PrepSession, Session } from './types'

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, options)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export const api = {
  sessions: {
    list: (userId?: string | null) =>
      request<Session[]>(userId ? `/api/sessions?user_id=${userId}` : '/api/sessions'),
    get: (threadId: string) =>
      request<Session>(`/api/sessions/${threadId}`),
    create: (body: Record<string, string>) =>
      request<{ thread_id: string }>('/api/sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      }),
    summary: (threadId: string) =>
      request<DashboardSummary>(`/api/sessions/${threadId}/summary`),
    audit: (threadId: string) =>
      request<GitHubIntelData>(`/api/sessions/${threadId}/audit`),
    jobs: (threadId: string) =>
      request<{ jobs: Job[] }>(`/api/sessions/${threadId}/jobs`),
    applications: (threadId: string) =>
      request<{ applications: Application[] }>(`/api/sessions/${threadId}/applications`),
    offers: (threadId: string) =>
      request<{ offers: OfferEvaluation[] }>(`/api/sessions/${threadId}/offers`),
    prep: (threadId: string) =>
      request<{ sessions: PrepSession[] }>(`/api/sessions/${threadId}/prep`),
  },

  modules: {
    run: (key: string, body: Record<string, unknown>) =>
      request<{ job_id: string; thread_id?: string }>(`/api/modules/${key}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      }),
  },

  jobs: {
    poll: (jobId: string) =>
      request<{ status: string; error?: string }>(`/api/jobs/${jobId}`),
  },
}

export function createSSE(threadId: string, onMessage: (msg: string) => void): () => void {
  const source = new EventSource(`/api/stream/${threadId}`)
  source.onmessage = (e) => {
    const msg = e.data as string
    if (!msg.startsWith('__DONE__') && !msg.startsWith('__ERROR__')) {
      onMessage(msg)
    }
  }
  return () => source.close()
}

export function nowTs(): string {
  return new Date().toTimeString().slice(0, 8)
}
