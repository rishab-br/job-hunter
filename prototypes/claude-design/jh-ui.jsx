// jh-ui.jsx — shared primitives, Sidebar, LogPanel
import React from 'react';
import {
  LayoutDashboard, Github, Search, FileText, DollarSign, MessageSquare,
  Plus, ChevronDown, ChevronUp, LogOut, Activity, Terminal,
  Trash2, Wifi
} from './jh-icons';

// ── Pill ─────────────────────────────────────────────────────────────────────
const PILL_VARIANTS = {
  cyan: 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20',
  emerald: 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20',
  amber: 'bg-amber-500/10 text-amber-400 border border-amber-500/20',
  red: 'bg-red-500/10 text-red-400 border border-red-500/20',
  violet: 'bg-violet-500/10 text-violet-400 border border-violet-500/20',
  pink: 'bg-pink-500/10 text-pink-400 border border-pink-500/20',
  muted: 'bg-white/5 text-slate-400 border border-white/10'
};

function Pill({ variant = 'muted', children, className = '' }) {
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium ${PILL_VARIANTS[variant] || PILL_VARIANTS.muted} ${className}`}>
      {children}
    </span>
  );
}

// ── StatusDot / Badge ─────────────────────────────────────────────────────────
function StatusDot({ status }) {
  const c = { running: 'bg-cyan-400 animate-dot-pulse', done: 'bg-emerald-400', warn: 'bg-amber-400', idle: 'bg-slate-600', error: 'bg-red-400' }[status] || 'bg-slate-600';
  return <span className={`inline-block w-1.5 h-1.5 rounded-full flex-shrink-0 ${c}`} />;
}

function StatusBadge({ status }) {
  const m = { running: { l: 'Running', v: 'cyan' }, done: { l: 'Done', v: 'emerald' }, warn: { l: 'Review', v: 'amber' }, idle: { l: 'Idle', v: 'muted' }, error: { l: 'Error', v: 'red' } }[status] || { l: 'Idle', v: 'muted' };
  return <Pill variant={m.v}><StatusDot status={status} />{m.l}</Pill>;
}

// ── ScoreBar ──────────────────────────────────────────────────────────────────
function ScoreBar({ value, max = 100 }) {
  const pct = Math.min(100, value / max * 100);
  const color = pct >= 85 ? '#10b981' : pct >= 70 ? '#00D4FF' : pct >= 50 ? '#f59e0b' : '#ef4444';
  return (
    <div className="flex items-center gap-2">
      <div className="w-14 h-1 bg-white/5 rounded-full overflow-hidden flex-shrink-0">
        <div className="h-full rounded-full transition-all duration-500" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="font-mono text-xs font-semibold" style={{ color }}>{value}</span>
    </div>
  );
}

// ── ScoreRing ─────────────────────────────────────────────────────────────────
function ScoreRing({ score, size = 96 }) {
  const r = (size - 10) / 2;
  const circ = 2 * Math.PI * r;
  const dash = score / 100 * circ;
  const color = score >= 70 ? '#10b981' : score >= 50 ? '#f59e0b' : '#ef4444';
  return (
    <div className="relative flex-shrink-0" style={{ width: size, height: size }}>
      <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth={8} />
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color} strokeWidth={8}
        strokeDasharray={`${dash} ${circ}`} strokeLinecap="round"
        style={{ transition: 'stroke-dasharray 0.8s ease', filter: `drop-shadow(0 0 6px ${color}80)` }} />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-2xl font-bold" style={{ color }}>{score}</span>
        <span className="text-[9px] text-slate-500 uppercase tracking-widest">/100</span>
      </div>
    </div>
  );
}

// ── EmptyState ────────────────────────────────────────────────────────────────
function EmptyState({ icon, message, action }) {
  return (
    <div className="flex flex-col items-center justify-center h-48 gap-3">
      <div className="opacity-20 text-slate-500">{icon}</div>
      <p className="text-sm text-slate-500">{message}</p>
      {action}
    </div>
  );
}

// ── Card ──────────────────────────────────────────────────────────────────────
function Card({ children, className = '', glow = false }) {
  const glowMap = {
    cyan: { border: '1px solid rgba(0,212,255,0.2)', boxShadow: '0 0 24px rgba(0,212,255,0.08)' },
    emerald: { border: '1px solid rgba(16,185,129,0.2)', boxShadow: '0 0 24px rgba(16,185,129,0.08)' },
    amber: { border: '1px solid rgba(245,158,11,0.2)', boxShadow: '0 0 24px rgba(245,158,11,0.08)' },
    red: { border: '1px solid rgba(239,68,68,0.2)', boxShadow: '0 0 24px rgba(239,68,68,0.08)' }
  };
  return (
    <div className={`rounded-2xl ${className}`}
    style={{ background: 'linear-gradient(135deg,rgba(255,255,255,0.035),rgba(255,255,255,0.01))',
      ...(glow ? glowMap[glow] : { border: '1px solid rgba(255,255,255,0.08)' }) }}>
      {children}
    </div>
  );
}

// ── Button ────────────────────────────────────────────────────────────────────
function Button({ variant = 'ghost', size = 'md', className = '', children, ...props }) {
  const base = 'inline-flex items-center gap-1.5 font-medium rounded-lg transition-all duration-150 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed';
  const sizeMap = { sm: 'px-2.5 py-1 text-xs', md: 'px-3.5 py-1.5 text-xs' };
  const variantMap = {
    primary: 'bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 hover:bg-cyan-500/20 hover:border-cyan-500/50',
    ghost: 'bg-white/[0.03] border border-white/10 text-slate-400 hover:text-slate-200 hover:border-white/20',
    danger: 'bg-red-500/10 border border-red-500/30 text-red-400 hover:bg-red-500/20'
  };
  return (
    <button className={`${base} ${sizeMap[size]} ${variantMap[variant] || variantMap.ghost} ${className}`} {...props}>
      {children}
    </button>
  );
}

// ── Topbar ────────────────────────────────────────────────────────────────────
function Topbar({ breadcrumb, children }) {
  return (
    <div className="flex items-center justify-between px-6 py-3.5 border-b flex-shrink-0"
    style={{ borderColor: 'rgba(255,255,255,0.06)', background: 'rgba(7,10,18,0.85)', backdropFilter: 'blur(8px)' }}>
      <div className="text-xs text-slate-600">
        Mission Control <span className="mx-1.5 text-slate-700">/</span>
        <span className="text-slate-300 font-semibold">{breadcrumb}</span>
      </div>
      <div className="flex items-center gap-2">{children}</div>
    </div>
  );
}

// ── SectionTitle ──────────────────────────────────────────────────────────────
function SectionTitle({ children }) {
  return <p className="text-[10px] font-semibold text-slate-600 uppercase tracking-[0.12em] mb-3">{children}</p>;
}

// ── Input / Textarea ──────────────────────────────────────────────────────────
function Input({ className = '', ...props }) {
  return (
    <input {...props}
    className={`w-full px-3 py-2 bg-[#0A0D14] border border-white/10 rounded-lg text-sm text-slate-200 placeholder-slate-600 outline-none focus:border-cyan-500/40 focus:ring-1 focus:ring-cyan-500/20 transition-all ${className}`} />
  );
}

