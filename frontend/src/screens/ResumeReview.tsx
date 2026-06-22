import { useState, useRef, useCallback, useEffect } from 'react'
import {
  ClipboardCheck, Upload, CheckCircle2, XCircle, AlertTriangle,
  TrendingUp, Shield, Lightbulb, ChevronDown, ChevronUp, Loader2,
} from 'lucide-react'
import { api, createSSE, nowTs } from '../api'
import { parseLogLine } from '../components/LogPanel'
import type { ResumeReview, LogEntry } from '../types'

let _logId = 0

// ── Score dial ────────────────────────────────────────────────────────────────

function ScoreDial({ score, label }: { score: number; label: string }) {
  const pct = (score / 10) * 100
  const color = score >= 7.5 ? '#10B981' : score >= 5 ? '#F59E0B' : '#EF4444'
  const r = 44, cx = 56, cy = 56, stroke = 8
  const circumference = 2 * Math.PI * r
  const dash = (pct / 100) * circumference

  return (
    <div className="flex flex-col items-center gap-1">
      <svg width={112} height={112} viewBox="0 0 112 112">
        <circle cx={cx} cy={cy} r={r} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth={stroke} />
        <circle
          cx={cx} cy={cy} r={r} fill="none"
          stroke={color} strokeWidth={stroke}
          strokeDasharray={`${dash} ${circumference}`}
          strokeLinecap="round"
          transform={`rotate(-90 ${cx} ${cy})`}
          style={{ filter: `drop-shadow(0 0 6px ${color})`, transition: 'stroke-dasharray 0.8s ease' }}
        />
        <text x={cx} y={cy - 4} textAnchor="middle" fill={color} fontSize={20} fontWeight={800} fontFamily="inherit">
          {score.toFixed(1)}
        </text>
        <text x={cx} y={cy + 14} textAnchor="middle" fill="#64748b" fontSize={9} fontFamily="inherit">
          / 10
        </text>
      </svg>
      <span className="text-[10px] text-slate-500 uppercase tracking-wider">{label}</span>
    </div>
  )
}

// ── Fit badge ─────────────────────────────────────────────────────────────────

function FitBadge({ fit }: { fit: string }) {
  const map = {
    strong:   { label: 'Strong Fit',   bg: 'rgba(16,185,129,0.12)',  border: 'rgba(16,185,129,0.3)',  color: '#10B981' },
    moderate: { label: 'Moderate Fit', bg: 'rgba(245,158,11,0.12)', border: 'rgba(245,158,11,0.3)',  color: '#F59E0B' },
    weak:     { label: 'Weak Fit',     bg: 'rgba(239,68,68,0.12)',   border: 'rgba(239,68,68,0.3)',   color: '#EF4444' },
  } as const
  const c = map[fit as keyof typeof map] ?? map.moderate
  return (
    <span className="px-3 py-1 rounded-full text-xs font-bold" style={{ background: c.bg, border: `1px solid ${c.border}`, color: c.color }}>
      {c.label}
    </span>
  )
}

// ── Section card ──────────────────────────────────────────────────────────────

function Section({ title, icon, color, children, defaultOpen = true }: {
  title: string; icon: React.ReactNode; color: string; children: React.ReactNode; defaultOpen?: boolean
}) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="rounded-2xl border border-white/[0.07] overflow-hidden" style={{ background: 'rgba(255,255,255,0.015)' }}>
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-5 py-3.5 text-left"
        style={{ borderBottom: open ? '1px solid rgba(255,255,255,0.06)' : 'none' }}
      >
        <div className="flex items-center gap-2.5">
          <span style={{ color }}>{icon}</span>
          <span className="text-xs font-bold text-slate-300 uppercase tracking-[0.12em]">{title}</span>
        </div>
        <span className="text-slate-600">{open ? <ChevronUp size={14} /> : <ChevronDown size={14} />}</span>
      </button>
      {open && <div className="px-5 py-4">{children}</div>}
    </div>
  )
}

// ── Strength / weakness row ───────────────────────────────────────────────────

