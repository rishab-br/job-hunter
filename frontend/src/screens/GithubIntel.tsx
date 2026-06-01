import { useEffect, useState } from 'react'
import { Github, Play, TrendingUp, AlertTriangle, CheckCircle } from 'lucide-react'
import { Card, ScoreRing, Pill, Topbar, Button, EmptyState, SectionTitle } from '../components/ui'
import { api } from '../api'
import type { GitHubIntelData, ModuleState } from '../types'

interface GithubIntelProps {
  threadId: string | null
  moduleState: ModuleState
  onRunModule: (key: string) => void
  activeJobId: string | null
}

export default function GithubIntel({ threadId, moduleState, onRunModule, activeJobId }: GithubIntelProps) {
  const [data, setData] = useState<GitHubIntelData | null>(null)

  useEffect(() => {
    if (!threadId) return
    api.sessions.audit(threadId).then(setData).catch(() => {})
  }, [threadId, moduleState.status])

  const audit = data?.github_audit
  const gap   = data?.gap_analysis
  const plan  = data?.improvement_plan ?? []

  const effortColor = (e?: string) => e === 'small' ? 'emerald' : e === 'large' ? 'red' : 'amber'
  const impactColor = (i?: string) => i === 'high' ? 'emerald' : i === 'low' ? 'muted' : 'cyan'
  const sevColor    = (s?: string) => s === 'high' ? 'red' : s === 'medium' ? 'amber' : 'emerald'

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      <Topbar breadcrumb="GitHub Intel">
        <Button
          variant="primary"
          onClick={() => onRunModule('github')}
          disabled={!!activeJobId || moduleState.status === 'running'}
        >
          <Play size={10} />
          {moduleState.status === 'running' ? 'Running…' : 'Run GitHub Intel'}
        </Button>
      </Topbar>

      <div className="flex-1 overflow-y-auto px-6 py-5">
        {!audit ? (
          <EmptyState
            icon={<Github size={36} />}
            message="Run GitHub Intel to audit your portfolio"
          />
        ) : (
          <div className="space-y-4">

            {/* Top row */}
            <div className="grid grid-cols-2 gap-4">

              {/* Score card */}
              <Card className="p-5">
                <SectionTitle>Profile Score</SectionTitle>
                <div className="flex items-center gap-5">
                  <ScoreRing score={audit.overall_score} size={100} />
                  <div className="flex-1">
                    <div className="mb-2">
                      <span className="text-[10px] text-slate-600">Bio Quality</span>
                      <div className="text-sm text-slate-200 font-medium capitalize mt-0.5">{audit.bio_quality ?? '—'}</div>
                    </div>
                    {audit.top_languages && audit.top_languages.length > 0 && (
                      <div>
                        <span className="text-[10px] text-slate-600 block mb-1">Top Languages</span>
                        <div className="flex flex-wrap gap-1">
                          {audit.top_languages.slice(0, 5).map(l => (
                            <Pill key={l} variant="muted">{l}</Pill>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {audit.summary && (
                  <p className="mt-3 text-xs text-slate-500 leading-relaxed border-t border-white/[0.05] pt-3">
                    {audit.summary}
                  </p>
                )}

                <div className="mt-3 grid grid-cols-2 gap-3">
                  {audit.key_strengths && audit.key_strengths.length > 0 && (
                    <div>
                      <div className="flex items-center gap-1 mb-1.5">
                        <CheckCircle size={10} className="text-emerald-500" />
                        <span className="text-[9px] text-slate-600 uppercase tracking-wider">Strengths</span>
                      </div>
                      <div className="flex flex-wrap gap-1">
                        {audit.key_strengths.map(s => <Pill key={s} variant="emerald">{s}</Pill>)}
                      </div>
                    </div>
                  )}
                  {audit.immediate_red_flags && audit.immediate_red_flags.length > 0 && (
                    <div>
                      <div className="flex items-center gap-1 mb-1.5">
                        <AlertTriangle size={10} className="text-red-500" />
                        <span className="text-[9px] text-slate-600 uppercase tracking-wider">Red Flags</span>
                      </div>
                      <div className="flex flex-wrap gap-1">
                        {audit.immediate_red_flags.map(f => <Pill key={f} variant="red">{f}</Pill>)}
                      </div>
                    </div>
                  )}
                </div>
              </Card>

              {/* Gap Analysis */}
              <Card className="p-5">
                <SectionTitle>Gap Analysis</SectionTitle>
                {gap ? (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-slate-500">Overall Severity</span>
                      <Pill variant={sevColor(gap.gap_severity) as 'red' | 'amber' | 'emerald'}>
                        {gap.gap_severity?.toUpperCase()}
                      </Pill>
                    </div>

                    {gap.missing_critical_skills?.length > 0 && (
                      <div>
                        <div className="text-[9px] text-slate-600 uppercase tracking-wider mb-1.5">Missing Critical Skills</div>
                        <div className="flex flex-wrap gap-1">
                          {gap.missing_critical_skills.map(s => <Pill key={s} variant="amber">{s}</Pill>)}
                        </div>
                      </div>
                    )}

                    {gap.missing_project_types?.length > 0 && (
                      <div>
                        <div className="text-[9px] text-slate-600 uppercase tracking-wider mb-1.5">Missing Project Types</div>
                        <div className="space-y-1.5">
                          {gap.missing_project_types.map((p, i) => (
                            <div key={i} className="flex items-start gap-2 text-xs">
                              <span className="text-amber-500 mt-0.5 flex-shrink-0">●</span>
                              <div>
                                <span className="text-slate-300 font-medium">{p.project_type}</span>
                                {p.why_it_matters && <span className="text-slate-600"> — {p.why_it_matters}</span>}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {gap.summary && (
                      <p className="text-xs text-slate-500 italic border-t border-white/[0.05] pt-3">{gap.summary}</p>
                    )}
                  </div>
                ) : (
                  <EmptyState icon={<TrendingUp size={28} />} message="No gap data yet" />
                )}
              </Card>
            </div>

            {/* Improvement Plan */}
            <Card className="p-5">
              <SectionTitle>Improvement Plan ({plan.length} actions)</SectionTitle>
              {plan.length === 0 ? (
                <EmptyState icon={<TrendingUp size={28} />} message="Run GitHub Intel to generate plan" />
              ) : (
                <div className="overflow-hidden rounded-lg border border-white/[0.05]">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-white/[0.05] bg-white/[0.02]">
                        {['#', 'Action', 'Category', 'Effort', 'Impact'].map(h => (
                          <th key={h} className="px-4 py-2.5 text-left text-[9px] font-semibold text-slate-600 uppercase tracking-wider">
                            {h}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/[0.03]">
                      {plan.map((item) => (
                        <tr key={item.priority} className="hover:bg-white/[0.02] transition-colors">
                          <td className="px-4 py-2.5 text-xs text-slate-600 font-mono">{item.priority}</td>
                          <td className="px-4 py-2.5 text-xs text-slate-300">{item.title}</td>
                          <td className="px-4 py-2.5"><Pill variant="muted">{item.category}</Pill></td>
                          <td className="px-4 py-2.5">
                            <Pill variant={effortColor(item.effort) as 'emerald' | 'red' | 'amber'}>{item.effort}</Pill>
                          </td>
                          <td className="px-4 py-2.5">
                            <Pill variant={impactColor(item.impact) as 'emerald' | 'cyan' | 'muted'}>{item.impact}</Pill>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Card>
          </div>
        )}
      </div>
    </div>
  )
}