function Textarea({ className = '', ...props }) {
  return (
    <textarea {...props}
    className={`w-full px-3 py-2 bg-[#0A0D14] border border-white/10 rounded-lg text-sm text-slate-200 placeholder-slate-600 outline-none focus:border-cyan-500/40 focus:ring-1 focus:ring-cyan-500/20 transition-all resize-none font-mono ${className}`} />
  );
}

// ── ModalOverlay ──────────────────────────────────────────────────────────────
function ModalOverlay({ children, onClose }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm animate-fade-in"
    onClick={(e) => {if (e.target === e.currentTarget) onClose();}}>
      <div className="animate-slide-up">{children}</div>
    </div>
  );
}

// ── Sidebar ───────────────────────────────────────────────────────────────────
const NAV_ITEMS = [
  { id: 'dashboard', label: 'Dashboard', Icon: LayoutDashboard, accent: '#00D4FF' },
  { id: 'github', label: 'GitHub Intel', Icon: Github, accent: '#8B5CF6' },
  { id: 'discovery', label: 'Job Discovery', Icon: Search, accent: '#00D4FF' },
  { id: 'applications', label: 'Applications', Icon: FileText, accent: '#10B981' },
  { id: 'offers', label: 'Offer Intel', Icon: DollarSign, accent: '#F59E0B' },
  { id: 'interview', label: 'Interview Prep', Icon: MessageSquare, accent: '#EC4899' }
];

