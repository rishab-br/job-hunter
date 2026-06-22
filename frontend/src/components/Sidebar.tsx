import {
  LayoutDashboard, Github, Search, FileText, DollarSign, MessageSquare, Bot,
  Plus, ChevronDown, LogOut,
} from 'lucide-react'
import type { AuthState, Session, Screen } from '../types'

interface NavItem { id: Screen; label: string; icon: React.ReactNode; accent: string }

const NAV_ITEMS: NavItem[] = [
  { id: 'dashboard',    label: 'Dashboard',      icon: <LayoutDashboard size={15} />, accent: '#00D4FF' },
  { id: 'github',       label: 'GitHub Intel',   icon: <Github size={15} />,          accent: '#8B5CF6' },
  { id: 'discovery',    label: 'Job Discovery',  icon: <Search size={15} />,           accent: '#00D4FF' },
  { id: 'applications', label: 'Applications',   icon: <FileText size={15} />,         accent: '#10B981' },
  { id: 'interview',    label: 'Interview Prep', icon: <MessageSquare size={15} />,    accent: '#EC4899' },
  { id: 'offers',       label: 'Offer Intel',    icon: <DollarSign size={15} />,       accent: '#F59E0B' },
  { id: 'autopilot',   label: 'Autopilot',       icon: <Bot size={15} />,              accent: '#A78BFA' },
]

interface SidebarProps {
  screen: Screen
  setScreen: (s: Screen) => void
  auth: AuthState | null
  onLogout: () => void
  sessions: Session[]
  threadId: string | null
  setThreadId: (id: string | null) => void
  currentPhase: string
  onNewSession: () => void
}

