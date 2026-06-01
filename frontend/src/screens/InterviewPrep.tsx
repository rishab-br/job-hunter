import { useEffect, useState } from 'react'
import { MessageSquare, Plus, Download } from 'lucide-react'
import { Card, Pill, Topbar, Button, EmptyState, SectionTitle } from '../components/ui'
import { api } from '../api'
import type { PrepSession, ModuleState } from '../types'

interface InterviewPrepProps {
  threadId: string | null
  moduleState: ModuleState
  onOpenPrepModal: () => void
  activeJobId: string | null
}

const Q_TYPES = [
  { key: 'technical_count',         label: 'Technical',   variant: 'cyan'    as const },
  { key: 'behavioral_count',        label: 'Behavioral',  variant: 'violet'  as const },
  { key: 'system_design_count',     label: 'Sys Design',  variant: 'amber'   as const },
  { key: 'company_specific_count',  label: 'Company',     variant: 'muted'   as const },
]

function QuickCard({ session }: { session: PrepSession }) {
  return (
    <Card className="p-4 space-y-4">
      <div className="flex items-start justify-between">
        <div>
          <div className="text-base font-bold text-slate-100">{session.company}</div>
          <div className="text-xs text-slate-500 mt-0.5">{session.role}</div>
        </div>
        <Pill variant="emerald">{session.prep_date}</Pill>
      </div>

      <div className="border-t border-white/[0.05] pt-4">
        <SectionTitle>Question Bank</SectionTitle>
        <div className="flex flex-wrap gap-1.5">
          <Pill variant="muted">Total: {session.question_count ?? '—'}</Pill>
          {Q_TYPES.map(q => (
            <Pill key={q.key} variant={q.variant}>
              {q.label}: {String((session as unknown as Record<string,unknown>)[q.key] ?? '—')}
            </Pill>
          ))}
        </div>
      </div>

      {session.cheat_sheet_path && (
        <div className="border-t border-white/[0.05] pt-4">
          <SectionTitle>Output Files</SectionTitle>
          <div className="space-y-1.5">
            {session.cheat_sheet_path && (
              <div className="text-[10px] font-mono text-cyan-500/80 truncate">
                📄 {session.cheat_sheet_path}
              </div>
            )}
            {session.quick_card_path && (
              <div className="text-[10px] font-mono text-cyan-500/80 truncate">
                📄 {session.quick_card_path}
              </div>
            )}
          </div>
        </div>
      )}

      <div className="flex gap-2 pt-1">
        <Button size="sm" className="flex-1 justify-center" disabled={!session.cheat_sheet_path}>
          <Download size={10} /> Cheat Sheet
        </Button>
        <Button size="sm" className="flex-1 justify-center" disabled={!session.quick_card_path}>
          <Download size={10} /> Quick Card
        </Button>
      </div>
    </Card>
  )
}

export default function InterviewPrep({ threadId, moduleState, onOpenPrepModal, activeJobId }: InterviewPrepProps) {
  const [sessions, setSessions] = useState<PrepSession[]>([])
  const [selected, setSelected] = useState<PrepSession | null>(null)

  useEffect(() => {
    if (!threadId) return
    api.sessions.prep(threadId).then(d => {
      const list = d.sessions ?? []
      setSessions(list)
      if (list.length > 0) setSelected(list[0])
    }).catch(() => {})
  }, [threadId, moduleState.status])

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      <Topbar breadcrumb="Interview Prep">
        <Button size="sm">
          <Download size={11} />
          Export All
        </Button>
        <Button variant="primary" size="sm" onClick={onOpenPrepModal} disabled={!!activeJobId}>
          <Plus size={11} />
          New Prep
        </Button>
      </Topbar>

      <div className="flex-1 overflow-hidden px-6 py-5">
        {sessions.length === 0 ? (
          <EmptyState
            icon={<MessageSquare size={36} />}
            message="No prep sessions yet — click '+ New Prep'"
          />
        ) : (
          <div className="grid grid-cols-[1fr_320px] gap-4 h-full min-h-0">

            {/* Session list */}
            <div className="overflow-y-auto pr-1 space-y-2">
              <SectionTitle>Prep Sessions ({sessions.length})</SectionTitle>
              {sessions.map((s, i) => (
                <div
                  key={s.session_id}
                  onClick={() => setSelected(s)}
                  className={`
                    p-4 rounded-xl border cursor-pointer transition-all
                    ${selected?.session_id === s.session_id
                      ? 'border-cyan-500/30 bg-cyan-500/5 shadow-[0_0_16px_rgba(0,212,255,0.06)]'
                      : 'border-white/[0.06] bg-[#0D1117] hover:border-white/10'
                    }
                  `}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-semibold text-slate-200">{s.company}</span>
                    <Pill variant={i === 0 ? 'emerald' : 'muted'}>{s.prep_date}</Pill>
                  </div>
                  <div className="text-xs text-slate-500 mb-2.5">{s.role}</div>
                  <div className="flex items-center gap-2">
                    <Pill variant="cyan">Questions: {s.question_count ?? '—'}</Pill>
                    {s.cheat_sheet_path && <Pill variant="emerald">Sheet ✓</Pill>}
                  </div>
                </div>
              ))}
            </div>

            {/* Quick card */}
            <div className="overflow-y-auto">
              <SectionTitle>Quick Card Preview</SectionTitle>
              {selected ? (
                <QuickCard session={selected} />
              ) : (
                <EmptyState icon={<MessageSquare size={28} />} message="Select a session" />
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
