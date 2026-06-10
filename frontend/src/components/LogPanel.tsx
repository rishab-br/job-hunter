import { useRef, useEffect, useState, useCallback } from 'react'
import { Terminal, Trash2, Wifi, ChevronDown, ChevronUp } from 'lucide-react'
import type { LogEntry } from '../types'

interface LogPanelProps {
  logs: LogEntry[]
  onClear: () => void
}

const TAG_STYLES: Record<string, { color: string; bg: string }> = {
  github:    { color: '#a78bfa', bg: 'rgba(167,139,250,0.12)' },
  discovery: { color: '#00D4FF', bg: 'rgba(0,212,255,0.1)'   },
  app:       { color: '#10B981', bg: 'rgba(16,185,129,0.1)'  },
  offer:     { color: '#F59E0B', bg: 'rgba(245,158,11,0.1)'  },
  prep:      { color: '#EC4899', bg: 'rgba(236,72,153,0.1)'  },
  interview: { color: '#EC4899', bg: 'rgba(236,72,153,0.1)'  },
  error:     { color: '#EF4444', bg: 'rgba(239,68,68,0.1)'   },
  system:    { color: '#475569', bg: 'rgba(71,85,105,0.1)'   },
}

const MSG_COLORS: Record<string, string> = {
  success: '#10B981',
  warn:    '#F59E0B',
  error:   '#EF4444',
  info:    '#00D4FF',
  '':      '#475569',
}

export function parseLogLine(raw: string, id: number): LogEntry {
  const ts = new Date().toTimeString().slice(0, 8)
  const m  = raw.match(/^\[([^\]]+)\]\s*(.*)/)
  if (!m) return { id, ts, tag: '[SYS]', tagClass: '#475569', msg: raw, msgClass: '#475569', raw }

  const tag = `[${m[1]}]`
  const msg = m[2]
  const key = m[1].toLowerCase()

  const tagStyle = Object.entries(TAG_STYLES).find(([k]) => key.includes(k))?.[1] ?? TAG_STYLES.system
  const msgColor = msg.includes('✓') || msg.toLowerCase().includes('done') || msg.toLowerCase().includes('completed') ? MSG_COLORS.success
    : msg.includes('⚠') || msg.toLowerCase().includes('warn')    ? MSG_COLORS.warn
    : msg.includes('ERROR') || msg.toLowerCase().includes('fail') ? MSG_COLORS.error
    : msg.includes('→') || msg.includes('saved') || msg.toLowerCase().includes('started') ? MSG_COLORS.info
    : MSG_COLORS['']

  return { id, ts, tag, tagClass: tagStyle.color, msg, msgClass: msgColor, raw }
}

