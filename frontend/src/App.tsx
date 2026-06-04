import { useState, useEffect, useCallback, useRef } from 'react'
import Sidebar from './components/Sidebar'
import LogPanel, { parseLogLine } from './components/LogPanel'
import Dashboard    from './screens/Dashboard'
import GithubIntel  from './screens/GithubIntel'
import JobDiscovery from './screens/JobDiscovery'
import Applications from './screens/Applications'
import Offers       from './screens/Offers'
import InterviewPrep from './screens/InterviewPrep'
import NewSessionModal from './modals/NewSessionModal'
import OfferModal      from './modals/OfferModal'
import PrepModal       from './modals/PrepModal'
import ApprovalModal   from './modals/ApprovalModal'
import { api, createSSE, nowTs } from './api'
import type { AuthState, Session, DashboardSummary, Screen, ModalType, ModuleState, LogEntry, PendingApproval } from './types'

let logIdCounter = 0

export default function App() {
  const [screen,       setScreen]       = useState<Screen>('dashboard')
  const [auth,         setAuth]         = useState<AuthState | null>(null)
  const [sessions,     setSessions]     = useState<Session[]>([])
  const [threadId,     setThreadIdRaw]  = useState<string | null>(null)
  const [summary,      setSummary]      = useState<DashboardSummary | null>(null)
  const [moduleStates, setModuleStates] = useState<Record<string, ModuleState>>({})
  const [logs,         setLogs]         = useState<LogEntry[]>([])
  const [activeJobId,  setActiveJobId]  = useState<string | null>(null)
  const [modal,        setModal]        = useState<ModalType>(null)
  const [pending,      setPending]      = useState<PendingApproval | null>(null)
  const [approving,    setApproving]    = useState(false)
  const sseCleanup   = useRef<(() => void) | null>(null)
  const threadIdRef  = useRef<string | null>(null)
  threadIdRef.current = threadId

  // ── Auth ────────────────────────────────────────────────────────────────────

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const uid = params.get('user_id')
    if (uid) {
      const a: AuthState = {
        userId:   uid,
        username: params.get('username') ?? '',
        avatar:   params.get('avatar')   ?? '',
      }
      setAuth(a)
      localStorage.setItem('jh_auth', JSON.stringify(a))
      window.history.replaceState({}, '', '/')
    } else {
      const stored = localStorage.getItem('jh_auth')
      if (stored) try { setAuth(JSON.parse(stored)) } catch { /* ignore */ }
    }
  }, [])

  function handleLogout() {
    setAuth(null)
    localStorage.removeItem('jh_auth')
    localStorage.removeItem('jh_thread_id')
    setThreadIdRaw(null)
    setSummary(null)
    setSessions([])
  }

  // ── Session ─────────────────────────────────────────────────────────────────

  const setThreadId = useCallback((id: string | null) => {
    setThreadIdRaw(id)
    if (id) {
      localStorage.setItem('jh_thread_id', id)
      connectSSE(id)
      loadSummary(id)
    } else {
      localStorage.removeItem('jh_thread_id')
      setSummary(null)
    }
  }, [])

  useEffect(() => {
    const stored = localStorage.getItem('jh_thread_id')
    if (stored) setThreadIdRaw(stored)
    loadSessions()
  }, [auth])

  useEffect(() => {
    if (threadId) {
      connectSSE(threadId)
      loadSummary(threadId)
      checkPending(threadId)   // resurface the approval gate if one is open
    } else {
      setPending(null)
    }
    return () => { sseCleanup.current?.() }
  }, [threadId])

  async function loadSessions() {
    try {
      const list = await api.sessions.list(auth?.userId)
      setSessions(list)
    } catch { /* ignore */ }
  }

  async function loadSummary(id: string) {
    try {
      const data = await api.sessions.summary(id)
      setSummary(data)
    } catch { /* ignore */ }
  }

  function connectSSE(id: string) {
    sseCleanup.current?.()
    sseCleanup.current = createSSE(
      id,
      (msg) => addLog(msg),
      (signal) => {
        if (signal === 'interrupt') {
          // Pipeline paused at the approval gate — surface the review modal
          checkPending(id)
        }
      },
    )
  }

  function addLog(raw: string) {
    const entry = parseLogLine(raw, logIdCounter++)
    setLogs(prev => [entry, ...prev].slice(0, 80))
  }

  // ── Human approval gate ────────────────────────────────────────────────────────

  async function checkPending(id: string) {
    try {
      const p = await api.sessions.pending(id)
      setPending(p.awaiting ? p : null)
    } catch {
      setPending(null)
    }
  }

  async function handleApprovalDecision(approved: boolean) {
    const id = threadIdRef.current
    if (!id) return
    setApproving(true)
    addLog(`[SYSTEM] ${approved ? 'Approving' : 'Skipping'} application…`)
    try {
      const { job_id } = await api.resume(id, approved)
      setActiveJobId(job_id)
      // Poll the resume job — it either re-interrupts (next app) or finishes
      pollResume(job_id, id)
    } catch {
      addLog('[ERROR] Failed to submit approval decision')
      setApproving(false)
    }
  }

  function pollResume(jobId: string, id: string) {
    const iv = setInterval(async () => {
      try {
        const j = await api.jobs.poll(jobId)
        if (j.status === 'awaiting_approval') {
          clearInterval(iv)
          setActiveJobId(null)
          setApproving(false)
          await checkPending(id)            // surfaces the next queued application
        } else if (j.status === 'done') {
          clearInterval(iv)
          setActiveJobId(null)
          setApproving(false)
          setPending(null)                  // queue cleared
          setModuleStates(prev => ({ ...prev, application: { status: 'done', ts: nowTs() } }))
          addLog('[SYSTEM] ✓ All applications processed')
          loadSummary(id)
        } else if (j.status === 'failed') {
          clearInterval(iv)
          setActiveJobId(null)
          setApproving(false)
          addLog(`[ERROR] Submission failed: ${j.error ?? 'unknown'}`)
        }
      } catch { /* retry */ }
    }, 2000)
  }

  // ── Session creation ─────────────────────────────────────────────────────────

  async function handleCreateSession(body: Record<string, string>) {
    const data = await api.sessions.create(body)
    await loadSessions()
    setThreadId(data.thread_id)
  }

  // ── Module runner ─────────────────────────────────────────────────────────────

  async function handleRunModule(key: string) {
    if (!threadId) { setModal('new-session'); return }
    if (activeJobId) return

    if (key === 'offer') { setModal('offer'); return }
    if (key === 'prep')  { setModal('prep');  return }

    const endpointMap: Record<string, string> = {
      github: 'github', discovery: 'discovery', application: 'application', status: 'status',
    }
    const endpoint = endpointMap[key]
    if (!endpoint) return

    let body: Record<string, unknown> = { thread_id: threadId }
    if (auth) body.user_id = auth.userId

    setModuleStates(prev => ({ ...prev, [key]: { status: 'running', ts: nowTs() } }))
    addLog(`[SYSTEM] Starting ${key} module…`)

    try {
      const { job_id } = await api.modules.run(endpoint, body)
      setActiveJobId(job_id)
      addLog(`[SYSTEM] Job ${job_id.slice(0, 8)}… dispatched`)
      pollJob(job_id, key)
    } catch {
      setModuleStates(prev => ({ ...prev, [key]: { status: 'error', ts: nowTs() } }))
      addLog(`[ERROR] Failed to start ${key}`)
    }
  }

  function pollJob(jobId: string, moduleKey: string) {
    const iv = setInterval(async () => {
      try {
        const j = await api.jobs.poll(jobId)
        const id = threadIdRef.current
        if (j.status === 'awaiting_approval') {
          // Application engine paused at the human approval gate
          clearInterval(iv)
          setActiveJobId(null)
          setModuleStates(prev => ({ ...prev, [moduleKey]: { status: 'warn', ts: nowTs() } }))
          addLog('[SYSTEM] ⏸ Awaiting your approval')
          if (id) await checkPending(id)
        } else if (j.status === 'done') {
          clearInterval(iv)
          setActiveJobId(null)
          setModuleStates(prev => ({ ...prev, [moduleKey]: { status: 'done', ts: nowTs() } }))
          addLog(`[SYSTEM] ✓ ${moduleKey} completed`)
          if (id) loadSummary(id)
        } else if (j.status === 'failed') {
          clearInterval(iv)
          setActiveJobId(null)
          setModuleStates(prev => ({ ...prev, [moduleKey]: { status: 'error', ts: nowTs() } }))
          addLog(`[ERROR] ${moduleKey} failed: ${j.error ?? 'unknown'}`)
        }
      } catch { /* retry */ }
    }, 2000)
  }

  // ── Demo: seed a synthetic job to exercise the approval gate ───────────────────

  async function handleSeedTestJob() {
    const id = threadIdRef.current
    if (!id) { setModal('new-session'); return }
    if (activeJobId) return
    try {
      await api.sessions.seedTestJob(id)
      addLog('[SYSTEM] Seeded demo job — running Application Engine…')
      handleRunModule('application')
    } catch {
      addLog('[ERROR] Failed to seed demo job')
    }
  }

  // ── Offer submission ─────────────────────────────────────────────────────────

  async function handleOfferSubmit(data: {
    company: string; job_title: string; offer_letter_text: string; deadline_date: string | null
  }) {
    if (!threadId) return
    const body = { thread_id: threadId, ...data, ...(auth ? { user_id: auth.userId } : {}) }
    setModuleStates(prev => ({ ...prev, offer: { status: 'running', ts: nowTs() } }))
    addLog('[SYSTEM] Offer evaluation started…')
    const { job_id } = await api.modules.run('offer', body)
    setActiveJobId(job_id)
    pollJob(job_id, 'offer')
    setModal(null)
  }

  // ── Prep submission ───────────────────────────────────────────────────────────

  async function handlePrepSubmit(data: {
    company: string; role: string; company_url: string; jd_text: string
  }) {
    let tid = threadId
    const body: Record<string, unknown> = { ...data, ...(auth ? { user_id: auth.userId } : {}) }
    if (tid) body.thread_id = tid

    setModuleStates(prev => ({ ...prev, prep: { status: 'running', ts: nowTs() } }))
    addLog('[SYSTEM] Interview prep started…')

    const res = await api.modules.run('prep', body)
    if (!tid && res.thread_id) {
      tid = res.thread_id
      setThreadId(tid)
      await loadSessions()
    }
    setActiveJobId(res.job_id)
    pollJob(res.job_id, 'prep')
    setModal(null)
  }

  const currentPhase = summary?.current_phase ?? 'idle'

  return (
    <div className="flex h-screen bg-[#050709] text-slate-200 overflow-hidden">

      <Sidebar
        screen={screen}
        setScreen={setScreen}
        auth={auth}
        onLogout={handleLogout}
        sessions={sessions}
        threadId={threadId}
        setThreadId={setThreadId}
        currentPhase={currentPhase}
        onNewSession={() => setModal('new-session')}
      />

      <div className="flex flex-col flex-1 min-w-0 overflow-hidden">

        {/* Screen area */}
        <div className="flex-1 overflow-hidden flex flex-col bg-[#060810]">
          {screen === 'dashboard'    && <Dashboard    summary={summary} moduleStates={moduleStates} onRunModule={handleRunModule} onRefresh={() => threadId && loadSummary(threadId)} activeJobId={activeJobId} onNavigate={(s) => setScreen(s as import('./types').Screen)} />}
          {screen === 'github'       && <GithubIntel  threadId={threadId} moduleState={moduleStates['github']      ?? { status: 'idle' }} onRunModule={handleRunModule} activeJobId={activeJobId} />}
          {screen === 'discovery'    && <JobDiscovery threadId={threadId} moduleState={moduleStates['discovery']   ?? { status: 'idle' }} onRunModule={handleRunModule} activeJobId={activeJobId} />}
          {screen === 'applications' && <Applications threadId={threadId} moduleState={moduleStates['application'] ?? { status: 'idle' }} onRunModule={handleRunModule} onSeedTestJob={handleSeedTestJob} activeJobId={activeJobId} />}
          {screen === 'offers'       && <Offers       threadId={threadId} moduleState={moduleStates['offer']       ?? { status: 'idle' }} onRunModule={handleRunModule} onOpenOfferModal={() => setModal('offer')} activeJobId={activeJobId} />}
          {screen === 'interview'    && <InterviewPrep threadId={threadId} moduleState={moduleStates['prep']       ?? { status: 'idle' }} onOpenPrepModal={() => setModal('prep')} activeJobId={activeJobId} />}
        </div>

        {/* Log panel */}
        <LogPanel logs={logs} onClear={() => setLogs([])} />
      </div>

      {/* Modals */}
      {modal === 'new-session' && (
        <NewSessionModal
          auth={auth}
          onClose={() => setModal(null)}
          onSubmit={handleCreateSession}
        />
      )}
      {modal === 'offer' && (
        <OfferModal
          onClose={() => setModal(null)}
          onSubmit={handleOfferSubmit}
        />
      )}
      {modal === 'prep' && (
        <PrepModal
          onClose={() => setModal(null)}
          onSubmit={handlePrepSubmit}
        />
      )}

      {/* Human Approval Gate — blocking, auto-surfaced when the pipeline pauses */}
      {pending?.awaiting && (
        <ApprovalModal
          pending={pending}
          onDecision={handleApprovalDecision}
          submitting={approving}
        />
      )}
    </div>
  )
}
