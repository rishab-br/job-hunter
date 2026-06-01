import { useEffect, useState } from 'react'
import { DollarSign, Plus, RefreshCw } from 'lucide-react'
import { Card, Pill, Topbar, Button, EmptyState } from '../components/ui'
import { api } from '../api'
import type { OfferEvaluation, ModuleState } from '../types'

interface OffersProps {
  threadId: string | null
  moduleState: ModuleState
  onRunModule: (key: string) => void
  onOpenOfferModal: () => void
  activeJobId: string | null
}

const RISK_CONFIG = {
  high:   { variant: 'red'     as const, label: 'High Risk',   border: 'rgba(239,68,68,0.2)',   bg: 'rgba(239,68,68,0.06)'   },
  medium: { variant: 'amber'   as const, label: 'Med Risk',    border: 'rgba(245,158,11,0.2)',  bg: 'rgba(245,158,11,0.06)'  },
  low:    { variant: 'emerald' as const, label: 'Low Risk',    border: 'rgba(16,185,129,0.2)',  bg: 'rgba(16,185,129,0.06)'  },
}

const COACHING_ICONS: Record<string, string> = {
  accept: '✅', counter_again: '🔄', decline: '❌', request_time: '⏳',
}

export default function Offers({ threadId, moduleState, onRunModule, onOpenOfferModal, activeJobId }: OffersProps) {
  const [offers, setOffers] = useState<OfferEvaluation[]>([])

  useEffect(() => {
    if (!threadId) return
    api.sessions.offers(threadId).then(d => setOffers(d.offers ?? [])).catch(() => {})
  }, [threadId, moduleState.status])

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      <Topbar breadcrumb="Offer Intelligence">
        <Button size="sm" onClick={onOpenOfferModal}>
          <Plus size={11} />
          Inject Offer
        </Button>
        <Button variant="primary" size="sm" onClick={() => onRunModule('offer')} disabled={!!activeJobId || moduleState.status === 'running'}>
          <RefreshCw size={11} />
          {moduleState.status === 'running' ? 'Evaluating…' : 'Re-evaluate'}
        </Button>
      </Topbar>

      <div className="flex-1 overflow-y-auto px-6 py-5">
        {offers.length === 0 ? (
          <EmptyState
            icon={<DollarSign size={36} />}
            message="No offers yet — inject one to evaluate"
          />
        ) : (
          <div className="space-y-4">
            {offers.map(o => {
              const risk = RISK_CONFIG[o.risk_level ?? 'low']
              return (
                <div
                  key={o.offer_id}
                  className="rounded-xl border p-5"
                  style={{ borderColor: risk.border, background: `linear-gradient(135deg, ${risk.bg} 0%, #0D1117 40%)` }}
                >
                  {/* Header */}
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <h3 className="text-base font-bold text-slate-100">{o.company}</h3>
                      <p className="text-xs text-slate-500 mt-0.5">{o.job_title}</p>
                    </div>
                    <Pill variant={risk.variant}>{risk.label}</Pill>
                  </div>

                  {/* 3 metric boxes */}
                  <div className="grid grid-cols-3 gap-3 mb-4">
                    <Card className="p-3.5 text-center">
                      <div className="text-[9px] text-slate-600 uppercase tracking-wider mb-1.5">Offered CTC</div>
                      <div className="text-lg font-bold text-slate-200">{o.total_ctc ?? '—'}</div>
                      {o.fair_value_range && (
                        <div className="text-[9px] text-slate-600 mt-1">Range: {o.fair_value_range}</div>
                      )}
                    </Card>
                    <Card className="p-3.5 text-center" glow="cyan">
                      <div className="text-[9px] text-slate-600 uppercase tracking-wider mb-1.5">Counter Ask</div>
                      <div className="text-lg font-bold text-cyan-400">{o.counter_ask ?? '—'}</div>
                      {o.offer_percentile && (
                        <div className="text-[9px] text-slate-600 mt-1">{o.offer_percentile} percentile</div>
                      )}
                    </Card>
                    <Card className="p-3.5 text-center" glow="red">
                      <div className="text-[9px] text-slate-600 uppercase tracking-wider mb-1.5">Walk Away Floor</div>
                      <div className="text-lg font-bold text-red-400">{o.walk_away_floor ?? '—'}</div>
                    </Card>
                  </div>

                  {/* Coaching + script path */}
                  <div className="flex items-center justify-between text-xs">
                    {o.coaching_move && (
                      <div className="flex items-center gap-2 text-slate-400">
                        <span>Coaching:</span>
                        <span>{COACHING_ICONS[o.coaching_move]}</span>
                        <span className="text-slate-200 font-medium">
                          {o.coaching_move.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                        </span>
                      </div>
                    )}
                    {o.script_path && (
                      <span className="text-[10px] text-slate-600 font-mono truncate max-w-[240px]">
                        📄 {o.script_path}
                      </span>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