export default function Sidebar({
  screen, setScreen, auth, onLogout,
  sessions, threadId, setThreadId, currentPhase, onNewSession,
}: SidebarProps) {
  const phaseLabel = currentPhase !== 'idle'
    ? currentPhase.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
    : null

  return (
    <aside className="relative w-56 min-w-[224px] flex flex-col bg-[#070a12] overflow-hidden">

      {/* Left gradient accent line */}
      <div className="absolute left-0 top-0 bottom-0 w-[1.5px] sidebar-border z-10" />

      {/* Right border */}
      <div className="absolute right-0 top-0 bottom-0 w-px bg-white/[0.06]" />

      {/* Logo */}
      <div className="px-5 py-5 relative">
        <div className="flex items-center gap-3">
          {/* Radar scope — clean sweep, no cardinal tick marks */}
          <div className="relative flex-shrink-0" style={{ width: 36, height: 36 }}>
            <svg width="36" height="36" viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="18" cy="18" r="17" fill="rgba(0,212,255,0.04)" />
              <circle cx="18" cy="18" r="15" stroke="rgba(0,212,255,0.22)" strokeWidth="0.75" />
              <circle cx="18" cy="18" r="10" stroke="rgba(0,212,255,0.18)" strokeWidth="0.75" />
              <circle cx="18" cy="18" r="5.5" stroke="rgba(0,212,255,0.3)"  strokeWidth="0.75" />
              {/* Sweep trail */}
              <line x1="18" y1="18" x2="18" y2="3.5" stroke="rgba(0,212,255,0.12)" strokeWidth="6"   strokeLinecap="round" className="radar-sweep-trail" />
              {/* Sweep arm */}
              <line x1="18" y1="18" x2="18" y2="3.5" stroke="#00D4FF"             strokeWidth="1.25" strokeLinecap="round" className="radar-sweep" />
              {/* Centre dot */}
              <circle cx="18" cy="18" r="1.75" fill="#00D4FF" style={{ filter: 'drop-shadow(0 0 3px #00D4FF)' }} />
            </svg>
            <div
              className="absolute inset-0 rounded-full pointer-events-none"
              style={{ background: 'radial-gradient(circle, rgba(0,212,255,0.12) 0%, transparent 70%)' }}
            />
          </div>
          <div>
            <div
              className="text-sm font-extrabold leading-tight"
              style={{ background: 'linear-gradient(90deg, #00D4FF, #60a5fa)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}
            >
              JobHunter
            </div>
            <div className="text-[9px] text-slate-600 tracking-wide mt-0.5">Autonomous career agent</div>
          </div>
        </div>

        {/* Glow behind logo */}
        <div className="absolute -top-4 -left-4 w-24 h-24 rounded-full blur-3xl pointer-events-none"
             style={{ background: 'rgba(0,212,255,0.08)' }} />
      </div>

      <div className="px-3 pb-2">
        <div className="h-px" style={{ background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.08), transparent)' }} />
      </div>

      {/* Nav */}
      <nav className="flex-1 px-2 py-3 overflow-y-auto">
        <p className="px-3 mb-2.5 text-[9px] font-bold text-slate-700 uppercase tracking-[0.16em]">Navigation</p>
        {NAV_ITEMS.map(item => {
          const isActive = screen === item.id
          return (
            <button
              key={item.id}
              onClick={() => setScreen(item.id)}
              className="relative w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs mb-1 transition-all duration-200 text-left group overflow-hidden"
              style={isActive ? {
                background: `linear-gradient(90deg, ${item.accent}18, ${item.accent}06)`,
                border: `1px solid ${item.accent}30`,
              } : {
                border: '1px solid transparent',
              }}
            >
              {/* Hover shimmer */}
              {!isActive && (
                <div className="absolute inset-0 bg-white/0 group-hover:bg-white/[0.03] transition-colors rounded-xl" />
              )}

              <span style={{ color: isActive ? item.accent : '#475569' }} className="transition-colors group-hover:text-slate-300">
                {item.icon}
              </span>

              <span
                className="font-medium transition-colors"
                style={{ color: isActive ? item.accent : undefined }}
              >
                {!isActive && <span className="text-slate-500 group-hover:text-slate-300 transition-colors">{item.label}</span>}
                {isActive && item.label}
              </span>

              {isActive && (
                <span
                  className="ml-auto w-1.5 h-1.5 rounded-full animate-dot-pulse"
                  style={{ background: item.accent, boxShadow: `0 0 6px ${item.accent}` }}
                />
              )}
            </button>
          )
        })}
      </nav>

      <div className="px-3 pb-1">
        <div className="h-px" style={{ background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.06), transparent)' }} />
      </div>

      {/* GitHub Auth */}
      <div className="px-3 py-3">
        {auth ? (
          <div className="flex items-center gap-2.5 px-3 py-2 rounded-xl bg-white/[0.03] border border-white/[0.07]">
            <img src={auth.avatar} alt={auth.username}
                 className="w-7 h-7 rounded-full flex-shrink-0"
                 style={{ outline: '2px solid rgba(0,212,255,0.4)', outlineOffset: '1px' }} />
            <div className="flex-1 min-w-0">
              <div className="text-xs text-slate-200 font-semibold truncate">{auth.username}</div>
              <div className="flex items-center gap-1.5 mt-0.5">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-dot-pulse" style={{ boxShadow: '0 0 6px rgba(16,185,129,0.7)' }} />
                <span className="text-[9px] text-emerald-400 font-medium">Connected</span>
              </div>
            </div>
            <button onClick={onLogout} className="text-slate-700 hover:text-red-400 transition-colors p-1 rounded-lg hover:bg-red-500/10" title="Disconnect">
              <LogOut size={11} />
            </button>
          </div>
        ) : (
          <a
            href="/auth/github"
            className="flex items-center gap-2.5 px-3 py-2.5 rounded-xl border border-dashed border-white/15 text-slate-500 hover:text-slate-300 hover:border-cyan-500/40 hover:bg-cyan-500/5 text-xs transition-all font-medium"
          >
            <Github size={13} />
            Connect GitHub
          </a>
        )}
      </div>

      {/* Session */}
      <div className="px-3 pb-4">
        <div className="flex items-center justify-between mb-2">
          <p className="text-[9px] font-bold text-slate-700 uppercase tracking-[0.16em]">Session</p>
          {phaseLabel && (
            <span className="text-[9px] text-cyan-500 font-medium px-1.5 py-0.5 rounded-md bg-cyan-500/10 border border-cyan-500/20">
              {phaseLabel}
            </span>
          )}
        </div>

        <div className="relative mb-2">
          <select
            value={threadId ?? ''}
            onChange={e => setThreadId(e.target.value || null)}
            className="w-full px-3 py-2 pr-7 rounded-xl text-[10px] font-mono text-slate-400 appearance-none cursor-pointer outline-none transition-all"
            style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.1)' }}
          >
            <option value="">— no session —</option>
            {sessions.map(s => (
              <option key={s.thread_id} value={s.thread_id}>
                {s.github_username || '?'} · {s.target_role || '?'} ({s.thread_id.slice(0, 8)}…)
              </option>
            ))}
          </select>
          <ChevronDown size={11} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-600 pointer-events-none" />
        </div>

        <button
          onClick={onNewSession}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-xl text-[10px] font-semibold transition-all"
          style={{
            background: 'linear-gradient(135deg, rgba(0,212,255,0.1), rgba(0,212,255,0.04))',
            border: '1px solid rgba(0,212,255,0.25)',
            color: '#00D4FF',
          }}
          onMouseEnter={e => (e.currentTarget.style.background = 'linear-gradient(135deg, rgba(0,212,255,0.18), rgba(0,212,255,0.08))')}
          onMouseLeave={e => (e.currentTarget.style.background = 'linear-gradient(135deg, rgba(0,212,255,0.1), rgba(0,212,255,0.04))')}
        >
          <Plus size={12} />
          New Session
        </button>
      </div>
    </aside>
  )
}
