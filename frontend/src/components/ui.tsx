import React from 'react'

// ── Badge / Pill ───────────────────────────────────────────────────────────────

const pillVariants = {
  cyan:    'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20',
  emerald: 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20',
  amber:   'bg-amber-500/10 text-amber-400 border border-amber-500/20',
  red:     'bg-red-500/10 text-red-400 border border-red-500/20',
  violet:  'bg-violet-500/10 text-violet-400 border border-violet-500/20',
  pink:    'bg-pink-500/10 text-pink-400 border border-pink-500/20',
  muted:   'bg-white/5 text-slate-400 border border-white/10',
}

export type PillVariant = keyof typeof pillVariants

interface PillProps {
  variant?: PillVariant
  children: React.ReactNode
  className?: string
}

export function Pill({ variant = 'muted', children, className = '' }: PillProps) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium ${pillVariants[variant]} ${className}`}>
      {children}
    </span>
  )
}

// ── Status Badge ──────────────────────────────────────────────────────────────

export function StatusDot({ status }: { status: 'running' | 'done' | 'warn' | 'idle' | 'error' }) {
  const config = {
    running: { color: 'bg-cyan-400', anim: 'animate-pulse-cyan' },
    done:    { color: 'bg-emerald-400', anim: 'animate-pulse-emerald' },
    warn:    { color: 'bg-amber-400', anim: '' },
    idle:    { color: 'bg-slate-600', anim: '' },
    error:   { color: 'bg-red-400', anim: '' },
  }
  const c = config[status]
  return <span className={`inline-block w-1.5 h-1.5 rounded-full ${c.color} ${c.anim}`} />
}

export function StatusBadge({ status }: { status: 'running' | 'done' | 'warn' | 'idle' | 'error' }) {
  const config = {
    running: { label: 'Running', variant: 'cyan' as PillVariant },
    done:    { label: 'Done',    variant: 'emerald' as PillVariant },
    warn:    { label: 'Review',  variant: 'amber' as PillVariant },
    idle:    { label: 'Idle',    variant: 'muted' as PillVariant },
    error:   { label: 'Error',   variant: 'red' as PillVariant },
  }
  const c = config[status]
  return (
    <Pill variant={c.variant} className="gap-1">
      <StatusDot status={status} />
      {c.label}
    </Pill>
  )
}

// ── Score Bar ─────────────────────────────────────────────────────────────────

export function ScoreBar({ value, max = 100 }: { value: number; max?: number }) {
  const pct = Math.min(100, (value / max) * 100)
  const color = pct >= 85 ? '#10b981' : pct >= 70 ? '#00D4FF' : pct >= 50 ? '#f59e0b' : '#ef4444'
  return (
    <div className="flex items-center gap-2">
      <div className="w-14 h-1 bg-white/5 rounded-full overflow-hidden flex-shrink-0">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${pct}%`, background: color }}
        />
      </div>
      <span className="font-mono text-xs font-semibold" style={{ color }}>{value}</span>
    </div>
  )
}

// ── Score Ring ────────────────────────────────────────────────────────────────

export function ScoreRing({ score, size = 96 }: { score: number; size?: number }) {
  const r = (size - 10) / 2
  const circ = 2 * Math.PI * r
  const dash = (score / 100) * circ
  const color = score >= 70 ? '#10b981' : score >= 50 ? '#f59e0b' : '#ef4444'

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="score-ring">
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth={8} />
        <circle
          cx={size/2} cy={size/2} r={r} fill="none"
          stroke={color} strokeWidth={8}
          strokeDasharray={`${dash} ${circ}`}
          strokeLinecap="round"
          style={{ transition: 'stroke-dasharray 0.8s ease', filter: `drop-shadow(0 0 6px ${color}80)` }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-2xl font-bold text-slate-100" style={{ color }}>{score}</span>
        <span className="text-[9px] text-slate-500 uppercase tracking-widest">/100</span>
      </div>
    </div>
  )
}

// ── Empty State ───────────────────────────────────────────────────────────────

export function EmptyState({ icon, message }: { icon: React.ReactNode; message: string }) {
  return (
    <div className="flex flex-col items-center justify-center h-48 gap-3 text-slate-600">
      <div className="opacity-30">{icon}</div>
      <p className="text-sm text-slate-500">{message}</p>
    </div>
  )
}

// ── Card ──────────────────────────────────────────────────────────────────────