function ProConRow({ point, detail, variant }: { point: string; detail: string; variant: 'pro' | 'con' }) {
  const isPro = variant === 'pro'
  const color = isPro ? '#10B981' : '#F87171'
  const Icon  = isPro ? CheckCircle2 : XCircle
  return (
    <div className="flex gap-3 py-2.5 border-b border-white/[0.04] last:border-0">
      <Icon size={14} style={{ color, flexShrink: 0, marginTop: 2 }} />
      <div>
        <div className="text-xs font-semibold text-slate-200">{point}</div>
        <div className="text-[11px] text-slate-500 mt-0.5 leading-relaxed">{detail}</div>
      </div>
    </div>
  )
}

// ── Missing skill row ─────────────────────────────────────────────────────────

function SkillRow({ skill, importance, why }: { skill: string; importance: string; why: string }) {
  const imp = {
    critical:       { label: 'Critical',      color: '#EF4444', bg: 'rgba(239,68,68,0.1)',   border: 'rgba(239,68,68,0.25)' },
    important:      { label: 'Important',     color: '#F59E0B', bg: 'rgba(245,158,11,0.1)', border: 'rgba(245,158,11,0.25)' },
    'nice-to-have': { label: 'Nice to have',  color: '#60A5FA', bg: 'rgba(96,165,250,0.1)', border: 'rgba(96,165,250,0.25)' },
  } as const
  const c = imp[importance as keyof typeof imp] ?? imp['nice-to-have']
  return (
    <div className="flex gap-3 items-start py-2.5 border-b border-white/[0.04] last:border-0">
      <span className="mt-0.5 px-1.5 py-0.5 rounded text-[9px] font-bold flex-shrink-0"
            style={{ background: c.bg, border: `1px solid ${c.border}`, color: c.color }}>
        {c.label}
      </span>
      <div>
        <div className="text-xs font-semibold text-slate-200">{skill}</div>
        <div className="text-[11px] text-slate-500 mt-0.5 leading-relaxed">{why}</div>
      </div>
    </div>
  )
}

// ── Recommendation row ────────────────────────────────────────────────────────

function RecRow({ action, impact, idx }: { action: string; impact: string; idx: number }) {
  const impColor = impact === 'high' ? '#10B981' : impact === 'medium' ? '#F59E0B' : '#64748b'
  return (
    <div className="flex gap-3 items-start py-2.5 border-b border-white/[0.04] last:border-0">
      <span className="w-5 h-5 rounded-full flex items-center justify-center text-[9px] font-bold flex-shrink-0 mt-0.5"
            style={{ background: 'rgba(167,139,250,0.15)', border: '1px solid rgba(167,139,250,0.3)', color: '#A78BFA' }}>
        {idx}
      </span>
      <div className="flex-1">
        <div className="text-xs text-slate-200 leading-relaxed">{action}</div>
      </div>
      <span className="text-[9px] font-bold uppercase mt-0.5" style={{ color: impColor }}>{impact}</span>
    </div>
  )
}

// ── Drop zone ─────────────────────────────────────────────────────────────────

function DropZone({ onFile }: { onFile: (f: File) => void }) {
  const [drag, setDrag] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  function handleDrop(e: React.DragEvent) {
    e.preventDefault()
    setDrag(false)
    const f = e.dataTransfer.files[0]
    if (f) onFile(f)
  }

  return (
    <div
      onDragOver={e => { e.preventDefault(); setDrag(true) }}
      onDragLeave={() => setDrag(false)}
      onDrop={handleDrop}
      onClick={() => inputRef.current?.click()}
      className="cursor-pointer rounded-2xl border-2 border-dashed transition-all duration-200 flex flex-col items-center justify-center gap-3 py-12"
      style={{
        borderColor: drag ? '#34D399' : 'rgba(255,255,255,0.1)',
        background:  drag ? 'rgba(52,211,153,0.04)' : 'rgba(255,255,255,0.01)',
      }}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.txt,.md"
        className="hidden"
        onChange={e => { const f = e.target.files?.[0]; if (f) onFile(f) }}
      />
      <div className="p-4 rounded-2xl" style={{ background: 'rgba(52,211,153,0.08)', border: '1px solid rgba(52,211,153,0.2)' }}>
        <Upload size={24} style={{ color: '#34D399' }} />
      </div>
      <div className="text-center">
        <p className="text-sm font-semibold text-slate-300">Drop your resume here</p>
        <p className="text-[11px] text-slate-600 mt-1">PDF, TXT, or MD · click to browse</p>
      </div>
    </div>
  )
}

