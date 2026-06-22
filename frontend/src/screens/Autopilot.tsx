import { useState, useEffect, useRef, useCallback } from 'react'
import { Bot, Play, Save, X, Plus, Clock, Zap, CheckCircle, AlertCircle, Loader2 } from 'lucide-react'
import { api, createSSE, nowTs } from '../api'
import LogPanel, { parseLogLine } from '../components/LogPanel'
import type { AutopilotConfig, AutopilotStatus, AutopilotLastRun, LogEntry, SeniorityLevel } from '../types'

let _logId = 0

const SENIORITY_OPTIONS: SeniorityLevel[] = ['fresher', 'junior', 'mid', 'senior', 'lead']

const DEFAULT_CONFIG: AutopilotConfig = {
  enabled: false,
  at: '08:00',
  role: 'AI Engineer',
  niche: 'Agentic AI',
  market: 'India',
  github_username: '',
  filters: { max_seniority: 'junior', locations: [], remote_ok: true, min_score: 0 },
}

function fmt(iso: string | undefined): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString(undefined, {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  })
}

function countdown(iso: string | null): string {
  if (!iso) return '—'
  const diff = new Date(iso).getTime() - Date.now()
  if (diff <= 0) return 'soon'
  const h = Math.floor(diff / 3600000)
  const m = Math.floor((diff % 3600000) / 60000)
  return h > 0 ? `${h}h ${m}m` : `${m}m`
}

// ── Sub-components ────────────────────────────────────────────────────────────

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-white/[0.08] bg-white/[0.02] overflow-hidden">
      <div className="px-5 py-3 border-b border-white/[0.06]">
        <span className="text-[11px] font-bold text-slate-500 uppercase tracking-[0.14em]">{title}</span>
      </div>
      <div className="p-5">{children}</div>
    </div>
  )
}

function Toggle({ value, onChange }: { value: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      onClick={() => onChange(!value)}
      className="relative w-11 h-6 rounded-full transition-colors duration-200 focus:outline-none"
      style={{ background: value ? '#A78BFA' : 'rgba(255,255,255,0.08)' }}
    >
      <span
        className="absolute top-1 w-4 h-4 rounded-full bg-white shadow transition-transform duration-200"
        style={{ transform: value ? 'translateX(24px)' : 'translateX(4px)' }}
      />
    </button>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-4 min-h-[36px]">
      <span className="text-xs text-slate-500 w-32 flex-shrink-0">{label}</span>
      <div className="flex-1">{children}</div>
    </div>
  )
}

function TextInput({ value, onChange, placeholder }: { value: string; onChange: (v: string) => void; placeholder?: string }) {
  return (
    <input
      value={value}
      onChange={e => onChange(e.target.value)}
      placeholder={placeholder}
      className="w-full bg-white/[0.04] border border-white/[0.1] rounded-lg px-3 py-1.5 text-xs text-slate-200 placeholder-slate-600 outline-none focus:border-violet-500/50 transition-colors"
    />
  )
}

// ── Main screen ────────────────────────────────────────────────────────────────

