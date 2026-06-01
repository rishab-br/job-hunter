import { useState } from 'react'
import { X, DollarSign } from 'lucide-react'
import { Card, Input, Textarea, Button, ModalOverlay } from '../components/ui'

interface OfferModalProps {
  onClose: () => void
  onSubmit: (data: {
    company: string
    job_title: string
    offer_letter_text: string
    deadline_date: string | null
  }) => Promise<void>
}

export default function OfferModal({ onClose, onSubmit }: OfferModalProps) {
  const [company,  setCompany]  = useState('')
  const [title,    setTitle]    = useState('')
  const [text,     setText]     = useState('')
  const [deadline, setDeadline] = useState('')
  const [loading,  setLoading]  = useState(false)

  async function handleSubmit() {
    if (!company || !text) return
    setLoading(true)
    try {
      await onSubmit({
        company,
        job_title: title,
        offer_letter_text: text,
        deadline_date: deadline || null,
      })
      onClose()
    } finally {
      setLoading(false)
    }
  }

  return (
    <ModalOverlay onClose={onClose}>
      <Card className="w-[480px] max-w-[95vw] p-6">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-amber-500/10 border border-amber-500/25 flex items-center justify-center">
              <DollarSign size={13} className="text-amber-400" />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-slate-200">Inject Offer</h2>
              <p className="text-xs text-slate-600 mt-0.5">Evaluate CTC, risk, and negotiate</p>
            </div>
          </div>
          <button onClick={onClose} className="text-slate-600 hover:text-slate-400 transition-colors p-1">
            <X size={14} />
          </button>
        </div>

        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-[10px] font-semibold text-slate-600 uppercase tracking-wider mb-1.5">
                Company <span className="text-red-500">*</span>
              </label>
              <Input placeholder="Stripe" value={company} onChange={e => setCompany(e.target.value)} />
            </div>
            <div>
              <label className="block text-[10px] font-semibold text-slate-600 uppercase tracking-wider mb-1.5">
                Job Title
              </label>
              <Input placeholder="Staff Engineer" value={title} onChange={e => setTitle(e.target.value)} />
            </div>
          </div>

          <div>
            <label className="block text-[10px] font-semibold text-slate-600 uppercase tracking-wider mb-1.5">
              Offer Letter Text <span className="text-red-500">*</span>
            </label>
            <Textarea
              placeholder="Paste the full offer letter or key details (CTC, components, clauses)…"
              value={text}
              onChange={e => setText(e.target.value)}
              className="h-28"
            />
          </div>

          <div>
            <label className="block text-[10px] font-semibold text-slate-600 uppercase tracking-wider mb-1.5">
              Decision Deadline (optional)
            </label>
            <Input
              placeholder="2026-07-01"
              value={deadline}
              onChange={e => setDeadline(e.target.value)}
            />
          </div>
        </div>

        <div className="flex justify-end gap-2 mt-6 pt-4 border-t border-white/[0.05]">
          <Button onClick={onClose}>Cancel</Button>
          <Button
            variant="primary"
            onClick={handleSubmit}
            disabled={loading || !company || !text}
          >
            {loading ? 'Evaluating…' : 'Evaluate Offer'}
          </Button>
        </div>
      </Card>
    </ModalOverlay>
  )
}
