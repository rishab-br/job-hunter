import { useState, useEffect, useRef } from 'react'
import {
  PenLine, Loader2, Copy, Check, ChevronDown, ChevronUp,
  Briefcase, Clock, Sparkles,
} from 'lucide-react'
import { api, createSSE } from '../api'
import { parseLogLine } from '../components/LogPanel'
import type { CoverLetter, LogEntry } from '../types'

let _logId = 0

type Tone = 'professional' | 'conversational' | 'enthusiastic'

const TONE_META: Record<Tone, { label: string; desc: string; color: string }> = {
  professional:   { label: 'Professional',   desc: 'Formal, polished — large enterprises',  color: '#60A5FA' },
  conversational: { label: 'Conversational', desc: 'Warm, human — modern teams',            color: '#34D399' },
  enthusiastic:   { label: 'Enthusiastic',   desc: 'Energetic, bold — startups',            color: '#F97316' },
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

// ── Collapsible section ────────────────────────────────────────────────────────

function Section({ title, icon, color, children }: {
  title: string; icon: React.ReactNode; color: string; children: React.ReactNode
}) {
  const [open, setOpen] = useState(true)
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

// ── Tone selector ──────────────────────────────────────────────────────────────

function TonePicker({ value, onChange }: { value: Tone; onChange: (t: Tone) => void }) {
  return (
    <div className="flex gap-1.5">
      {(Object.entries(TONE_META) as [Tone, typeof TONE_META[Tone]][]).map(([key, meta]) => (
        <button
          key={key}
          onClick={() => onChange(key)}
          className="flex-1 py-2 px-2 rounded-xl text-[10px] font-bold transition-all text-center leading-tight"
          style={value === key
            ? { background: `${meta.color}18`, border: `1px solid ${meta.color}45`, color: meta.color }
            : { background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)', color: '#475569' }}
        >
          {meta.label}
        </button>
      ))}
    </div>
  )
}

// ── History item ───────────────────────────────────────────────────────────────

function HistoryItem({ record, active, onClick }: {
  record: CoverLetter; active: boolean; onClick: () => void
}) {
  const toneColor = TONE_META[record.tone]?.color ?? '#60A5FA'
  return (
    <button
      onClick={onClick}
      className="w-full text-left px-3 py-2.5 rounded-xl transition-all"
      style={active
        ? { background: 'rgba(14,165,233,0.1)', border: '1px solid rgba(14,165,233,0.25)' }
        : { background: 'transparent', border: '1px solid transparent' }}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="text-[11px] font-semibold text-slate-200 truncate">{record.company || 'Unknown'}</div>
          <div className="text-[10px] text-slate-500 truncate mt-0.5">{record.job_title}</div>
        </div>
        <span className="text-[9px] font-bold flex-shrink-0 mt-0.5 capitalize" style={{ color: toneColor }}>
          {record.tone}
        </span>
      </div>
      <div className="flex items-center gap-2 mt-1.5 text-[9px] text-slate-700">
        <Clock size={8} />
        {new Date(record.generated_at).toLocaleDateString()}
        {record.word_count && (
          <span className="ml-auto">{record.word_count}w</span>
        )}
      </div>
    </button>
  )
}

// ── Result panel ───────────────────────────────────────────────────────────────

function ResultPanel({ record }: { record: CoverLetter }) {
  const toneColor = TONE_META[record.tone]?.color ?? '#60A5FA'

  return (
    <div className="flex flex-col gap-4 h-full">
      {/* Meta row */}
      <div className="flex items-center gap-3 px-4 py-3 rounded-xl border border-white/[0.07]"
           style={{ background: 'rgba(14,165,233,0.04)' }}>
        <div className="p-2 rounded-lg" style={{ background: 'rgba(14,165,233,0.1)', border: '1px solid rgba(14,165,233,0.2)' }}>
          <PenLine size={15} style={{ color: '#0EA5E9' }} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-xs font-bold text-slate-200">
            {record.company} <span className="text-slate-600 font-normal">·</span> {record.job_title}
          </div>
          <div className="flex items-center gap-2 mt-0.5">
            <span className="text-[9px] font-bold capitalize px-1.5 py-0.5 rounded-md"
                  style={{ background: `${toneColor}15`, border: `1px solid ${toneColor}30`, color: toneColor }}>
              {record.tone}
            </span>
            {record.word_count && (
              <span className="text-[9px] text-slate-600">{record.word_count} words</span>
            )}
            {!record.has_jd && (
              <span className="text-[9px] text-amber-600">no JD provided</span>
            )}
          </div>
        </div>
      </div>

      {/* Letter */}
      <div className="flex flex-col flex-1 min-h-0 rounded-xl border border-white/[0.07] overflow-hidden">
        <div className="flex items-center justify-between px-4 py-2.5 border-b border-white/[0.06]"
             style={{ background: 'rgba(255,255,255,0.02)' }}>
          <span className="text-[10px] text-slate-500 font-mono">cover_letter.txt</span>
          <CopyButton text={record.cover_letter} />
        </div>
        <div className="flex-1 overflow-y-auto p-5">
          <pre className="text-[12px] text-slate-300 leading-relaxed whitespace-pre-wrap font-sans">
            {record.cover_letter}
          </pre>
        </div>
      </div>

      {/* Key selling points */}
      {record.key_points.length > 0 && (
        <Section title="Key Selling Points" icon={<Sparkles size={13} />} color="#0EA5E9">
          <ul className="space-y-2">
            {record.key_points.map((pt, i) => (
              <li key={i} className="flex gap-2.5 text-[11px] text-slate-400 leading-relaxed">
                <span className="text-sky-500 flex-shrink-0 mt-0.5 font-bold">{i + 1}.</span>
                {pt}
              </li>
            ))}
          </ul>
        </Section>
      )}
    </div>
  )
}

// ── Main screen ────────────────────────────────────────────────────────────────

interface Props { threadId: string | null }

export default function CoverLetter({ threadId }: Props) {
  const [history, setHistory]     = useState<CoverLetter[]>([])
  const [selected, setSelected]   = useState<CoverLetter | null>(null)
  const [hasResume, setHasResume] = useState(false)

  // Form
  const [company, setCompany]   = useState('')
  const [jobTitle, setJobTitle] = useState('')
  const [jd, setJd]             = useState('')
  const [tone, setTone]         = useState<Tone>('professional')

  // Run state
  const [running, setRunning] = useState(false)
  const [logs, setLogs]       = useState<LogEntry[]>([])
  const [error, setError]     = useState<string | null>(null)
  const sseRef = useRef<(() => void) | null>(null)

  useEffect(() => {
    if (!threadId) return
    api.sessions.get(threadId).then(session => {
      const s = session as any
      if (s.cover_letters?.length) {
        setHistory(s.cover_letters)
        setSelected(s.cover_letters[0])
      }
      setHasResume(!!s.resume_text)
    }).catch(() => {})
  }, [threadId])

  function addLog(raw: string) {
    setLogs(prev => [...prev, parseLogLine(raw, ++_logId)])
  }

  async function handleGenerate() {
    if (!threadId || !company.trim() || !jobTitle.trim() || running) return
    sseRef.current?.()
    setLogs([])
    setError(null)
    setRunning(true)
    addLog(`[SYSTEM] Generating ${tone} cover letter for ${company}…`)

    try {
      const { job_id, thread_id } = await api.coverLetter.run(threadId, company, jobTitle, jd, tone)
      addLog(`[SYSTEM] Job ${job_id.slice(0, 8)}… started`)

      const cleanup = createSSE(
        thread_id,
        msg => addLog(msg),
        async signal => {
          if (signal === 'done') {
            addLog('[SYSTEM] ✓ Cover letter ready')
            setRunning(false)
            try {
              const resp = await fetch(`/api/sessions/${thread_id}`)
              if (resp.ok) {
                const data = await resp.json()
                if (data?.cover_letters?.length) {
                  setHistory(data.cover_letters)
                  setSelected(data.cover_letters[0])
                }
              }
            } catch { /* ignore */ }
          } else if (signal === 'error') {
            setError('Generation failed — check logs')
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
  const canRun    = !noSession && company.trim().length > 0 && jobTitle.trim().length > 0 && !running

  return (
    <div className="flex flex-col h-full overflow-hidden">

      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div className="flex-shrink-0 px-6 pt-5 pb-4 border-b border-white/[0.06]">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl" style={{ background: 'rgba(14,165,233,0.1)', border: '1px solid rgba(14,165,233,0.2)' }}>
            <PenLine size={18} style={{ color: '#0EA5E9' }} />
          </div>
          <div>
            <h1 className="text-sm font-bold text-slate-100">Cover Letter Generator</h1>
            <p className="text-[10px] text-slate-500 mt-0.5">
              Tailored, JD-matched cover letter — three tones, hook-led opening, specific achievements
            </p>
          </div>
        </div>
      </div>

      {/* ── Two-column body ─────────────────────────────────────────────────── */}
      <div className="flex flex-1 min-h-0 overflow-hidden">

        {/* LEFT — input + history ──────────────────────────────────────────── */}
        <div className="w-80 flex-shrink-0 flex flex-col border-r border-white/[0.06] overflow-hidden">
          <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">

            {noSession && (
              <div className="px-3 py-2.5 rounded-xl border border-amber-500/20 bg-amber-500/5 text-[11px] text-amber-400">
                Select a session to get started.
              </div>
            )}
            {!hasResume && !noSession && (
              <div className="px-3 py-2.5 rounded-xl border border-orange-500/20 bg-orange-500/5 text-[11px] text-orange-400">
                No resume uploaded. Run <strong>Resume Review</strong> first.
              </div>
            )}

            {/* Form */}
            <div className="space-y-3">
              <div>
                <label className="block text-[9px] font-bold text-slate-600 uppercase tracking-wider mb-1.5">
                  Company <span className="text-sky-500">*</span>
                </label>
                <input
                  value={company}
                  onChange={e => setCompany(e.target.value)}
                  placeholder="e.g. Stripe"
                  className="w-full px-3 py-2 rounded-xl text-xs text-slate-200 outline-none transition-all placeholder-slate-700"
                  style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.1)' }}
                  onFocus={e => (e.target.style.borderColor = 'rgba(14,165,233,0.45)')}
                  onBlur={e => (e.target.style.borderColor = 'rgba(255,255,255,0.1)')}
                />
              </div>

              <div>
                <label className="block text-[9px] font-bold text-slate-600 uppercase tracking-wider mb-1.5">
                  Job Title <span className="text-sky-500">*</span>
                </label>
                <input
                  value={jobTitle}
                  onChange={e => setJobTitle(e.target.value)}
                  placeholder="e.g. Backend Engineer"
                  className="w-full px-3 py-2 rounded-xl text-xs text-slate-200 outline-none transition-all placeholder-slate-700"
                  style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.1)' }}
                  onFocus={e => (e.target.style.borderColor = 'rgba(14,165,233,0.45)')}
                  onBlur={e => (e.target.style.borderColor = 'rgba(255,255,255,0.1)')}
                />
              </div>

              <div>
                <label className="block text-[9px] font-bold text-slate-600 uppercase tracking-wider mb-1.5">
                  Tone
                </label>
                <TonePicker value={tone} onChange={setTone} />
                <p className="text-[9px] text-slate-700 mt-1.5">{TONE_META[tone].desc}</p>
              </div>

              <div>
                <label className="block text-[9px] font-bold text-slate-600 uppercase tracking-wider mb-1.5">
                  Job Description <span className="text-slate-700">(optional — improves quality)</span>
                </label>
                <textarea
                  value={jd}
                  onChange={e => setJd(e.target.value)}
                  placeholder="Paste the JD here for a more targeted letter…"
                  rows={8}
                  className="w-full px-3 py-2 rounded-xl text-xs text-slate-200 outline-none resize-none transition-all placeholder-slate-700 leading-relaxed"
                  style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.1)' }}
                  onFocus={e => (e.target.style.borderColor = 'rgba(14,165,233,0.45)')}
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
                style={{ background: 'rgba(14,165,233,0.15)', border: '1px solid rgba(14,165,233,0.35)', color: '#0EA5E9' }}
              >
                {running
                  ? <><Loader2 size={13} className="animate-spin" />Generating…</>
                  : <><Briefcase size={13} />Generate Cover Letter</>}
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
                {running && (
                  <div className="flex items-center gap-1.5 text-slate-700 mt-1">
                    <Loader2 size={9} className="animate-spin" />Running…
                  </div>
                )}
              </div>
            )}

            {/* History */}
            {history.length > 0 && (
              <div>
                <div className="text-[9px] font-bold text-slate-700 uppercase tracking-wider mb-2">
                  History ({history.length})
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

        {/* RIGHT — letter output ───────────────────────────────────────────── */}
        <div className="flex-1 min-w-0 overflow-hidden px-5 py-4">
          {selected ? (
            <ResultPanel record={selected} />
          ) : (
            <div className="h-full flex flex-col items-center justify-center gap-4 text-center">
              <div className="p-5 rounded-2xl"
                   style={{ background: 'rgba(14,165,233,0.06)', border: '1px solid rgba(14,165,233,0.12)' }}>
                <PenLine size={32} style={{ color: 'rgba(14,165,233,0.4)' }} />
              </div>
              <div>
                <p className="text-sm font-semibold text-slate-500">No cover letter yet</p>
                <p className="text-[11px] text-slate-700 mt-1">
                  Fill in company + role on the left and hit <strong className="text-slate-500">Generate</strong>
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