export default function Autopilot() {
  const [status, setStatus]     = useState<AutopilotStatus | null>(null)
  const [cfg, setCfg]           = useState<AutopilotConfig>(DEFAULT_CONFIG)
  const [dirty, setDirty]       = useState(false)
  const [saving, setSaving]     = useState(false)
  const [saveOk, setSaveOk]     = useState(false)
  const [running, setRunning]   = useState(false)
  const [logs, setLogs]         = useState<LogEntry[]>([])
  const [ticker, setTicker]     = useState(0)
  const [locInput, setLocInput] = useState('')
  const sseCleanup = useRef<(() => void) | null>(null)

  // countdown ticker — refresh every 30s
  useEffect(() => {
    const iv = setInterval(() => setTicker(t => t + 1), 30000)
    return () => clearInterval(iv)
  }, [])

  const load = useCallback(async () => {
    try {
      const s = await api.autopilot.status()
      setStatus(s)
      setCfg(s.config)
      setDirty(false)
    } catch { /* backend might not be running */ }
  }, [])

  useEffect(() => { load() }, [load])

  function update(patch: Partial<AutopilotConfig>) {
    setCfg(prev => ({ ...prev, ...patch }))
    setDirty(true)
    setSaveOk(false)
  }

  function updateFilter(patch: Partial<AutopilotConfig['filters']>) {
    setCfg(prev => ({ ...prev, filters: { ...prev.filters, ...patch } }))
    setDirty(true)
    setSaveOk(false)
  }

  async function handleSave() {
    setSaving(true)
    try {
      await api.autopilot.updateConfig(cfg)
      setSaveOk(true)
      setDirty(false)
      await load()
    } catch { /* show nothing extra */ }
    setSaving(false)
  }

  function addLog(raw: string) {
    const id = ++_logId
    setLogs(prev => [...prev, parseLogLine(raw, id)])
  }

  async function handleRunNow() {
    if (running) return
    sseCleanup.current?.()
    setLogs([])
    setRunning(true)
    addLog('[SYSTEM] Starting autopilot discovery run…')
    try {
      const { thread_id } = await api.autopilot.runNow()
      const cleanup = createSSE(
        thread_id,
        (msg) => addLog(msg),
        (signal) => {
          if (signal === 'done') {
            addLog('[SYSTEM] ✓ Autopilot run complete — check your email for the digest')
            setRunning(false)
            load()
          } else if (signal === 'error') {
            addLog('[ERROR] Autopilot run failed')
            setRunning(false)
          }
        },
      )
      sseCleanup.current = cleanup
    } catch {
      addLog('[ERROR] Failed to start run')
      setRunning(false)
    }
  }

  function addLocation() {
    const v = locInput.trim()
    if (!v || cfg.filters.locations.includes(v)) { setLocInput(''); return }
    updateFilter({ locations: [...cfg.filters.locations, v] })
    setLocInput('')
  }

  function removeLocation(loc: string) {
    updateFilter({ locations: cfg.filters.locations.filter(l => l !== loc) })
  }

  const lr = status?.last_run as AutopilotLastRun | null
  const nextRun = status?.next_run ?? null

  return (
    <div className="flex flex-col h-full overflow-hidden">

      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div className="flex-shrink-0 px-6 pt-5 pb-4 border-b border-white/[0.06]">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl" style={{ background: 'rgba(167,139,250,0.1)', border: '1px solid rgba(167,139,250,0.2)' }}>
              <Bot size={18} style={{ color: '#A78BFA' }} />
            </div>
            <div>
              <h1 className="text-sm font-bold text-slate-100">Autopilot</h1>
              <p className="text-[10px] text-slate-500 mt-0.5">Autonomous daily discovery with Gmail digest delivery</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {dirty && (
              <button
                onClick={handleSave}
                disabled={saving}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all"
                style={{ background: 'rgba(167,139,250,0.15)', border: '1px solid rgba(167,139,250,0.3)', color: '#A78BFA' }}
              >
                {saving ? <Loader2 size={12} className="animate-spin" /> : <Save size={12} />}
                {saving ? 'Saving…' : 'Save'}
              </button>
            )}
            {saveOk && !dirty && (
              <span className="flex items-center gap-1 text-[10px] text-emerald-400">
                <CheckCircle size={11} /> Saved
              </span>
            )}
            <button
              onClick={handleRunNow}
              disabled={running}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all"
              style={{
                background: running ? 'rgba(255,255,255,0.05)' : 'rgba(167,139,250,0.2)',
                border: '1px solid rgba(167,139,250,0.35)',
                color: running ? '#64748b' : '#A78BFA',
              }}
            >
              {running ? <Loader2 size={12} className="animate-spin" /> : <Play size={12} />}
              {running ? 'Running…' : 'Run Now'}
            </button>
          </div>
        </div>
      </div>

      {/* ── Body ───────────────────────────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto px-6 py-5 space-y-4">

        {/* ── Status row ──────────────────────────────────────────────────── */}
        <div className="grid grid-cols-3 gap-3">

          {/* Enabled toggle */}
          <div className="rounded-2xl border border-white/[0.08] bg-white/[0.02] p-4 flex items-center justify-between">
            <div>
              <div className="text-xs font-semibold text-slate-300">Scheduler</div>
              <div className="text-[10px] text-slate-600 mt-0.5">{cfg.enabled ? 'Running daily' : 'Disabled'}</div>
            </div>
            <Toggle value={cfg.enabled} onChange={v => update({ enabled: v })} />
          </div>

          {/* Next run */}
          <div className="rounded-2xl border border-white/[0.08] bg-white/[0.02] p-4">
            <div className="flex items-center gap-2 mb-1">
              <Clock size={12} style={{ color: '#A78BFA' }} />
              <span className="text-[10px] text-slate-500 uppercase tracking-wide">Next run</span>
            </div>
            <div className="text-sm font-bold text-slate-200">
              {cfg.enabled && nextRun ? countdown(nextRun) : '—'}
            </div>
            <div className="text-[10px] text-slate-600 mt-0.5">
              {cfg.enabled && nextRun ? fmt(nextRun) : 'Enable to schedule'}
            </div>
          </div>

          {/* Last run */}
          <div className="rounded-2xl border border-white/[0.08] bg-white/[0.02] p-4">
            <div className="flex items-center gap-2 mb-1">
              {lr?.error
                ? <AlertCircle size={12} className="text-red-400" />
                : <Zap size={12} style={{ color: '#10B981' }} />
              }
              <span className="text-[10px] text-slate-500 uppercase tracking-wide">Last run</span>
            </div>
            {lr ? (
              lr.error ? (
                <div className="text-xs text-red-400 truncate">{lr.error}</div>
              ) : (
                <>
                  <div className="text-sm font-bold text-slate-200">
                    {lr.new_jobs ?? 0} new · {lr.high_priority ?? 0} hot
                  </div>
                  <div className="text-[10px] text-slate-600 mt-0.5">{fmt(lr.ran_at)}</div>
                </>
              )
            ) : (
              <div className="text-xs text-slate-600">Never run</div>
            )}
          </div>
        </div>

        {/* ── Config ──────────────────────────────────────────────────────── */}
        <Card title="Configuration">
          <div className="space-y-3">
            <Field label="Target role">
              <TextInput value={cfg.role} onChange={v => update({ role: v })} placeholder="e.g. AI Engineer" />
            </Field>
            <Field label="Niche">
              <TextInput value={cfg.niche} onChange={v => update({ niche: v })} placeholder="e.g. Agentic AI" />
            </Field>
            <Field label="Market">
              <TextInput value={cfg.market} onChange={v => update({ market: v })} placeholder="e.g. India" />
            </Field>
            <Field label="GitHub username">
              <TextInput value={cfg.github_username} onChange={v => update({ github_username: v })} placeholder="Used for profile context (optional)" />
            </Field>
            <Field label="Daily time (UTC)">
              <input
                type="time"
                value={cfg.at}
                onChange={e => update({ at: e.target.value })}
                className="bg-white/[0.04] border border-white/[0.1] rounded-lg px-3 py-1.5 text-xs text-slate-200 outline-none focus:border-violet-500/50 transition-colors"
              />
            </Field>
          </div>
        </Card>

        {/* ── Filters ─────────────────────────────────────────────────────── */}
        <Card title="Discovery Filters">
          <div className="space-y-4">

            {/* Seniority */}
            <Field label="Max seniority">
              <div className="flex gap-1.5 flex-wrap">
                {SENIORITY_OPTIONS.map(s => {
                  const active = cfg.filters.max_seniority === s
                  return (
                    <button
                      key={s}
                      onClick={() => updateFilter({ max_seniority: s })}
                      className="px-2.5 py-1 rounded-lg text-[10px] font-semibold capitalize transition-all"
                      style={active ? {
                        background: 'rgba(167,139,250,0.2)',
                        border: '1px solid rgba(167,139,250,0.4)',
                        color: '#A78BFA',
                      } : {
                        background: 'rgba(255,255,255,0.03)',
                        border: '1px solid rgba(255,255,255,0.08)',
                        color: '#64748b',
                      }}
                    >
                      {s}
                    </button>
                  )
                })}
              </div>
            </Field>

            {/* Locations */}
            <Field label="Locations">
              <div className="flex flex-wrap gap-1.5 mb-2">
                {cfg.filters.locations.map(loc => (
                  <span
                    key={loc}
                    className="inline-flex items-center gap-1 px-2 py-0.5 rounded-lg text-[10px] text-slate-300"
                    style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)' }}
                  >
                    {loc}
                    <button onClick={() => removeLocation(loc)} className="text-slate-600 hover:text-red-400 transition-colors">
                      <X size={9} />
                    </button>
                  </span>
                ))}
                {cfg.filters.locations.length === 0 && (
                  <span className="text-[10px] text-slate-600">No location filter — all locations accepted</span>
                )}
              </div>
              <div className="flex gap-2">
                <input
                  value={locInput}
                  onChange={e => setLocInput(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && addLocation()}
                  placeholder="Add city…"
                  className="flex-1 bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-1.5 text-xs text-slate-200 placeholder-slate-600 outline-none focus:border-violet-500/50 transition-colors"
                />
                <button
                  onClick={addLocation}
                  className="p-1.5 rounded-lg transition-colors"
                  style={{ background: 'rgba(167,139,250,0.1)', border: '1px solid rgba(167,139,250,0.2)', color: '#A78BFA' }}
                >
                  <Plus size={13} />
                </button>
              </div>
            </Field>

            {/* Remote */}
            <Field label="Include remote">
              <div className="flex items-center gap-3">
                <Toggle value={cfg.filters.remote_ok} onChange={v => updateFilter({ remote_ok: v })} />
                <span className="text-[10px] text-slate-500">
                  {cfg.filters.remote_ok ? 'Remote jobs bypass location filter' : 'Remote jobs excluded'}
                </span>
              </div>
            </Field>

            {/* Min score */}
            <Field label={`Min score: ${cfg.filters.min_score}`}>
              <div className="flex items-center gap-3">
                <input
                  type="range"
                  min={0}
                  max={90}
                  step={5}
                  value={cfg.filters.min_score}
                  onChange={e => updateFilter({ min_score: Number(e.target.value) })}
                  className="flex-1 accent-violet-400 cursor-pointer"
                />
                <span className="text-[10px] text-slate-500 w-16">
                  {cfg.filters.min_score === 0 ? 'No cut-off' : `≥ ${cfg.filters.min_score}/100`}
                </span>
              </div>
            </Field>
          </div>
        </Card>

        {/* ── Live log ─────────────────────────────────────────────────────── */}
        {logs.length > 0 && (
          <Card title="Live log">
            <div className="space-y-0.5 max-h-64 overflow-y-auto font-mono text-[10px]">
              {logs.map(l => (
                <div key={l.id} className="flex gap-2 leading-5">
                  <span className="text-slate-700 flex-shrink-0">{l.ts}</span>
                  <span className={l.tagClass + ' flex-shrink-0'}>[{l.tag}]</span>
                  <span className={l.msgClass}>{l.msg}</span>
                </div>
              ))}
              {running && (
                <div className="flex items-center gap-2 text-slate-600 mt-1">
                  <Loader2 size={10} className="animate-spin" />
                  <span>Running…</span>
                </div>
              )}
            </div>
          </Card>
        )}
      </div>
    </div>
  )
}
