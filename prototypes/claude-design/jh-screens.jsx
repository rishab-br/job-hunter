// jh-screens.jsx — Screen components (GitHub, Discovery, Applications, Offers, Interview)
import React from 'react';
import { Pill, StatusBadge, ScoreBar, ScoreRing, EmptyState, Card, Button, Topbar, SectionTitle, Input } from './jh-ui';
import {
  Github, Search, FileText, DollarSign, MessageSquare,
  Play, RefreshCw, Download, CheckCircle, AlertTriangle, ExternalLink, ShieldCheck, Plus
} from './jh-icons';

// ── GithubIntelScreen ─────────────────────────────────────────────────────────
function GithubIntelScreen({ data, moduleState, onRunModule, activeJobId }) {
  const audit = data?.github_audit;
  const gap   = data?.gap_analysis;
  const plan  = data?.improvement_plan || [];
  const effortColor = e => e==='small'?'emerald':e==='large'?'red':'amber';
  const impactColor = i => i==='high'?'emerald':i==='low'?'muted':'cyan';
  const sevColor    = s => s==='high'?'red':s==='medium'?'amber':'emerald';
  
  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      <Topbar breadcrumb="GitHub Intel">
        <Button variant="primary" onClick={() => onRunModule('github')} disabled={!!activeJobId || moduleState.status==='running'}>
          <Play size={10}/>{moduleState.status==='running'?'Running…':'Run GitHub Intel'}
        </Button>
      </Topbar>
      <div className="flex-1 overflow-y-auto px-6 py-5">
        {!audit ? (
          <EmptyState icon={<Github size={36}/>} message="Run GitHub Intel to audit your portfolio"/>
        ) : (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <Card className="p-5">
                <SectionTitle>Profile Score</SectionTitle>
                <div className="flex items-center gap-5">
                  <ScoreRing score={audit.overall_score} size={100}/>
                  <div className="flex-1 min-w-0">
                    <div className="mb-3">
                      <span className="text-[10px] text-slate-600">Bio Quality</span>
                      <div className="text-sm text-slate-200 font-medium capitalize mt-0.5">{audit.bio_quality}</div>
                    </div>
                    <span className="text-[10px] text-slate-600 block mb-1">Top Languages</span>
                    <div className="flex flex-wrap gap-1">
                      {(audit.top_languages||[]).slice(0,5).map(l=><Pill key={l} variant="muted">{l}</Pill>)}
                    </div>
                  </div>
                </div>
                {audit.summary && <p className="mt-3 text-xs text-slate-500 leading-relaxed border-t border-white/[0.05] pt-3">{audit.summary}</p>}
              </Card>
              <Card className="p-5">
                <SectionTitle>Gap Analysis</SectionTitle>
                {gap ? (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-slate-500">Overall Severity</span>
                      <Pill variant={sevColor(gap.gap_severity)}>{(gap.gap_severity||'').toUpperCase()}</Pill>
                    </div>
                    {(gap.missing_critical_skills||[]).length>0 && (
                      <div>
                        <div className="text-[9px] text-slate-600 uppercase tracking-wider mb-1.5">Missing Critical Skills</div>
                        <div className="flex flex-wrap gap-1">{gap.missing_critical_skills.map(s=><Pill key={s} variant="amber">{s}</Pill>)}</div>
                      </div>
                    )}
                  </div>
                ) : <EmptyState icon={<AlertTriangle size={28}/>} message="No gap data yet"/>}
              </Card>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ── JobDiscoveryScreen ────────────────────────────────────────────────────────
function JobDiscoveryScreen({ jobs, moduleState, onRunModule, activeJobId }) {
  const [query, setQuery] = React.useState('');
  const [platform, setPlatform] = React.useState('');
  const [priority, setPriority] = React.useState('');
  const filtered = React.useMemo(() => jobs.filter(j=>
    (!query || j.company.toLowerCase().includes(query.toLowerCase()) || j.job_title.toLowerCase().includes(query.toLowerCase())) &&
    (!platform || j.platform === platform) &&
    (!priority || j.priority === priority)
  ), [jobs, query, platform, priority]);

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      <Topbar breadcrumb="Job Discovery">
        <Button size="sm" onClick={() => { const rows=[['Company','Role','Score','Platform','Priority'],
          ...jobs.map(j=>[j.company,j.job_title,j.relevance_score,j.platform,j.priority])];
          const a=Object.assign(document.createElement('a'),{href:'data:text/csv,'+encodeURIComponent(rows.map(r=>r.join(',')).join('\n')),download:'jobs.csv'}); a.click(); }} disabled={!jobs.length}>
          <Download size={11}/> Export CSV
        </Button>
        <Button variant="primary" size="sm" onClick={()=>onRunModule('discovery')} disabled={!!activeJobId||moduleState.status==='running'}>
          <RefreshCw size={11}/>{moduleState.status==='running'?'Scanning…':'Rescan'}
        </Button>
      </Topbar>
      <div className="flex-1 overflow-y-auto px-6 py-5">
        <div className="flex items-center gap-3 mb-4">
          <div className="relative flex-1">
            <Search size={12} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-600"/>
            <input type="text" placeholder="Filter by company, role…" value={query} onChange={e=>setQuery(e.target.value)}
              className="w-full pl-8 pr-3 py-2 bg-[#0D1117] border border-white/[0.06] rounded-lg text-xs text-slate-300 placeholder-slate-600 outline-none focus:border-cyan-500/30 transition-all"/>
          </div>
          <span className="text-[10px] text-slate-600 whitespace-nowrap">{filtered.length}/{jobs.length} results</span>
        </div>
        {jobs.length===0 ? <EmptyState icon={<Search size={36}/>} message="No jobs found — run Job Discovery"/> : (
          <div className="border border-white/[0.06] rounded-xl overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/[0.05] bg-[#0D1117]">
                  <th className="px-4 py-3 text-left text-[9px] font-semibold text-slate-600">Company</th>
                  <th className="px-4 py-3 text-left text-[9px] font-semibold text-slate-600">Role</th>
                  <th className="px-4 py-3 text-left text-[9px] font-semibold text-slate-600">Platform</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.03]">
                {filtered.map(j=>(
                  <tr key={j.job_id} className="hover:bg-white/[0.02]">
                    <td className="px-4 py-3 text-sm font-medium text-slate-200">{j.company}</td>
                    <td className="px-4 py-3 text-xs text-slate-400">{j.job_title}</td>
                    <td className="px-4 py-3"><Pill variant="muted">{j.platform}</Pill></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

// ── ApplicationsScreen ────────────────────────────────────────────────────────
const STATUS_CONFIG = {
  submitted:           { label:'Submitted',      variant:'emerald' },
  applied:             { label:'Applied',         variant:'muted'   },
  viewed:              { label:'Viewed',           variant:'cyan'    },
  shortlisted:         { label:'Shortlisted',     variant:'amber'   },
  interview_scheduled: { label:'Interview ✓',     variant:'emerald' },
  offer:               { label:'Offer! 🎉',       variant:'violet'  },
  rejected:            { label:'Rejected',        variant:'red'     },
};

function ApplicationsScreen({ apps, moduleState, onRunModule, activeJobId }) {
  const summary = apps.reduce((acc,a)=>{ acc[a.status]=(acc[a.status]||0)+1; return acc; },{});
  
  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      <Topbar breadcrumb="Applications">
        <Button variant="primary" size="sm" onClick={()=>onRunModule('application')} disabled={!!activeJobId||moduleState.status==='running'}>
          <Play size={10}/>{moduleState.status==='running'?'Applying…':'Apply to Queued'}
        </Button>
      </Topbar>
      <div className="flex-1 overflow-y-auto px-6 py-5 space-y-4">
        {apps.length>0 && (
          <div className="flex items-center gap-2 flex-wrap">
            {Object.entries(summary).map(([status,count])=>{
              const cfg=STATUS_CONFIG[status]||{label:status,variant:'muted'};
              return <Pill key={status} variant={cfg.variant}>{cfg.label}: {count}</Pill>;
            })}
          </div>
        )}
        {apps.length===0 ? <EmptyState icon={<FileText size={36}/>} message="No applications yet"/> : (
          <div className="border border-white/[0.06] rounded-xl overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/[0.05] bg-[#0D1117]">
                  <th className="px-4 py-3 text-left text-[9px] font-semibold text-slate-600">Company</th>
                  <th className="px-4 py-3 text-left text-[9px] font-semibold text-slate-600">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.03]">
                {apps.map(a=>{
                  const cfg=STATUS_CONFIG[a.status]||{label:a.status,variant:'muted'};
                  return (
                    <tr key={a.job_id} className="hover:bg-white/[0.02]">
                      <td className="px-4 py-3 text-sm font-semibold text-slate-200">{a.company}</td>
                      <td className="px-4 py-3"><Pill variant={cfg.variant}>{cfg.label}</Pill></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

// ── OffersScreen ──────────────────────────────────────────────────────────────
const RISK_CONFIG = {
  high:   { variant:'red',     label:'High Risk' },
  medium: { variant:'amber',   label:'Med Risk' },
  low:    { variant:'emerald', label:'Low Risk' },
};

function OffersScreen({ offers, moduleState, onRunModule, activeJobId }) {
  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      <Topbar breadcrumb="Offer Intelligence">
        <Button size="sm" onClick={()=>{}}><Plus size={11}/> Inject Offer</Button>
        <Button variant="primary" size="sm" onClick={()=>onRunModule('offer')} disabled={!!activeJobId||moduleState.status==='running'}>
          <RefreshCw size={11}/>{moduleState.status==='running'?'Evaluating…':'Re-evaluate'}
        </Button>
      </Topbar>
      <div className="flex-1 overflow-y-auto px-6 py-5">
        {offers.length===0 ? <EmptyState icon={<DollarSign size={36}/>} message="No offers yet"/> : (
          <div className="space-y-4">
            {offers.map(o=>{
              const risk=RISK_CONFIG[o.risk_level||'low'];
              return (
                <Card key={o.offer_id} className="p-5">
                  <div className="flex items-start justify-between mb-4">
                    <div><h3 className="text-base font-bold text-slate-100">{o.company}</h3>
                      <p className="text-xs text-slate-500 mt-0.5">{o.job_title}</p></div>
                    <Pill variant={risk.variant}>{risk.label}</Pill>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <div className="text-[9px] text-slate-600 uppercase tracking-wider mb-1.5">Offered CTC</div>
                      <div className="text-lg font-bold text-slate-200">{o.total_ctc||'—'}</div>
                    </div>
                    <div>
                      <div className="text-[9px] text-slate-600 uppercase tracking-wider mb-1.5">Counter Ask</div>
                      <div className="text-lg font-bold text-cyan-400">{o.counter_ask||'—'}</div>
                    </div>
                  </div>
                </Card>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

// ── InterviewPrepScreen ───────────────────────────────────────────────────────
function InterviewPrepScreen({ sessions, moduleState, onOpenPrepModal, activeJobId }) {
  const [selected, setSelected] = React.useState(sessions[0]||null);
  React.useEffect(()=>{ if(sessions.length>0&&!selected) setSelected(sessions[0]); },[sessions]);
  
  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      <Topbar breadcrumb="Interview Prep">
        <Button size="sm"><Download size={11}/> Export All</Button>
        <Button variant="primary" size="sm" onClick={onOpenPrepModal} disabled={!!activeJobId}>
          <Plus size={11}/> New Prep
        </Button>
      </Topbar>
      <div className="flex-1 overflow-hidden px-6 py-5">
        {sessions.length===0 ? <EmptyState icon={<MessageSquare size={36}/>} message="No prep sessions yet"/> : (
          <div className="space-y-4">
            <SectionTitle>Prep Sessions ({sessions.length})</SectionTitle>
            <div className="space-y-2">
              {sessions.map((s,i)=>(
                <div key={s.session_id} onClick={()=>setSelected(s)}
                  className="p-4 rounded-xl border cursor-pointer transition-all"
                  style={selected?.session_id===s.session_id
                    ? { borderColor:'rgba(0,212,255,0.3)', background:'rgba(0,212,255,0.05)' }
                    : { borderColor:'rgba(255,255,255,0.06)', background:'#0D1117' }}>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-semibold text-slate-200">{s.company}</span>
                    <Pill variant={i===0?'emerald':'muted'}>{s.prep_date}</Pill>
                  </div>
                  <div className="text-xs text-slate-500">{s.role}</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export {
  GithubIntelScreen, JobDiscoveryScreen, ApplicationsScreen,
  OffersScreen, InterviewPrepScreen
};
