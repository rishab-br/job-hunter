import { useState, useEffect } from 'react'
import {
  ShieldCheck, FileText, Mail, Image as ImageIcon, ExternalLink,
  Check, X, Loader2, AlertTriangle, MapPin, Pencil, Save, RotateCcw,
} from 'lucide-react'
import { api } from '../api'
import type { PendingApproval } from '../types'

interface ApprovalModalProps {
  pending: PendingApproval
  onDecision: (approved: boolean) => void
  submitting: boolean
}

type Tab = 'resume' | 'cover' | 'form'

const PLATFORM_COLOR: Record<string, string> = {
  LinkedIn: '#00D4FF', Indeed: '#F59E0B', Naukri: '#EF4444',
  Greenhouse: '#10B981', Lever: '#8B5CF6',
}

export default function ApprovalModal({ pending, onDecision, submitting }: ApprovalModalProps) {
  const job = pending.job
  const [tab, setTab]               = useState<Tab>('resume')
  const [resumeText, setResumeText] = useState<string>('')
  const [coverText, setCoverText]   = useState<string>('')
  const [loadingDoc, setLoadingDoc] = useState(false)

  // Edit state
  const [editing,   setEditing]   = useState(false)
  const [draft,     setDraft]     = useState('')
  const [saving,    setSaving]    = useState(false)
  const [editedDocs, setEditedDocs] = useState<Set<string>>(new Set())

  // Reset everything when a new application surfaces
  useEffect(() => {
    setTab('resume')
    setEditing(false)
    setEditedDocs(new Set())
  }, [job?.job_id])

  // Leaving a tab cancels an in-progress edit
  useEffect(() => { setEditing(false) }, [tab])

  // Fetch resume markdown
  useEffect(() => {
    if (!job?.resume_path) { setResumeText(''); return }
    setLoadingDoc(true)
    api.files.text(job.resume_path)
      .then(t => setResumeText(t || '_Resume file could not be loaded._'))
      .catch(() => setResumeText('_Resume file could not be loaded._'))
      .finally(() => setLoadingDoc(false))
  }, [job?.resume_path])

  // Cover letter — prefer inline content, fall back to file
  useEffect(() => {
    if (!job) return
    if (job.cover_letter_content) { setCoverText(job.cover_letter_content); return }
    if (job.cover_letter_path) {
      api.files.text(job.cover_letter_path)
        .then(t => setCoverText(t || '_Cover letter could not be loaded._'))
        .catch(() => setCoverText('_Cover letter could not be loaded._'))
    }
  }, [job?.job_id])

  if (!job) return null

  const accent = PLATFORM_COLOR[job.platform] ?? '#00D4FF'
  const filledFields = Object.entries(job.filled_fields ?? {}).filter(([k]) => k !== 'note')

  // Current document context for the active tab
  const docCtx = tab === 'resume'
    ? { text: resumeText, path: job.resume_path, set: setResumeText, key: 'resume' }
    : tab === 'cover'
    ? { text: coverText, path: job.cover_letter_path, set: setCoverText, key: 'cover' }
    : null

  function startEdit() {
    if (!docCtx) return
    setDraft(docCtx.text)
    setEditing(true)
  }

  async function saveEdit() {
    if (!docCtx?.path) return
    setSaving(true)
    try {
      await api.files.save(docCtx.path, draft)
      docCtx.set(draft)
      setEditedDocs(prev => new Set(prev).add(docCtx.key))
      setEditing(false)
    } catch {
      /* keep editing so the user doesn't lose their text */
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md modal-backdrop p-6">
      <div className="modal-content w-full max-w-5xl max-h-[90vh] flex flex-col rounded-2xl overflow-hidden"
           style={{ background: 'linear-gradient(160deg, #0D1117, #080B14)', border: '1px solid rgba(255,255,255,0.1)', boxShadow: '0 0 60px rgba(0,212,255,0.12)' }}>

        {/* ── Header ── */}
        <div className="relative px-6 py-5 border-b border-white/[0.07] flex-shrink-0 overflow-hidden">
          <div className="absolute -top-10 -left-10 w-48 h-48 rounded-full blur-3xl pointer-events-none"
               style={{ background: 'rgba(0,212,255,0.1)' }} />
          <div className="relative flex items-center justify-between">
            <div className="flex items-center gap-3.5">
              <div className="w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0 animate-glow-cyan"
                   style={{ background: 'linear-gradient(135deg, #00D4FF, #0066ff)' }}>
                <ShieldCheck size={20} className="text-slate-900" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-base font-bold text-slate-100">Human Approval Gate</h2>
                  <span className="text-[9px] font-mono px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/25">
                    LangGraph interrupt()
                  </span>
                </div>
                <p className="text-xs text-slate-500 mt-0.5">
                  Review &amp; revise everything before this application is submitted. Nothing is sent without your approval.
                </p>
              </div>
            </div>
            {typeof pending.remaining === 'number' && pending.remaining > 1 && (
              <span className="text-[10px] font-semibold px-3 py-1.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/25">
                {pending.remaining} in queue
              </span>
            )}
          </div>
        </div>

        {/* ── Job summary bar ── */}
        <div className="px-6 py-3.5 border-b border-white/[0.05] flex-shrink-0 flex items-center justify-between"
             style={{ background: 'rgba(255,255,255,0.015)' }}>
          <div>
            <div className="text-sm font-bold text-slate-100">{job.job_title}</div>
            <div className="flex items-center gap-3 mt-1 text-xs text-slate-500">
              <span className="font-medium text-slate-400">{job.company}</span>
              <span className="flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full" style={{ background: accent }} />
                {job.platform}
              </span>
            </div>
          </div>
          {job.job_url && (
            <a href={job.job_url} target="_blank" rel="noopener noreferrer"
               className="flex items-center gap-1.5 text-[10px] text-slate-500 hover:text-cyan-400 transition-colors">
              <ExternalLink size={11} /> View posting
            </a>
          )}
        </div>

        {/* ── Tabs ── */}
        <div className="flex items-center gap-1 px-6 pt-3 flex-shrink-0">
          {([
            { id: 'resume', label: 'Tailored Resume', icon: <FileText size={13} /> },
            { id: 'cover',  label: 'Cover Letter',    icon: <Mail size={13} /> },
            { id: 'form',   label: 'Form Preview',    icon: <ImageIcon size={13} /> },
          ] as { id: Tab; label: string; icon: React.ReactNode }[]).map(t => {
            const active = tab === t.id
            const wasEdited = editedDocs.has(t.id)
            return (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className="flex items-center gap-1.5 px-3.5 py-2 rounded-t-lg text-xs font-medium transition-all"
                style={active
                  ? { background: 'rgba(0,212,255,0.08)', color: '#00D4FF', borderBottom: '2px solid #00D4FF' }
                  : { color: '#64748b', borderBottom: '2px solid transparent' }}
              >
                {t.icon}{t.label}
                {wasEdited && <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" title="Edited" />}
              </button>
            )
          })}

          {/* Edit / Save controls (resume + cover only) */}
          {docCtx && (
            <div className="ml-auto flex items-center gap-2 pb-1">
              {!editing ? (
                <button
                  onClick={startEdit}
                  disabled={!docCtx.path}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-medium transition-all disabled:opacity-30 disabled:cursor-not-allowed"
                  style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.1)', color: '#94a3b8' }}
                >
                  <Pencil size={11} /> Edit
                </button>
              ) : (
                <>
                  <button
                    onClick={() => setEditing(false)}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-medium transition-all"
                    style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.1)', color: '#64748b' }}
                  >
                    <RotateCcw size={11} /> Cancel
                  </button>
                  <button
                    onClick={saveEdit}
                    disabled={saving}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-semibold transition-all"
                    style={{ background: 'rgba(0,212,255,0.12)', border: '1px solid rgba(0,212,255,0.35)', color: '#00D4FF' }}
                  >
                    {saving ? <Loader2 size={11} className="animate-spin" /> : <Save size={11} />} Save
                  </button>
                </>
              )}
            </div>
          )}
        </div>

        {/* ── Content ── */}
        <div className="flex-1 overflow-y-auto px-6 py-4 min-h-0">
          {(tab === 'resume' || tab === 'cover') && (
            editing ? (
              <textarea
                value={draft}
                onChange={e => setDraft(e.target.value)}
                spellCheck={false}
                className="w-full h-full min-h-[340px] rounded-xl border border-cyan-500/30 bg-[#0A0D14] p-5 text-sm text-slate-200 font-mono leading-relaxed outline-none focus:border-cyan-500/50 resize-none"
              />
            ) : (
              <DocView
                loading={tab === 'resume' && loadingDoc}
                text={docCtx?.text ?? ''}
                emptyHint={tab === 'resume' ? 'No resume generated yet.' : 'No cover letter generated yet.'}
              />
            )
          )}

          {tab === 'form' && (
            <div className="space-y-4">
              {job.form_screenshot_path ? (
                <div className="rounded-xl overflow-hidden border border-white/10">
                  <img src={api.files.url(job.form_screenshot_path)} alt="Form preview"
                       className="w-full" style={{ background: '#fff' }} />
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center h-40 gap-2 rounded-xl border border-dashed border-white/10 text-slate-600">
                  <AlertTriangle size={24} className="opacity-40" />
                  <p className="text-xs">No form screenshot captured (the form may have changed or required login).</p>
                </div>
              )}

              {filledFields.length > 0 && (
                <div>
                  <p className="text-[10px] font-semibold text-slate-600 uppercase tracking-widest mb-2">
                    Auto-filled fields
                  </p>
                  <div className="grid grid-cols-2 gap-2">
                    {filledFields.map(([k, v]) => (
                      <div key={k} className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/[0.03] border border-white/[0.06]">
                        <Check size={11} className="text-emerald-400 flex-shrink-0" />
                        <span className="text-[10px] text-slate-500 font-mono truncate">{k.replace(/.*\[|['\]]/g, '')}</span>
                        <span className="text-xs text-slate-300 ml-auto truncate">{v}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* ── Footer / Decision ── */}
        <div className="px-6 py-4 border-t border-white/[0.07] flex-shrink-0 flex items-center justify-between"
             style={{ background: 'rgba(0,0,0,0.3)' }}>
          <div className="flex items-center gap-2 text-xs text-slate-600">
            {editedDocs.size > 0 ? (
              <>
                <Check size={12} className="text-emerald-400" />
                <span className="text-emerald-500/80">
                  {editedDocs.size} document{editedDocs.size > 1 ? 's' : ''} edited — your version will be submitted.
                </span>
              </>
            ) : (
              <>
                <MapPin size={12} />
                Pipeline is paused — your decision resumes it.
              </>
            )}
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => onDecision(false)}
              disabled={submitting || editing}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold transition-all disabled:opacity-40 disabled:cursor-not-allowed"
              style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)', color: '#f87171' }}
            >
              <X size={15} /> Skip
            </button>
            <button
              onClick={() => onDecision(true)}
              disabled={submitting || editing}
              className="flex items-center gap-2 px-6 py-2.5 rounded-xl text-sm font-bold transition-all disabled:opacity-60 disabled:cursor-not-allowed"
              style={{ background: 'linear-gradient(135deg, #10B981, #059669)', color: '#022c22', boxShadow: '0 0 20px rgba(16,185,129,0.3)' }}
              title={editing ? 'Save or cancel your edit first' : undefined}
            >
              {submitting ? <><Loader2 size={15} className="animate-spin" /> Submitting…</> : <><Check size={15} /> Approve &amp; Submit</>}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Document viewer (renders markdown-ish plaintext) ──────────────────────────

function DocView({ loading, text, emptyHint }: { loading: boolean; text: string; emptyHint: string }) {
  if (loading) {
    return (
      <div className="flex items-center justify-center h-48 gap-2 text-slate-600">
        <Loader2 size={18} className="animate-spin" />
        <span className="text-xs">Loading document…</span>
      </div>
    )
  }
  if (!text) {
    return (
      <div className="flex items-center justify-center h-48 text-slate-600">
        <p className="text-xs">{emptyHint}</p>
      </div>
    )
  }
  return (
    <div className="rounded-xl border border-white/[0.06] bg-[#0A0D14] p-5">
      <pre className="whitespace-pre-wrap font-sans text-sm text-slate-300 leading-relaxed">{text}</pre>
    </div>
  )
}