function Sidebar({ screen, setScreen, auth, currentPhase, onNewSession }) {
  const phaseLabel = currentPhase && currentPhase !== 'idle' ?
  currentPhase.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()) : null;
  
  return (
    <aside className="relative w-56 min-w-[224px] flex flex-col bg-[#070a12] overflow-hidden">
      <div className="absolute left-0 top-0 bottom-0 w-[1.5px] sidebar-border z-10" />
      <div className="absolute right-0 top-0 bottom-0 w-px bg-white/[0.06]" />
      
      {/* Logo */}
      <div className="px-5 py-5 relative">
        <div className="flex items-center gap-3">
          {/* Radar scope mark */}
          <div className="relative flex-shrink-0" style={{ width:36, height:36 }}>
            <svg width="36" height="36" viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="18" cy="18" r="17" fill="rgba(0,212,255,0.04)"/>
              <circle cx="18" cy="18" r="15" stroke="rgba(0,212,255,0.22)" strokeWidth="0.75"/>
              <circle cx="18" cy="18" r="10" stroke="rgba(0,212,255,0.18)" strokeWidth="0.75"/>
              <circle cx="18" cy="18" r="5.5" stroke="rgba(0,212,255,0.3)" strokeWidth="0.75"/>
              <line x1="18" y1="18" x2="18" y2="3.5" stroke="rgba(0,212,255,0.12)" strokeWidth="6" strokeLinecap="round" className="radar-sweep-trail"/>
              <line x1="18" y1="18" x2="18" y2="3.5" stroke="#00D4FF" strokeWidth="1.25" strokeLinecap="round" className="radar-sweep"/>
              <circle cx="18" cy="18" r="1.75" fill="#00D4FF" style={{ filter:'drop-shadow(0 0 3px #00D4FF)' }}/>
            </svg>
            <div className="absolute inset-0 rounded-full pointer-events-none"
                 style={{ background:'radial-gradient(circle, rgba(0,212,255,0.12) 0%, transparent 70%)' }}/>
          </div>
          {/* Wordmark */}
          <div>
            <div className="text-sm font-extrabold leading-tight tracking-tight"
                 style={{ background:'linear-gradient(90deg,#00D4FF,#60a5fa)', WebkitBackgroundClip:'text', WebkitTextFillColor:'transparent' }}>
              JobHunter
            </div>
            <div className="text-[9px] text-slate-600 tracking-wide mt-0.5">Autonomous career agent</div>
          </div>
        </div>
        <div className="absolute -top-4 -left-4 w-24 h-24 rounded-full blur-3xl pointer-events-none" style={{ background:'rgba(0,212,255,0.08)' }}/>
      </div>
      
      <div className="px-3 pb-2">
        <div className="h-px" style={{ background: 'linear-gradient(90deg,transparent,rgba(255,255,255,0.08),transparent)' }} />
      </div>
      
      {/* Nav */}
      <nav className="flex-1 px-2 py-3 overflow-y-auto">
        <p className="px-3 mb-2.5 text-[9px] font-bold text-slate-700 uppercase tracking-[0.16em]">Navigation</p>
        {NAV_ITEMS.map(({ id, label, Icon, accent }) => {
          const isActive = screen === id;
          return (
            <button key={id} onClick={() => setScreen(id)}
            className="relative w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs mb-1 transition-all duration-200 text-left group overflow-hidden"
            style={isActive ?
            { background: `linear-gradient(90deg,${accent}18,${accent}06)`, border: `1px solid ${accent}30` } :
            { border: '1px solid transparent' }}>
              {!isActive && <div className="absolute inset-0 bg-white/0 group-hover:bg-white/[0.03] transition-colors rounded-xl" />}
              <span style={{ color: isActive ? accent : '#475569' }} className="transition-colors group-hover:text-slate-300 flex-shrink-0">
                <Icon size={15} />
              </span>
              <span className="font-medium transition-colors" style={{ color: isActive ? accent : '#6b7280' }}
              onMouseEnter={(e) => {if (!isActive) e.currentTarget.style.color = '#cbd5e1';}}
              onMouseLeave={(e) => {if (!isActive) e.currentTarget.style.color = '#6b7280';}}>
                {label}
              </span>
              {isActive && <span className="ml-auto w-1.5 h-1.5 rounded-full animate-dot-pulse flex-shrink-0"
              style={{ background: accent, boxShadow: `0 0 6px ${accent}` }} />}
            </button>
          );
        })}
      </nav>
      
      <div className="px-3 pb-1">
        <div className="h-px" style={{ background: 'linear-gradient(90deg,transparent,rgba(255,255,255,0.06),transparent)' }} />
      </div>
      
      {/* Auth */}
      <div className="px-3 py-3">
        {auth ?
        <div className="flex items-center gap-2.5 px-3 py-2 rounded-xl bg-white/[0.03] border border-white/[0.07]">
            <img src={auth.avatar} alt={auth.username} className="w-7 h-7 rounded-full flex-shrink-0"
          style={{ outline: '2px solid rgba(0,212,255,0.4)', outlineOffset: '1px' }} />
            <div className="flex-1 min-w-0">
              <div className="text-xs text-slate-200 font-semibold truncate">{auth.username}</div>
              <div className="flex items-center gap-1.5 mt-0.5">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-dot-pulse" style={{ boxShadow: '0 0 6px rgba(16,185,129,0.7)' }} />
                <span className="text-[9px] text-emerald-400 font-medium">Connected</span>
              </div>
            </div>
            <button className="text-slate-700 hover:text-red-400 transition-colors p-1 rounded-lg hover:bg-red-500/10" title="Disconnect">
              <LogOut size={11} />
            </button>
          </div> :

        <div className="flex items-center gap-2.5 px-3 py-2.5 rounded-xl border border-dashed border-white/15 text-slate-500 hover:text-slate-300 hover:border-cyan-500/40 hover:bg-cyan-500/5 text-xs transition-all font-medium cursor-pointer">
            <Github size={13} /> Connect GitHub
          </div>
        }
      </div>
      
      {/* Session */}
      <div className="px-3 pb-4">
        <div className="flex items-center justify-between mb-2">
          <p className="text-[9px] font-bold text-slate-700 uppercase tracking-[0.16em]" style={{ color: "rgb(222, 229, 240)" }}>Session</p>
          {phaseLabel && <span className="text-[9px] text-cyan-500 font-medium px-1.5 py-0.5 rounded-md bg-cyan-500/10 border border-cyan-500/20">{phaseLabel}</span>}
        </div>
        <div className="relative mb-2">
          <select defaultValue="main" className="w-full px-3 py-2 pr-7 rounded-xl text-[10px] font-mono text-slate-400 appearance-none cursor-pointer outline-none transition-all"
          style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.1)' }}>
            <option value="main">rishab-br · AI Engineer (a1b2c3…)</option>
          </select>
          <ChevronDown size={11} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-600 pointer-events-none" />
        </div>
        <button onClick={onNewSession}
        className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-xl text-[10px] font-semibold transition-all"
        style={{ background: 'linear-gradient(135deg,rgba(0,212,255,0.1),rgba(0,212,255,0.04))', border: '1px solid rgba(0,212,255,0.25)', color: '#00D4FF' }}
        onMouseEnter={(e) => e.currentTarget.style.background = 'linear-gradient(135deg,rgba(0,212,255,0.18),rgba(0,212,255,0.08))'}
        onMouseLeave={(e) => e.currentTarget.style.background = 'linear-gradient(135deg,rgba(0,212,255,0.1),rgba(0,212,255,0.04))'}>
          <Plus size={12} /> New Session
        </button>
      </div>
    </aside>
  );
}