// ── Main screen ───────────────────────────────────────────────────────────────

interface Props { threadId: string | null }

export default function ResumeReview({ threadId }: Props) {
  const [file, setFile]       = useState<File | null>(null)
  const [running, setRunning] = useState(false)
  const [review, setReview]   = useState<ResumeReview | null>(null)
  const [logs, setLogs]       = useState<LogEntry[]>([])
  const [error, setError]     = useState<string | null>(null)
  const sseRef = useRef<(() => void) | null>(null)

  // Load existing review from session state if available
  useEffect(() => {
    if (!threadId) return
    api.sessions.get(threadId).then(session => {
      if ((session as any).resume_review) setReview((session as any).resume_review)
    }).catch(() => {})
  }, [threadId])

  function addLog(raw: string) {
    setLogs(prev => [...prev, parseLogLine(raw, ++_logId)])
  }

  const handleFile = useCallback((f: File) => {
    setFile(f)
    setError(null)
  }, [])

  async function handleAnalyze() {
    if (!file || !threadId || running) return
    sseRef.current?.()
    setLogs([])
    setReview(null)
    setError(null)
    setRunning(true)
    addLog(`[SYSTEM] Uploading ${file.name}…`)

    try {
      const { thread_id, job_id } = await api.resumeReview.run(threadId, file)
      addLog(`[SYSTEM] Job ${job_id.slice(0, 8)}… started — streaming analysis…`)

      const cleanup = createSSE(
        thread_id,
        msg => addLog(msg),
        async signal => {
          if (signal === 'done') {
            addLog('[SYSTEM] ✓ Review complete')
            setRunning(false)
            // Fetch updated session to get resume_review
            try {
              const resp = await fetch(`/api/sessions/${thread_id}`)
              if (resp.ok) {
                const data = await resp.json()
                if (data?.resume_review) setReview(data.resume_review)
              }
            } catch { /* ignore */ }
          } else if (signal === 'error') {
            setError('Analysis failed — check logs above')
            setRunning(false)
          }
        },
      )
      sseRef.current = cleanup
    } catch (e: any) {
      setError(e?.message ?? 'Upload failed')
      setRunning(false)
    }
  }

  const noSession = !threadId

  return (
    <div className="flex flex-col h-full overflow-hidden">

      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div className="flex-shrink-0 px-6 pt-5 pb-4 border-b border-white/[0.06]">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl" style={{ background: 'rgba(52,211,153,0.1)', border: '1px solid rgba(52,211,153,0.2)' }}>
              <ClipboardCheck size={18} style={{ color: '#34D399' }} />
            </div>
            <div>
              <h1 className="text-sm font-bold text-slate-100">Resume Review</h1>
              <p className="text-[10px] text-slate-500 mt-0.5">
                LLM-powered analysis benchmarked against your target role and market trends
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* ── Body ───────────────────────────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5">

        {noSession && (
          <div className="rounded-2xl border border-amber-500/20 bg-amber-500/5 px-5 py-4 text-xs text-amber-400">
            Create or select a session first — the reviewer uses your target role and niche for context.
          </div>
        )}

        {/* ── Upload + analyse ─────────────────────────────────────────────── */}
        {!review && (
          <div className="space-y-4">
            <DropZone onFile={handleFile} />

            {file && (
              <div className="flex items-center justify-between px-4 py-3 rounded-xl border border-white/[0.08] bg-white/[0.02]">
                <div className="flex items-center gap-2.5">
                  <div className="p-1.5 rounded-lg" style={{ background: 'rgba(52,211,153,0.1)' }}>
                    <ClipboardCheck size={13} style={{ color: '#34D399' }} />
                  </div>
                  <div>
                    <div className="text-xs font-semibold text-slate-200">{file.name}</div>
                    <div className="text-[10px] text-slate-600">{(file.size / 1024).toFixed(1)} KB</div>
                  </div>
                </div>
                <button
                  onClick={handleAnalyze}
                  disabled={noSession || running}
                  className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-bold transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                  style={{ background: 'rgba(52,211,153,0.15)', border: '1px solid rgba(52,211,153,0.35)', color: '#34D399' }}
                >
                  {running ? <Loader2 size={12} className="animate-spin" /> : <ClipboardCheck size={12} />}
                  {running ? 'Analysing…' : 'Analyse Resume'}
                </button>
              </div>
            )}

            {error && (
              <div className="px-4 py-3 rounded-xl border border-red-500/20 bg-red-500/5 text-xs text-red-400">{error}</div>
            )}

            {/* Live log during analysis */}
            {logs.length > 0 && (
              <div className="rounded-xl border border-white/[0.07] bg-black/20 p-4 max-h-48 overflow-y-auto font-mono text-[10px] space-y-0.5">
                {logs.map(l => (
                  <div key={l.id} className="flex gap-2 leading-5">
                    <span className="text-slate-700 flex-shrink-0">{l.ts}</span>
                    <span className={l.tagClass + ' flex-shrink-0'}>[{l.tag}]</span>
                    <span className={l.msgClass}>{l.msg}</span>
                  </div>
                ))}
                {running && <div className="flex items-center gap-2 text-slate-600 mt-1"><Loader2 size={10} className="animate-spin" />Running…</div>}
              </div>
            )}
          </div>
        )}

        {/* ── Report ──────────────────────────────────────────────────────── */}
        {review && (
          <div className="space-y-4">

            {/* Re-upload link */}
            <button
              onClick={() => { setReview(null); setFile(null); setLogs([]) }}
              className="text-[10px] text-slate-600 hover:text-slate-400 transition-colors underline"
            >
              ↩ Upload a different resume
            </button>

            {/* Score overview */}
            <div className="rounded-2xl border border-white/[0.08] bg-white/[0.02] p-5">
              <div className="flex items-center gap-6">
                <ScoreDial score={review.overall_score} label="Resume Score" />
                <ScoreDial score={review.ats_score} label="ATS Score" />
                <div className="flex-1 space-y-3">
                  <div className="flex items-center gap-2.5">
                    <FitBadge fit={review.role_fit} />
                    <span className="px-2.5 py-1 rounded-full text-xs font-semibold capitalize"
                          style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', color: '#94a3b8' }}>
                      {review.format_quality} format
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 leading-relaxed">{review.score_rationale}</p>
                </div>
              </div>
            </div>

            {/* Strengths */}
            <Section title="Strengths" icon={<CheckCircle2 size={15} />} color="#10B981">
              {review.strengths.map((s, i) => <ProConRow key={i} {...s} variant="pro" />)}
            </Section>

            {/* Weaknesses */}
            <Section title="Weaknesses" icon={<XCircle size={15} />} color="#F87171">
              {review.weaknesses.map((w, i) => <ProConRow key={i} {...w} variant="con" />)}
            </Section>

            {/* Missing skills */}
            <Section title="Missing Skills & Keywords" icon={<AlertTriangle size={15} />} color="#F59E0B">
              {review.missing_skills.map((s, i) => <SkillRow key={i} {...s} />)}
            </Section>

            {/* ATS concerns */}
            {review.ats_concerns.length > 0 && (
              <Section title="ATS Concerns" icon={<Shield size={15} />} color="#60A5FA" defaultOpen={false}>
                <ul className="space-y-2">
                  {review.ats_concerns.map((c, i) => (
                    <li key={i} className="flex gap-2 text-xs text-slate-400 leading-relaxed">
                      <span className="text-blue-400 flex-shrink-0 mt-0.5">•</span>
                      {c}
                    </li>
                  ))}
                </ul>
              </Section>
            )}

            {/* Market alignment */}
            <Section title="Market Alignment" icon={<TrendingUp size={15} />} color="#A78BFA" defaultOpen={false}>
              <p className="text-xs text-slate-400 leading-relaxed">{review.market_alignment}</p>
            </Section>

            {/* Recommendations */}
            <Section title="Recommendations" icon={<Lightbulb size={15} />} color="#FBBF24">
              {review.recommendations.map((r, i) => <RecRow key={i} {...r} idx={i + 1} />)}
            </Section>

          </div>
        )}
      </div>
    </div>
  )
}