interface CardProps {
  children: React.ReactNode
  className?: string
  glow?: 'cyan' | 'emerald' | 'amber' | 'red' | false
}

export function Card({ children, className = '', glow = false }: CardProps) {
  const glowStyle = glow === 'cyan'    ? { border: '1px solid rgba(0,212,255,0.2)',    boxShadow: '0 0 24px rgba(0,212,255,0.08)'    }
    : glow === 'emerald' ? { border: '1px solid rgba(16,185,129,0.2)',  boxShadow: '0 0 24px rgba(16,185,129,0.08)'  }
    : glow === 'amber'   ? { border: '1px solid rgba(245,158,11,0.2)',  boxShadow: '0 0 24px rgba(245,158,11,0.08)'  }
    : glow === 'red'     ? { border: '1px solid rgba(239,68,68,0.2)',   boxShadow: '0 0 24px rgba(239,68,68,0.08)'   }
    : { border: '1px solid rgba(255,255,255,0.08)' }

  return (
    <div
      className={`rounded-2xl ${className}`}
      style={{ background: 'linear-gradient(135deg, rgba(255,255,255,0.035), rgba(255,255,255,0.01))', ...glowStyle }}
    >
      {children}
    </div>
  )
}

// ── Button ────────────────────────────────────────────────────────────────────

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'ghost' | 'danger'
  size?: 'sm' | 'md'
}

export function Button({ variant = 'ghost', size = 'md', className = '', children, ...props }: ButtonProps) {
  const base = 'inline-flex items-center gap-1.5 font-medium rounded-lg transition-all duration-150 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed'
  const sizes = { sm: 'px-2.5 py-1 text-xs', md: 'px-3.5 py-1.5 text-xs' }
  const variants = {
    primary: 'bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 hover:bg-cyan-500/20 hover:border-cyan-500/50',
    ghost:   'bg-white/[0.03] border border-white/10 text-slate-400 hover:text-slate-200 hover:border-white/20',
    danger:  'bg-red-500/10 border border-red-500/30 text-red-400 hover:bg-red-500/20',
  }
  return (
    <button className={`${base} ${sizes[size]} ${variants[variant]} ${className}`} {...props}>
      {children}
    </button>
  )
}

// ── Topbar ────────────────────────────────────────────────────────────────────

export function Topbar({ breadcrumb, children }: { breadcrumb: string; children?: React.ReactNode }) {
  return (
    <div
      className="flex items-center justify-between px-6 py-3.5 border-b flex-shrink-0"
      style={{ borderColor: 'rgba(255,255,255,0.06)', background: 'rgba(7,10,18,0.85)', backdropFilter: 'blur(8px)' }}
    >
      <div className="text-xs text-slate-600">
        Mission Control{' '}
        <span className="mx-1.5 text-slate-700">/</span>
        <span className="text-slate-300 font-semibold">{breadcrumb}</span>
      </div>
      <div className="flex items-center gap-2">{children}</div>
    </div>
  )
}

// ── Input / Textarea ──────────────────────────────────────────────────────────

export function Input(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className={`w-full px-3 py-2 bg-[#0A0D14] border border-white/10 rounded-lg text-sm text-slate-200 placeholder-slate-600 outline-none focus:border-cyan-500/40 focus:ring-1 focus:ring-cyan-500/20 transition-all ${props.className ?? ''}`}
    />
  )
}

export function Textarea(props: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      {...props}
      className={`w-full px-3 py-2 bg-[#0A0D14] border border-white/10 rounded-lg text-sm text-slate-200 placeholder-slate-600 outline-none focus:border-cyan-500/40 focus:ring-1 focus:ring-cyan-500/20 transition-all resize-none font-mono ${props.className ?? ''}`}
    />
  )
}

export function Select(props: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      {...props}
      className={`px-3 py-2 bg-[#0A0D14] border border-white/10 rounded-lg text-xs text-slate-300 outline-none focus:border-cyan-500/40 transition-all cursor-pointer ${props.className ?? ''}`}
    />
  )
}

// ── Modal wrapper ─────────────────────────────────────────────────────────────

export function ModalOverlay({ children, onClose }: { children: React.ReactNode; onClose: () => void }) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm animate-fade-in"
      onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
    >
      <div className="animate-slide-up">
        {children}
      </div>
    </div>
  )
}

// ── Section Title ─────────────────────────────────────────────────────────────

export function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-[10px] font-semibold text-slate-600 uppercase tracking-[0.12em] mb-3">
      {children}
    </p>
  )
}