export default function LogPanel({ logs, onClear }: LogPanelProps) {
  const bodyRef = useRef<HTMLDivElement>(null)

  // ── Minimize / height state (both persisted to localStorage) ────────────────
  const [minimized, setMinimized] = useState<boolean>(
    () => localStorage.getItem('jh-log-minimized') === 'true'
  )
  const [height, setHeight] = useState<number>(
    () => parseInt(localStorage.getItem('jh-log-height') ?? '176', 10)
  )

  // Drag-to-resize state (not persisted, just in-flight)
  const dragState = useRef<{ startY: number; startH: number } | null>(null)

  useEffect(() => { if (bodyRef.current) bodyRef.current.scrollTop = 0 }, [logs.length])

  useEffect(() => {
    localStorage.setItem('jh-log-minimized', String(minimized))
  }, [minimized])

  useEffect(() => {
    localStorage.setItem('jh-log-height', String(height))
  }, [height])

  // ── Drag handle ──────────────────────────────────────────────────────────────
  const onDragStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    dragState.current = { startY: e.clientY, startH: height }

    const onMove = (ev: MouseEvent) => {
      if (!dragState.current) return
      const delta = dragState.current.startY - ev.clientY
      setHeight(Math.max(72, Math.min(600, dragState.current.startH + delta)))
    }
    const onUp = () => {
      dragState.current = null
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
    }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
  }, [height])

  return (
    <div
      className="flex-shrink-0 flex flex-col border-t relative"
      style={{
        height: minimized ? 'auto' : height,
        background: '#030508',
        borderColor: 'rgba(255,255,255,0.06)',
        transition: minimized ? 'height 0.15s ease' : 'none',
      }}
    >
      {/* ── Drag handle (only shown when expanded) ── */}
      {!minimized && (
        <div
          onMouseDown={onDragStart}
          className="absolute top-0 left-0 right-0 z-20 flex items-center justify-center"
          style={{ height: 8, cursor: 'ns-resize' }}
          title="Drag to resize"
        >
          <div
            className="drag-handle-bar"
            style={{ width: 36, height: 2, borderRadius: 1, background: 'rgba(255,255,255,0.13)', transition: 'background 0.15s' }}
            onMouseEnter={e => (e.currentTarget.style.background = 'rgba(0,212,255,0.5)')}
            onMouseLeave={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.13)')}
          />
        </div>
      )}

      {/* ── Header ── */}
      <div
        className="flex items-center justify-between px-5 py-2.5 border-b flex-shrink-0"
        style={{ borderColor: 'rgba(255,255,255,0.05)', background: 'rgba(0,0,0,0.4)' }}
      >
        <div className="flex items-center gap-2.5">
          <Terminal size={12} style={{ color: '#1e3a2f' }} />
          <span className="text-[10px] font-bold uppercase tracking-[0.15em] text-slate-700 log-terminal">
            Agent Log
          </span>
          <div className="flex items-center gap-1.5">
            <span
              className="w-1.5 h-1.5 rounded-full animate-dot-pulse"
              style={{ background: '#10B981', boxShadow: '0 0 6px rgba(16,185,129,0.8)' }}
            />
            <span className="text-[9px] text-emerald-700 font-semibold log-terminal">LIVE</span>
          </div>
          {logs.length > 0 && (
            <span className="text-[9px] text-slate-800 log-terminal">{logs.length} entries</span>
          )}
        </div>

        <div className="flex items-center gap-3">
          <Wifi size={10} style={{ color: logs.length > 0 ? '#10B981' : '#1e3a2f' }} />
          <button
            onClick={onClear}
            className="flex items-center gap-1.5 text-slate-800 hover:text-slate-500 transition-colors text-[9px] uppercase tracking-wider log-terminal"
          >
            <Trash2 size={10} />
            Clear
          </button>
          {/* ── Minimize / expand toggle ── */}
          <button
            onClick={() => setMinimized(m => !m)}
            title={minimized ? 'Expand log' : 'Minimize log'}
            className="flex items-center justify-center rounded transition-colors"
            style={{ color: '#334155', width: 18, height: 18, background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)' }}
            onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.color = '#00D4FF'; (e.currentTarget as HTMLButtonElement).style.borderColor = 'rgba(0,212,255,0.3)' }}
            onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.color = '#334155'; (e.currentTarget as HTMLButtonElement).style.borderColor = 'rgba(255,255,255,0.07)' }}
          >
            {minimized ? <ChevronUp size={10} /> : <ChevronDown size={10} />}
          </button>
        </div>
      </div>

      {/* ── Body (hidden when minimized) ── */}
      {!minimized && (
        <div ref={bodyRef} className="flex-1 overflow-y-auto px-5 py-3 log-terminal">
          {logs.length === 0 ? (
            <div className="flex items-center gap-2 h-full">
              <span style={{ color: '#1e3a2f' }}>$</span>
              <span className="text-[11px] animate-dot-pulse" style={{ color: '#1e3a2f' }}>
                Waiting for agent activity_
              </span>
            </div>
          ) : (
            <div className="space-y-0.5">
              {logs.slice(0, 60).map((entry, i) => {
                const tagStyle = Object.entries(TAG_STYLES).find(
                  ([k]) => entry.tagClass.includes(k) || entry.tag.toLowerCase().includes(k)
                )?.[1]
                return (
                  <div key={entry.id} className={`flex gap-3 ${i === 0 ? 'log-line-enter' : ''}`}>
                    <span className="text-slate-800 flex-shrink-0 tabular-nums select-none">{entry.ts}</span>
                    <span
                      className="flex-shrink-0 min-w-[130px] px-1.5 py-0 rounded text-[10px]"
                      style={{
                        color: entry.tagClass,
                        background: tagStyle?.bg ?? 'transparent',
                        fontWeight: 600,
                      }}
                    >
                      {entry.tag}
                    </span>
                    <span style={{ color: entry.msgClass }}>{entry.msg}</span>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
