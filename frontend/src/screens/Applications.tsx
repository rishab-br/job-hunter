import { useEffect, useState } from 'react'
import { FileText, Play, ExternalLink, ShieldCheck, Bell } from 'lucide-react'
import { Pill, Topbar, Button, EmptyState } from '../components/ui'
import { api } from '../api'
import type { Application, ModuleState, PendingApproval } from '../types'

interface ApplicationsProps {
  threadId: string | null
  moduleState: ModuleState
  onRunModule: (key: string) => void
  onSeedTestJob: () => void
  activeJobId: string | null
}

const STATUS_CONFIG: Record<string, { label: string; variant: 'emerald' | 'cyan' | 'amber' | 'red' | 'violet' | 'muted' }> = {
  submitted:            { label: 'Submitted',          variant: 'emerald' },
  applied:              { label: 'Applied',            variant: 'muted'   },
  viewed:               { label: 'Viewed',             variant: 'cyan'    },
  shortlisted:          { label: 'Shortlisted',        variant: 'amber'   },
  interview_scheduled:  { label: 'Interview ✓',        variant: 'emerald' },
  offer:                { label: 'Offer! 🎉',          variant: 'violet'  },
  rejected:             { label: 'Rejected',           variant: 'red'     },
  unknown:              { label: 'Applied',            variant: 'muted'   },
}

export default function Applications({ threadId, moduleState, onRunModule, onSeedTestJob, activeJobId }: ApplicationsProps) {
  const [apps,    setApps]    = useState<Application[]>([])
  const [pending, setPending] = useState<PendingApproval | null>(null)

  useEffect(() => {
    if (!threadId) return
    api.sessions.applications(threadId).then(d => setApps(d.applications ?? [])).catch(() => {})
    api.sessions.pending(threadId).then(p => setPending(p.awaiting ? p : null)).catch(() => {})
  }, [threadId, moduleState.status])

  // Group by status for mini summary
  const summary = apps.reduce<Record<string, number>>((acc, a) => {
    acc[a.status] = (acc[a.status] ?? 0) + 1
    return acc
  }, {})

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      <Topbar breadcrumb="Applications">
        <Button size="sm" onClick={onSeedTestJob} disabled={!!activeJobId}>
          <ShieldCheck size={11} />
          Demo Approval Gate
        </Button>
        <Button variant="primary" size="sm" onClick={() => onRunModule('application')} disabled={!!activeJobId || moduleState.status === 'running'}>
          <Play size={10} />
          {moduleState.status === 'running' ? 'Applying…' : 'Apply to Queued'}
        </Button>
      </Topbar>

      <div className="flex-1 overflow-y-auto px-6 py-5 space-y-4">

        {/* Approval gate banner — shown when pipeline is paused awaiting a decision */}
        {pending?.awaiting && (
          <div
            className="flex items-center gap-3 px-4 py-3 rounded-xl border animate-fade-in"
            style={{ background: 'rgba(0,212,255,0.06)', borderColor: 'rgba(0,212,255,0.25)' }}
          >
            <Bell size={15} className="text-cyan-400 flex-shrink-0 animate-dot-pulse" />
            <div className="flex-1 min-w-0">
              <span className="text-sm font-semibold text-cyan-300">Pipeline paused — awaiting your approval</span>
              {pending.job && (
                <span className="text-xs text-slate-500 ml-2">
                  {pending.job.job_title} at {pending.job.company}
                </span>
              )}
            </div>
            <span className="text-[10px] font-mono text-cyan-600 bg-cyan-500/10 px-2 py-1 rounded-lg border border-cyan-500/20">
              LangGraph interrupt()
            </span>
          </div>
        )}

        {/* Status summary pills */}
        {apps.length > 0 && (
          <div className="flex items-center gap-2 flex-wrap">
            {Object.entries(summary).map(([status, count]) => {
              const cfg = STATUS_CONFIG[status] ?? { label: status, variant: 'muted' as const }
              return (
                <Pill key={status} variant={cfg.variant}>
                  {cfg.label}: {count}
                </Pill>
              )
            })}
          </div>
        )}

        {apps.length === 0 ? (
          <EmptyState icon={<FileText size={36} />} message="No applications yet — run the Application Engine" />
        ) : (
          <div className="border border-white/[0.06] rounded-xl overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="border-b border-white/[0.05] bg-[#0D1117]">
                  {['Company', 'Role', 'Platform', 'Status', 'Submitted', ''].map((h, i) => (
                    <th key={i} className="px-4 py-3 text-left text-[9px] font-semibold text-slate-600 uppercase tracking-wider">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.03]">
                {apps.map(a => {
                  const cfg = STATUS_CONFIG[a.status] ?? { label: a.status, variant: 'muted' as const }
                  return (
                    <tr key={a.job_id} className="hover:bg-white/[0.02] transition-colors">
                      <td className="px-4 py-3 text-sm font-semibold text-slate-200">{a.company ?? '—'}</td>
                      <td className="px-4 py-3 text-xs text-slate-400">{a.job_title ?? '—'}</td>
                      <td className="px-4 py-3"><Pill variant="muted">{a.platform ?? '—'}</Pill></td>
                      <td className="px-4 py-3">
                        <Pill variant={cfg.variant}>{cfg.label}</Pill>
                      </td>
                      <td className="px-4 py-3 text-[10px] text-slate-600 font-mono">
                        {a.submitted_at?.slice(0, 10) ?? '—'}
                      </td>
                      <td className="px-4 py-3">
                        {a.url && (
                          <a href={a.url} target="_blank" rel="noopener noreferrer"
                             className="inline-flex items-center gap-1 text-[10px] text-slate-500 hover:text-cyan-400 transition-colors">
                            <ExternalLink size={11} />
                            View
                          </a>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
