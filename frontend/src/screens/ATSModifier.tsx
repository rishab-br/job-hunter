import { useState, useEffect, useRef } from 'react'
import {
  FilePen, Loader2, Copy, Check, ChevronDown, ChevronUp,
  Plus, Minus, Zap, Tag, ArrowRight, Clock, Download,
} from 'lucide-react'
import { api, createSSE } from '../api'
import { parseLogLine } from '../components/LogPanel'
import type { ATSModifiedResume, LogEntry } from '../types'

let _logId = 0

// ── ATS score ring ─────────────────────────────────────────────────────────────

function ScoreRing({ score, size = 80 }: { score: number; size?: number }) {
  const r  = size / 2 - 7
  const cx = size / 2
  const circ = 2 * Math.PI * r
  const dash = (score / 10) * circ
  const color = score >= 7.5 ? '#10B981' : score >= 5 ? '#F97316' : '#EF4444'
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      <circle cx={cx} cy={cx} r={r} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth={6} />
      <circle
        cx={cx} cy={cx} r={r} fill="none"
        stroke={color} strokeWidth={6}
        strokeDasharray={`${dash} ${circ}`}
        strokeLinecap="round"
        transform={`rotate(-90 ${cx} ${cx})`}
        style={{ filter: `drop-shadow(0 0 5px ${color})`, transition: 'stroke-dasharray 0.7s ease' }}
      />
      <text x={cx} y={cx - 2} textAnchor="middle" fill={color} fontSize={size * 0.22} fontWeight={800} fontFamily="inherit">
        {score.toFixed(1)}
      </text>
      <text x={cx} y={cx + size * 0.16} textAnchor="middle" fill="#64748b" fontSize={size * 0.12} fontFamily="inherit">
        /10
      </text>
    </svg>
  )
}

// ── Keyword pill ───────────────────────────────────────────────────────────────

function Pill({ label, variant }: { label: string; variant: 'added' | 'matched' }) {
  const isAdded = variant === 'added'
  return (
    <span
      className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold"
      style={isAdded
        ? { background: 'rgba(249,115,22,0.12)', border: '1px solid rgba(249,115,22,0.3)', color: '#F97316' }
        : { background: 'rgba(96,165,250,0.10)', border: '1px solid rgba(96,165,250,0.25)', color: '#60A5FA' }}
    >
      {isAdded ? <Plus size={8} /> : <Check size={8} />}
      {label}
    </span>
  )
}

// ── Collapsible section ────────────────────────────────────────────────────────

function Section({ title, icon, color, children, defaultOpen = true }: {
  title: string; icon: React.ReactNode; color: string; children: React.ReactNode; defaultOpen?: boolean
}) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="rounded-xl border border-white/[0.07] overflow-hidden">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-4 py-3 text-left"
        style={{ borderBottom: open ? '1px solid rgba(255,255,255,0.06)' : 'none' }}
      >
        <div className="flex items-center gap-2">
          <span style={{ color }}>{icon}</span>
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">{title}</span>
        </div>
        <span className="text-slate-700">{open ? <ChevronUp size={12} /> : <ChevronDown size={12} />}</span>
      </button>
      {open && <div className="px-4 py-3">{children}</div>}
    </div>
  )
}

// ── Copy button ────────────────────────────────────────────────────────────────

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)
  function doCopy() {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }
  return (
    <button
      onClick={doCopy}
      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[10px] font-semibold transition-all"
      style={copied
        ? { background: 'rgba(16,185,129,0.15)', border: '1px solid rgba(16,185,129,0.35)', color: '#10B981' }
        : { background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.1)', color: '#64748b' }}
    >
      {copied ? <Check size={11} /> : <Copy size={11} />}
      {copied ? 'Copied!' : 'Copy'}
    </button>
  )
}

function DownloadPdfButton({ path }: { path: string }) {
  return (
    <a
      href={api.files.url(path)}
      download
      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[10px] font-bold transition-all"
      style={{ background: 'rgba(249,115,22,0.15)', border: '1px solid rgba(249,115,22,0.35)', color: '#F97316' }}
    >
      <Download size={11} />
      Download PDF
    </a>
  )
}

// ── History sidebar item ───────────────────────────────────────────────────────

