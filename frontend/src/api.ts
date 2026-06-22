import type { DashboardSummary, GitHubIntelData, Job, Application, OfferEvaluation, PrepSession, Session, PendingApproval, AutopilotConfig, AutopilotStatus } from './types'

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
    pending: (threadId: string) =>
      request<PendingApproval>(`/api/sessions/${threadId}/pending`),
    seedTestJob: (threadId: string) =>
      request<{ status: string; job_id: string }>(`/api/sessions/${threadId}/seed-test-job`, {
        method: 'POST',
      }),
  },

  modules: {
    run: (key: string, body: Record<string, unknown>) =>
      request<{ job_id: string; thread_id?: string }>(`/api/modules/${key}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      }),
  },

  // Resume the pipeline after an approval decision
  resume: (threadId: string, approved: boolean) =>
    request<{ job_id: string; thread_id: string }>('/api/resume', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ thread_id: threadId, approved }),
    }),

  jobs: {
    poll: (jobId: string) =>
      request<{ status: string; error?: string }>(`/api/jobs/${jobId}`),
  },


  resumeReview: {
    run: (threadId: string, file: File): Promise<{ job_id: string; thread_id: string }> => {
      const form = new FormData()
      form.append('file', file)
      form.append('thread_id', threadId)
      return fetch('/api/resume-review/run', { method: 'POST', body: form }).then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
    },
  },

  autopilot: {
    status: () =>
      request<AutopilotStatus>('/api/autopilot/status'),
    updateConfig: (cfg: AutopilotConfig) =>
      request<{ status: string; config: AutopilotConfig }>('/api/autopilot/config', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(cfg),
      }),
    runNow: () =>
      request<{ job_id: string; thread_id: string }>('/api/autopilot/run', { method: 'POST' }),
  },

  // Output files (resumes, cover letters, screenshots)
  files: {
    url: (path: string) => `/api/files?path=${encodeURIComponent(path)}`,
    text: (path: string) =>
      fetch(`/api/files?path=${encodeURIComponent(path)}`).then(r => (r.ok ? r.text() : '')),
    save: (path: string, content: string) =>
      request<{ status: string; path: string }>('/api/files/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path, content }),
      }),
  },
}

export function createSSE(
  threadId: string,
  onMessage: (msg: string) => void,
  onControl?: (signal: 'done' | 'error' | 'interrupt') => void,
): () => void {
  const source = new EventSource(`/api/stream/${threadId}`)
  source.onmessage = (e) => {
    const msg = e.data as string
    if (msg.startsWith('__INTERRUPT__')) { onControl?.('interrupt'); return }
    if (msg.startsWith('__DONE__'))      { onControl?.('done');      return }
    if (msg.startsWith('__ERROR__'))     { onControl?.('error');     return }
    onMessage(msg)
  }
  return () => source.close()
}

export function nowTs(): string {
  return new Date().toTimeString().slice(0, 8)
}