// ── LogPanel ──────────────────────────────────────────────────────────────────
const LOG_TAG_STYLES = {
  github: { color: '#a78bfa', bg: 'rgba(167,139,250,0.12)' },
  discovery: { color: '#00D4FF', bg: 'rgba(0,212,255,0.1)' },
  app: { color: '#10B981', bg: 'rgba(16,185,129,0.1)' },
  offer: { color: '#F59E0B', bg: 'rgba(245,158,11,0.1)' },
  prep: { color: '#EC4899', bg: 'rgba(236,72,153,0.1)' },
  status: { color: '#F59E0B', bg: 'rgba(245,158,11,0.1)' },
  error: { color: '#EF4444', bg: 'rgba(239,68,68,0.1)' },
  system: { color: '#475569', bg: 'rgba(71,85,105,0.1)' }
};

function LogPanel({ logs, onClear, visible = true }) {
  const bodyRef = React.useRef(null);
  const [minimized, setMinimized] = React.useState(() =>
    localStorage.getItem('jh-log-minimized') === 'true'
  );
  const [height, setHeight] = React.useState(() =>
    parseInt(localStorage.getItem('jh-log-height') || '176', 10)
  );
  const dragState = React.useRef(null);

  React.useEffect(() => {
    if (bodyRef.current) bodyRef.current.scrollTop = 0;
  }, [logs.length]);

  React.useEffect(() => {
    localStorage.setItem('jh-log-minimized', minimized);
  }, [minimized]);

  React.useEffect(() => {
    localStorage.setItem('jh-log-height', height);
  }, [height]);

  const onDragStart = React.useCallback((e) => {
    e.preventDefault();
    dragState.current = { startY: e.clientY, startH: height };
    const onMove = (ev) => {
      if (!dragState.current) return;
      const delta = dragState.current.startY - ev.clientY;
      setHeight(Math.max(72, Math.min(600, dragState.current.startH + delta)));
    };
    const onUp = () => {
      dragState.current = null;
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    };
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
  }, [height]);

  if (!visible) return null;

  return (
    <div className="flex-shrink-0 flex flex-col border-t relative"
         style={{ height: minimized ? 'auto' : height, background: '#030508', borderColor: 'rgba(255,255,255,0.06)', transition: minimized ? 'height 0.15s ease' : 'none' }}>

      {!minimized && (
        <div onMouseDown={onDragStart} className="absolute top-0 left-0 right-0 z-20 flex items-center justify-center" style={{ height: 8, cursor: 'ns-resize' }} title="Drag to resize">
          <div style={{ width: 36, height: 2, borderRadius: 1, background: 'rgba(255,255,255,0.13)', transition: 'background 0.15s' }}
               onMouseEnter={e => e.currentTarget.style.background = 'rgba(0,212,255,0.5)'}
               onMouseLeave={e => e.currentTarget.style.background = 'rgba(255,255,255,0.13)'} />
        </div>
      )}

      <div className="flex items-center justify-between px-5 py-2.5 border-b flex-shrink-0"
           style={{ borderColor: 'rgba(255,255,255,0.05)', background: 'rgba(0,0,0,0.4)', paddingTop: minimized ? 10 : undefined }}>
        <div className="flex items-center gap-2.5">
          <Terminal size={12} style={{ color: '#1e3a2f' }} />
          <span className="text-[10px] font-bold uppercase tracking-[0.15em] text-slate-700">Agent Log</span>
          <div className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full animate-dot-pulse" style={{ background: '#10B981', boxShadow: '0 0 6px rgba(16,185,129,0.8)' }} />
            <span className="text-[9px] text-emerald-700 font-semibold">LIVE</span>
          </div>
          {logs.length > 0 && <span className="text-[9px] text-slate-800">{logs.length} entries</span>}
        </div>
        <div className="flex items-center gap-3">
          <Wifi size={10} style={{ color: logs.length > 0 ? '#10B981' : '#1e3a2f' }} />
          <button onClick={onClear} className="flex items-center gap-1.5 text-slate-800 hover:text-slate-500 transition-colors text-[9px] uppercase tracking-wider">
            <Trash2 size={10} /> Clear
          </button>
          <button onClick={() => setMinimized(m => !m)} title={minimized ? 'Expand' : 'Minimize'}
            className="flex items-center justify-center rounded transition-colors" style={{ color: '#334155', width: 18, height: 18, background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)' }}
            onMouseEnter={e => { e.currentTarget.style.color = '#00D4FF'; e.currentTarget.style.borderColor = 'rgba(0,212,255,0.3)'; }}
            onMouseLeave={e => { e.currentTarget.style.color = '#334155'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.07)'; }}>
            {minimized ? <ChevronUp size={10} /> : <ChevronDown size={10} />}
          </button>
        </div>
      </div>

      {!minimized && (
        <div ref={bodyRef} className="flex-1 overflow-y-auto px-5 py-3">
          {logs.length === 0 ?
            <div className="flex items-center gap-2 h-full">
              <span style={{ color: '#1e3a2f' }}>$</span>
              <span className="text-[11px] animate-dot-pulse" style={{ color: '#1e3a2f' }}>Waiting for agent activity_</span>
            </div> :
            <div className="space-y-0.5">
              {logs.slice(0, 60).map((e, i) =>
                <div key={e.id} className={`flex gap-3 ${i === 0 ? 'log-line-enter' : ''}`}>
                  <span className="text-slate-800 flex-shrink-0 tabular-nums select-none">{e.ts}</span>
                  <span className="flex-shrink-0 min-w-[130px] px-1.5 py-0 rounded text-[10px]"
                        style={{ color: e.tagColor, background: e.tagBg, fontWeight: 600 }}>{e.tag}</span>
                  <span style={{ color: e.msgColor }}>{e.msg}</span>
                </div>
              )}
            </div>
          }
        </div>
      )}
    </div>
  );
}

export {
  Pill, StatusDot, StatusBadge, ScoreBar, ScoreRing,
  EmptyState, Card, Button, Topbar, SectionTitle,
  Input, Textarea, ModalOverlay, Sidebar, LogPanel,
  LOG_TAG_STYLES, NAV_ITEMS
};