function HistoryItem({ record, active, onClick }: {
  record: ATSModifiedResume; active: boolean; onClick: () => void
}) {
  const color = '#F97316'
  const score = record.ats_score_estimate
  const scoreColor = score >= 7.5 ? '#10B981' : score >= 5 ? '#F97316' : '#EF4444'
  return (
    <button
      onClick={onClick}
      className="w-full text-left px-3 py-2.5 rounded-xl transition-all"
      style={active
        ? { background: `${color}12`, border: `1px solid ${color}30` }
        : { background: 'transparent', border: '1px solid transparent' }}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="text-[11px] font-semibold text-slate-200 truncate">{record.company || 'Unknown'}</div>
          <div className="text-[10px] text-slate-500 truncate mt-0.5">{record.job_title}</div>
        </div>
        <span className="text-[10px] font-bold flex-shrink-0 mt-0.5" style={{ color: scoreColor }}>
          {score?.toFixed(1)}/10
        </span>
      </div>
      <div className="flex items-center gap-1 mt-1.5 text-[9px] text-slate-700">
        <Clock size={8} />
        {new Date(record.generated_at).toLocaleDateString()}
      </div>
    </button>
  )
}

// ── Result panel ───────────────────────────────────────────────────────────────

function ResultPanel({ record }: { record: ATSModifiedResume }) {
  const [tab, setTab] = useState<'resume' | 'changes'>('resume')

  return (
    <div className="flex flex-col gap-4 h-full">
      {/* Score header */}
      <div className="flex items-center gap-5 px-5 py-4 rounded-2xl border border-white/[0.08]"
           style={{ background: 'rgba(249,115,22,0.04)' }}>
        <ScoreRing score={record.ats_score_estimate ?? 0} size={76} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-sm font-bold text-slate-100 truncate">{record.company}</span>
            <ArrowRight size={12} className="text-slate-600 flex-shrink-0" />
            <span className="text-xs text-slate-400 truncate">{record.job_title}</span>
          </div>
          <div className="text-[10px] text-slate-600 mb-2.5">
            {record.keywords_added.length} keywords added · {record.changes.length} changes · {record.keywords_matched.length} matched
          </div>
          <div className="flex flex-wrap gap-1.5">
            {record.keywords_added.slice(0, 6).map(k => <Pill key={k} label={k} variant="added" />)}
            {record.keywords_matched.slice(0, 4).map(k => <Pill key={k} label={k} variant="matched" />)}
          </div>
        </div>
      </div>

      {/* Tab switcher */}
      <div className="flex gap-1 p-1 rounded-xl" style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)' }}>
        {(['resume', 'changes'] as const).map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className="flex-1 py-1.5 rounded-lg text-[10px] font-bold uppercase tracking-wider transition-all"
            style={tab === t
              ? { background: 'rgba(249,115,22,0.15)', border: '1px solid rgba(249,115,22,0.3)', color: '#F97316' }
              : { background: 'transparent', border: '1px solid transparent', color: '#475569' }}
          >
            {t === 'resume' ? 'Tailored Resume' : 'Changes Made'}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {tab === 'resume' && (
        <div className="flex flex-col flex-1 min-h-0 rounded-xl border border-white/[0.07] overflow-hidden">
          <div className="flex items-center justify-between px-4 py-2.5 border-b border-white/[0.06]"
               style={{ background: 'rgba(255,255,255,0.02)' }}>
            <span className="text-[10px] text-slate-500 font-mono">tailored_resume.md</span>
            <div className="flex items-center gap-2">
              {record.resume_pdf_path && <DownloadPdfButton path={record.resume_pdf_path} />}
              <CopyButton text={record.tailored_resume} />
            </div>
          </div>
          <div className="flex-1 overflow-y-auto p-4">
            <pre className="text-[11px] text-slate-300 leading-relaxed whitespace-pre-wrap font-mono">
              {record.tailored_resume}
            </pre>
          </div>
        </div>
      )}

      {tab === 'changes' && (
        <div className="space-y-3 overflow-y-auto flex-1">
          {/* Changes list */}
          <Section title="Changes Made" icon={<FilePen size={13} />} color="#F97316">
            <div className="space-y-2">
              {record.changes.map((c, i) => (
                <div key={i} className="flex gap-2.5 py-2 border-b border-white/[0.04] last:border-0">
                  <span className="w-4 h-4 rounded-full flex items-center justify-center text-[8px] font-bold flex-shrink-0 mt-0.5"
                        style={{ background: 'rgba(249,115,22,0.15)', border: '1px solid rgba(249,115,22,0.3)', color: '#F97316' }}>
                    {i + 1}
                  </span>
                  <div>
                    <span className="text-[9px] font-bold uppercase tracking-wider text-slate-600 mr-1.5">{c.section}</span>
                    <span className="text-[11px] text-slate-300">{c.change}</span>
                  </div>
                </div>
              ))}
            </div>
          </Section>

          {/* Keywords added */}
          <Section title="Keywords Added" icon={<Plus size={13} />} color="#F97316" defaultOpen={false}>
            <div className="flex flex-wrap gap-1.5 pt-1">
              {record.keywords_added.map(k => <Pill key={k} label={k} variant="added" />)}
              {record.keywords_added.length === 0 && <span className="text-[11px] text-slate-600">None added</span>}
            </div>
          </Section>

          {/* Keywords already matched */}
          <Section title="Keywords Already Present" icon={<Tag size={13} />} color="#60A5FA" defaultOpen={false}>
            <div className="flex flex-wrap gap-1.5 pt-1">
              {record.keywords_matched.map(k => <Pill key={k} label={k} variant="matched" />)}
              {record.keywords_matched.length === 0 && <span className="text-[11px] text-slate-600">None</span>}
            </div>
          </Section>
        </div>
      )}
    </div>
  )
}

