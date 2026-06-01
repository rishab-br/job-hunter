import { useState } from 'react'
import { X, Github } from 'lucide-react'
import { Card, Input, Button, ModalOverlay } from '../components/ui'
import type { AuthState } from '../types'

interface NewSessionModalProps {
  auth: AuthState | null
  onClose: () => void
  onSubmit: (data: Record<string, string>) => Promise<void>
}

export default function NewSessionModal({ auth, onClose, onSubmit }: NewSessionModalProps) {
  const [username, setUsername] = useState('')
  const [role, setRole]         = useState('')
  const [market, setMarket]     = useState('India')
  const [niche, setNiche]       = useState('')
  const [loading, setLoading]   = useState(false)

  async function handleSubmit() {
    if (!role) return
    if (!auth && !username) return
    setLoading(true)
    try {
      const body: Record<string, string> = { target_role: role, target_market: market, target_niche: niche }
      if (auth) body.user_id = auth.userId
      else body.github_username = username
      await onSubmit(body)
      onClose()
    } finally {
      setLoading(false)
    }
  }

  return (
    <ModalOverlay onClose={onClose}>
      <Card className="w-[440px] max-w-[95vw] p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-sm font-semibold text-slate-200">New Session</h2>
            <p className="text-xs text-slate-600 mt-0.5">Configure your job hunting target</p>
          </div>
          <button onClick={onClose} className="text-slate-600 hover:text-slate-400 transition-colors p-1">
            <X size={14} />
          </button>
        </div>

        <div className="space-y-4">
          {auth ? (
            <div className="flex items-center gap-2.5 px-3 py-2.5 rounded-lg bg-emerald-500/8 border border-emerald-500/20">
              {auth.avatar && <img src={auth.avatar} className="w-5 h-5 rounded-full" />}
              <Github size={12} className="text-emerald-400" />
              <span className="text-xs text-emerald-400 font-medium">
                GitHub connected as <strong>{auth.username}</strong>
              </span>
            </div>
          ) : (
            <div>
              <label className="block text-[10px] font-semibold text-slate-600 uppercase tracking-wider mb-1.5">
                GitHub Username
              </label>
              <Input
                placeholder="johndoe"
                value={username}
                onChange={e => setUsername(e.target.value)}
              />
            </div>
          )}

          <div>
            <label className="block text-[10px] font-semibold text-slate-600 uppercase tracking-wider mb-1.5">
              Target Role <span className="text-red-500">*</span>
            </label>
            <Input
              placeholder="AI Engineer"
              value={role}
              onChange={e => setRole(e.target.value)}
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-[10px] font-semibold text-slate-600 uppercase tracking-wider mb-1.5">
                Target Market
              </label>
              <Input
                placeholder="India"
                value={market}
                onChange={e => setMarket(e.target.value)}
              />
            </div>
            <div>
              <label className="block text-[10px] font-semibold text-slate-600 uppercase tracking-wider mb-1.5">
                Niche / Focus
              </label>
              <Input
                placeholder="MLOps, LLM fine-tuning…"
                value={niche}
                onChange={e => setNiche(e.target.value)}
              />
            </div>
          </div>
        </div>

        <div className="flex justify-end gap-2 mt-6 pt-4 border-t border-white/[0.05]">
          <Button onClick={onClose}>Cancel</Button>
          <Button
            variant="primary"
            onClick={handleSubmit}
            disabled={loading || !role || (!auth && !username)}
          >
            {loading ? 'Creating…' : 'Create Session'}
          </Button>
        </div>
      </Card>
    </ModalOverlay>
  )
}
