import { useState } from 'react'
import { X, MessageSquare } from 'lucide-react'
import { Card, Input, Textarea, Button, ModalOverlay } from '../components/ui'

interface PrepModalProps {
  onClose: () => void
  onSubmit: (data: {
    company: string
    role: string
    company_url: string
    jd_text: string
  }) => Promise<void>
}

export default function PrepModal({ onClose, onSubmit }: PrepModalProps) {
  const [company, setCompany] = useState('')
  const [role,    setRole]    = useState('')
  const [url,     setUrl]     = useState('')
  const [jd,      setJd]      = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit() {
    if (!company || !role || !jd) return
    setLoading(true)
    try {
      await onSubmit({ company, role, company_url: url, jd_text: jd })
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
            <div className="w-7 h-7 rounded-lg bg-pink-500/10 border border-pink-500/25 flex items-center justify-center">
              <MessageSquare size={13} className="text-pink-400" />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-slate-200">New Interview Prep</h2>
              <p className="text-xs text-slate-600 mt-0.5">Generate cheat sheets & Q&A banks</p>
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
              <Input placeholder="Acme AI" value={company} onChange={e => setCompany(e.target.value)} />
            </div>
            <div>
              <label className="block text-[10px] font-semibold text-slate-600 uppercase tracking-wider mb-1.5">
                Role <span className="text-red-500">*</span>
              </label>
              <Input placeholder="ML Engineer" value={role} onChange={e => setRole(e.target.value)} />
            </div>
          </div>

          <div>
            <label className="block text-[10px] font-semibold text-slate-600 uppercase tracking-wider mb-1.5">
              Company URL (optional)
            </label>
            <Input
              placeholder="https://acme.ai"
              value={url}
              onChange={e => setUrl(e.target.value)}
            />
          </div>

          <div>
            <label className="block text-[10px] font-semibold text-slate-600 uppercase tracking-wider mb-1.5">
              Job Description <span className="text-red-500">*</span>
            </label>
            <Textarea
              placeholder="Paste the full job description here…"
              value={jd}
              onChange={e => setJd(e.target.value)}
              className="h-32"
            />
          </div>
        </div>

        <div className="flex justify-end gap-2 mt-6 pt-4 border-t border-white/[0.05]">
          <Button onClick={onClose}>Cancel</Button>
          <Button
            variant="primary"
            onClick={handleSubmit}
            disabled={loading || !company || !role || !jd}
          >
            {loading ? 'Generating…' : 'Start Prep'}
          </Button>
        </div>
      </Card>
    </ModalOverlay>
  )
}
