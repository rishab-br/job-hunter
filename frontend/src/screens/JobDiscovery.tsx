import { useEffect, useState, useMemo } from 'react'
import { Search, Download, RefreshCw, ExternalLink } from 'lucide-react'
import { ScoreBar, Pill, Topbar, Button, EmptyState } from '../components/ui'
import { api } from '../api'
import type { Job, ModuleState } from '../types'

interface JobDiscoveryProps {
  threadId: string | null
  moduleState: ModuleState
  onRunModule: (key: string) => void
  activeJobId: string | null
}

const PLATFORM_COLORS: Record<string, 'cyan' | 'amber' | 'red' | 'emerald' | 'violet' | 'muted'> = {
  LinkedIn:   'cyan',
  Indeed:     'amber',
  Naukri:     'red',
  Greenhouse: 'emerald',
  Lever:      'violet',
}

export default function JobDiscovery({ threadId, moduleState, onRunModule, activeJobId }: JobDiscoveryProps) {
  const [jobs, setJobs]         = useState<Job[]>([])
  const [query, setQuery]       = useState('')
  const [platform, setPlatform] = useState('')
  const [priority, setPriority] = useState('')

  useEffect(() => {
    if (!threadId) return
    api.sessions.jobs(threadId).then(d => setJobs(d.jobs ?? [])).catch(() => {})
  }, [threadId, moduleState.status])

  const filtered = useMemo(() => jobs.filter(j =>
    (!query    || j.company.toLowerCase().includes(query.toLowerCase()) || j.job_title.toLowerCase().includes(query.toLowerCase())) &&
    (!platform || j.platform === platform) &&
    (!priority || j.priority === priority)
  ), [jobs, query, platform, priority])

  function exportCSV() {
    if (!jobs.length) return
    const rows = [['Company','Role','Score','Platform','Priority','URL'], ...jobs.map(j => [j.company, j.job_title, j.relevance_score, j.platform, j.priority, j.url])]
    const a = Object.assign(document.createElement('a'), {
      href: 'data:text/csv,' + encodeURIComponent(rows.map(r => r.join(',')).join('\n')),
      download: 'jobs.csv',
    })
    a.click()
  }

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      <Topbar breadcrumb="Job Discovery">
        <Button size="sm" onClick={exportCSV} disabled={!jobs.length}>
          <Download size={11} />
          Export CSV
        </Button>
        <Button variant="primary" size="sm" onClick={() => onRunModule('discovery')} disabled={!!activeJobId || moduleState.status === 'running'}>
          <RefreshCw size={11} />
          {moduleState.status === 'running' ? 'Scanning…' : 'Rescan'}
        </Button>
      </Topbar>

      <div className="flex-1 overflow-y-auto px-6 py-5">
        {/* Filters */}
        <div className="flex items-center gap-3 mb-4">
          <div className="relative flex-1">
            <Search size={12} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-600" />
            <input
              type="text"
              placeholder="Filter by company, role…"
              value={query}
              onChange={e => setQuery(e.target.value)}
              className="w-full pl-8 pr-3 py-2 bg-[#0D1117] border border-white/[0.06] rounded-lg text-xs text-slate-300 placeholder-slate-600 outline-none focus:border-cyan-500/30 transition-all"
            />
          </div>
          <select
            value={platform}
            onChange={e => setPlatform(e.target.value)}
            className="px-3 py-2 bg-[#0D1117] border border-white/[0.06] rounded-lg text-xs text-slate-400 outline-none focus:border-cyan-500/30 transition-all cursor-pointer"
          >
            <option value="">All Platforms</option>
            <option>LinkedIn</option>
            <option>Indeed</option>
            <option>Naukri</option>
          </select>
          <select
            value={priority}
            onChange={e => setPriority(e.target.value)}
            className="px-3 py-2 bg-[#0D1117] border border-white/[0.06] rounded-lg text-xs text-slate-400 outline-none focus:border-cyan-500/30 transition-all cursor-pointer"
          >
            <option value="">All Priority</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
          <span className="text-[10px] text-slate-600 whitespace-nowrap">
            {filtered.length} / {jobs.length} results
          </span>
        </div>

        {/* Table */}
        {jobs.length === 0 ? (
          <EmptyState icon={<Search size={36} />} message="No jobs found — run Job Discovery" />
        ) : (
          <div className="border border-white/[0.06] rounded-xl overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="border-b border-white/[0.05] bg-[#0D1117]">
                  {['Company', 'Role', 'Score', 'Platform', 'Priority', ''].map((h, i) => (
                    <th key={i} className="px-4 py-3 text-left text-[9px] font-semibold text-slate-600 uppercase tracking-wider">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.03]">
                {filtered.map(j => (
                  <tr key={j.job_id} className="hover:bg-white/[0.02] transition-colors">
                    <td className="px-4 py-3 text-sm font-medium text-slate-200">{j.company}</td>
                    <td className="px-4 py-3 text-xs text-slate-400">{j.job_title}</td>
                    <td className="px-4 py-3"><ScoreBar value={j.relevance_score} /></td>
                    <td className="px-4 py-3">
                      <Pill variant={PLATFORM_COLORS[j.platform] ?? 'muted'}>{j.platform}</Pill>
                    </td>
                    <td className="px-4 py-3">
                      <Pill variant={j.priority === 'high' ? 'emerald' : j.priority === 'medium' ? 'cyan' : 'muted'}>
                        {j.priority}
                      </Pill>
                    </td>
                    <td className="px-4 py-3">
                      <a
                        href={j.url || '#'}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-[10px] text-slate-500 hover:text-cyan-400 transition-colors"
                      >
                        <ExternalLink size={11} />
                        Open
                      </a>
                    </td>
                  </tr>
                ))}
                {filtered.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-4 py-10 text-center text-sm text-slate-600">
                      No results match your filters
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