// ── Main screen ────────────────────────────────────────────────────────────────

interface Props { threadId: string | null }

export default function ATSModifier({ threadId }: Props) {
  const [history, setHistory]   = useState<ATSModifiedResume[]>([])
  const [selected, setSelected] = useState<ATSModifiedResume | null>(null)
  const [hasResume, setHasResume] = useState(false)

  // Form
  const [jd, setJd]           = useState('')
  const [company, setCompany] = useState('')
  const [jobTitle, setJobTitle] = useState('')

  // Run state
  const [running, setRunning] = useState(false)
  const [logs, setLogs]       = useState<LogEntry[]>([])
  const [error, setError]     = useState<string | null>(null)
  const sseRef = useRef<(() => void) | null>(null)

  // Load existing history from session
  useEffect(() => {
    if (!threadId) return
    api.sessions.get(threadId).then(session => {
      const s = session as any
      if (s.ats_modified_resumes?.length) {
        setHistory(s.ats_modified_resumes)
        setSelected(s.ats_modified_resumes[0])
      }
      setHasResume(!!s.resume_text)
    }).catch(() => {})
  }, [threadId])

  function addLog(raw: string) {
    setLogs(prev => [...prev, parseLogLine(raw, ++_logId)])
  }

  async function handleGenerate() {
    if (!threadId || !jd.trim() || running) return
    sseRef.current?.()
    setLogs([])
    setError(null)
    setRunning(true)
    addLog(`[SYSTEM] Tailoring resume for ${company || 'company'}…`)

    try {
      const { job_id, thread_id } = await api.atsModifier.run(threadId, jd, company, jobTitle)
      addLog(`[SYSTEM] Job ${job_id.slice(0, 8)}… started`)

      const cleanup = createSSE(
        thread_id,
        msg => addLog(msg),
        async signal => {
          if (signal === 'done') {
            addLog('[SYSTEM] ✓ Tailoring complete')
            setRunning(false)
            try {
              const resp = await fetch(`/api/sessions/${thread_id}`)
              if (resp.ok) {
                const data = await resp.json()
                if (data?.ats_modified_resumes?.length) {
                  setHistory(data.ats_modified_resumes)
                  setSelected(data.ats_modified_resumes[0])
                }
              }
            } catch { /* ignore */ }
          } else if (signal === 'error') {
            setError('Tailoring failed — check logs')
            setRunning(false)
          }
        },
      )
      sseRef.current = cleanup
    } catch (e: any) {
      const msg = e?.message ?? 'Request failed'
      setError(msg.includes('422') ? 'No resume uploaded yet — run Resume Review first.' : msg)
      setRunning(false)
    }
  }

  const noSession = !threadId
  const canRun    = !noSession && jd.trim().length > 0 && !running

  return (
    <div className="flex flex-col h-full overflow-hidden">

      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div className="flex-shrink-0 px-6 pt-5 pb-4 border-b border-white/[0.06]">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl" style={{ background: 'rgba(249,115,22,0.1)', border: '1px solid rgba(249,115,22,0.2)' }}>
            <FilePen size={18} style={{ color: '#F97316' }} />
          </div>
          <div>
            <h1 className="text-sm font-bold text-slate-100">ATS Resume Modifier</h1>
            <p className="text-[10px] text-slate-500 mt-0.5">
              Paste a JD — LLM rewrites your resume with matched keywords, ATS-safe formatting, and targeted changes
            </p>
          </div>
        </div>
      </div>

      {/* ── Body: two-column layout ─────────────────────────────────────────── */}
      <div className="flex flex-1 min-h-0 overflow-hidden">

        {/* LEFT — Input + history ──────────────────────────────────────────── */}
        <div className="w-80 flex-shrink-0 flex flex-col border-r border-white/[0.06] overflow-hidden">
          <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">

            {noSession && (
              <div className="px-3 py-2.5 rounded-xl border border-amber-500/20 bg-amber-500/5 text-[11px] text-amber-400">
                Select a session to get started.
              </div>
            )}

            {!hasResume && !noSession && (
              <div className="px-3 py-2.5 rounded-xl border border-orange-500/20 bg-orange-500/5 text-[11px] text-orange-400">
                No resume uploaded yet. Run <strong>Resume Review</strong> first to upload your resume.
              </div>
            )}

            {/* Input form */}
            <div className="space-y-3">
              <div>
                <label className="block text-[9px] font-bold text-slate-600 uppercase tracking-wider mb-1.5">
                  Company
                </label>
                <input
                  value={company}
                  onChange={e => setCompany(e.target.value)}
                  placeholder="e.g. Google"
                  className="w-full px-3 py-2 rounded-xl text-xs text-slate-200 outline-none transition-all placeholder-slate-700"
                  style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.1)' }}
                  onFocus={e => (e.target.style.borderColor = 'rgba(249,115,22,0.4)')}
                  onBlur={e => (e.target.style.borderColor = 'rgba(255,255,255,0.1)')}
                />
              </div>

              <div>
                <label className="block text-[9px] font-bold text-slate-600 uppercase tracking-wider mb-1.5">
                  Job Title
                </label>
                <input
                  value={jobTitle}
                  onChange={e => setJobTitle(e.target.value)}
                  placeholder="e.g. Senior ML Engineer"
                  className="w-full px-3 py-2 rounded-xl text-xs text-slate-200 outline-none transition-all placeholder-slate-700"
                  style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.1)' }}
                  onFocus={e => (e.target.style.borderColor = 'rgba(249,115,22,0.4)')}
                  onBlur={e => (e.target.style.borderColor = 'rgba(255,255,255,0.1)')}
                />
              </div>

              <div>
                <label className="block text-[9px] font-bold text-slate-600 uppercase tracking-wider mb-1.5">
                  Job Description <span className="text-orange-500">*</span>
                </label>
                <textarea
                  value={jd}
                  onChange={e => setJd(e.target.value)}
                  placeholder="Paste the full job description here…"
                  rows={10}
                  className="w-full px-3 py-2 rounded-xl text-xs text-slate-200 outline-none resize-none transition-all placeholder-slate-700 leading-relaxed"
                  style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.1)' }}
                  onFocus={e => (e.target.style.borderColor = 'rgba(249,115,22,0.4)')}
                  onBlur={e => (e.target.style.borderColor = 'rgba(255,255,255,0.1)')}
                />
                {jd.length > 0 && (
                  <div className="text-[9px] text-slate-700 mt-1 text-right">{jd.length} chars</div>
                )}
              </div>

              <button
                onClick={handleGenerate}
                disabled={!canRun}
                className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl text-xs font-bold transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                style={{ background: 'rgba(249,115,22,0.15)', border: '1px solid rgba(249,115,22,0.35)', color: '#F97316' }}
              >
                {running
                  ? <><Loader2 size={13} className="animate-spin" />Generating…</>
                  : <><Zap size={13} />Tailor Resume</>}
              </button>

              {error && (
                <div className="px-3 py-2 rounded-xl border border-red-500/20 bg-red-500/5 text-[11px] text-red-400">
                  {error}
                </div>
              )}
            </div>

            {/* Live log */}
            {logs.length > 0 && (
              <div className="rounded-xl border border-white/[0.07] bg-black/20 p-3 max-h-36 overflow-y-auto font-mono space-y-0.5">
                {logs.map(l => (
                  <div key={l.id} className="flex gap-2 text-[9px] leading-5">
                    <span className="text-slate-700 flex-shrink-0">{l.ts}</span>
                    <span className={l.tagClass + ' flex-shrink-0'}>[{l.tag}]</span>
                    <span className={l.msgClass}>{l.msg}</span>
                  </div>
                ))}
                {running && <div className="flex items-center gap-1.5 text-slate-700 mt-1"><Loader2 size={9} className="animate-spin" />Running…</div>}
              </div>
            )}

            {/* History */}
            {history.length > 0 && (
              <div>
                <div className="text-[9px] font-bold text-slate-700 uppercase tracking-wider mb-2">
                  Previous Versions ({history.length})
                </div>
                <div className="space-y-1">
                  {history.map((r, i) => (
                    <HistoryItem
                      key={i}
                      record={r}
                      active={selected === r}
                      onClick={() => setSelected(r)}
                    />
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* RIGHT — Result ──────────────────────────────────────────────────── */}
        <div className="flex-1 min-w-0 overflow-hidden px-5 py-4">
          {selected ? (
            <ResultPanel record={selected} />
          ) : (
            <div className="h-full flex flex-col items-center justify-center gap-4 text-center">
              <div className="p-5 rounded-2xl" style={{ background: 'rgba(249,115,22,0.06)', border: '1px solid rgba(249,115,22,0.12)' }}>
                <FilePen size={32} style={{ color: 'rgba(249,115,22,0.4)' }} />
              </div>
              <div>
                <p className="text-sm font-semibold text-slate-500">No tailored resume yet</p>
                <p className="text-[11px] text-slate-700 mt-1">
                  Paste a job description on the left and hit <strong className="text-slate-500">Tailor Resume</strong>
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
