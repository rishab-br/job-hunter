// jh-dashboard.jsx — Dashboard screen (StatCards + Pipeline + ModuleGrid)

// ── StatCard ──────────────────────────────────────────────────────────────────
function StatCard({ label, value, icon, accent, sub }) {
  const v = (value === null || value === undefined) ? '—' : value;
  return (
    <div className="relative overflow-hidden rounded-2xl p-5 flex flex-col justify-between min-h-[130px] transition-all duration-300 hover:scale-[1.01] hover:brightness-110 cursor-default"
         style={{ background:`linear-gradient(135deg,${accent}12 0%,rgba(255,255,255,0.03) 60%,transparent 100%)`, border:`1px solid ${accent}28` }}>
      <div className="absolute -top-8 -right-8 w-32 h-32 rounded-full blur-3xl pointer-events-none" style={{ background:`${accent}20` }}/>
      <div className="flex items-start justify-between relative z-10">
        <div className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0"
             style={{ background:`${accent}18`, border:`1px solid ${accent}35`, color:accent }}>
          {icon}
        </div>
        {sub && <span className="text-[10px] font-semibold px-2 py-1 rounded-full"
                      style={{ background:`${accent}15`, color:accent, border:`1px solid ${accent}30` }}>{sub}</span>}
      </div>
      <div className="relative z-10">
        <div className="text-4xl font-black tracking-tight leading-none mb-1"
             style={{ color: v==='—'?'rgba(255,255,255,0.2)':'white', textShadow: v!=='—'?`0 0 30px ${accent}50`:'none' }}>
          {v}
        </div>
        <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-widest">{label}</div>
      </div>
      <div className="absolute bottom-0 left-0 right-0 h-[2px]"
           style={{ background:`linear-gradient(90deg,transparent,${accent}60,transparent)` }}/>
    </div>
  );
}

// ── Pipeline ──────────────────────────────────────────────────────────────────
const PIPE_STEPS = [
  { key:'github_analysis',  label:'GitHub\nIntel',    Icon:()=><Github size={18}/>,         color:'#8B5CF6' },
  { key:'job_discovery',    label:'Job\nDiscovery',   Icon:()=><Search size={18}/>,          color:'#00D4FF' },
  { key:'applying',         label:'App\nEngine',      Icon:()=><FileText size={18}/>,        color:'#10B981' },
  { key:'tracking',         label:'Status\nTracker',  Icon:()=><Activity size={18}/>,        color:'#F59E0B' },
  { key:'offer_evaluation', label:'Offer\nIntel',     Icon:()=><DollarSign size={18}/>,      color:'#FBBF24' },
  { key:'interview_prep',   label:'Interview\nPrep',  Icon:()=><MessageSquare size={18}/>,   color:'#EC4899' },
];

function Pipeline({ currentPhase, summary }) {
  const phaseOrder = PIPE_STEPS.map(s=>s.key);
  const curIdx = phaseOrder.indexOf(currentPhase);
  return (
    <div className="rounded-2xl p-5"
         style={{ background:'linear-gradient(135deg,rgba(255,255,255,0.03),rgba(255,255,255,0.01))', border:'1px solid rgba(255,255,255,0.08)' }}>
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-2">
          <div className="w-1 h-4 rounded-full" style={{ background:'linear-gradient(180deg,#00D4FF,#7C3AED)' }}/>
          <span className="text-xs font-bold text-slate-300 uppercase tracking-widest">Pipeline Status</span>
        </div>
        <span className="text-[10px] text-slate-600">{curIdx>=0?`Step ${curIdx+1} of ${PIPE_STEPS.length}`:'Idle'}</span>
      </div>
      <div className="flex items-center">
        {PIPE_STEPS.map((step, i) => {
          const hasKey = summary?.[`has_${step.key.split('_')[0]}`];
          const isDone = curIdx > i || !!hasKey;
          const isActive = step.key === currentPhase;
          return (
            <div key={step.key} className="flex items-center flex-1 last:flex-none">
              <div className="flex flex-col items-center gap-2.5">
                <div className="w-11 h-11 rounded-2xl flex items-center justify-center relative transition-all duration-500"
                     style={{
                       background: isActive?`${step.color}22`:isDone?`${step.color}14`:'rgba(255,255,255,0.03)',
                       border:`1px solid ${isActive?step.color+'70':isDone?step.color+'35':'rgba(255,255,255,0.08)'}`,
                       color: isActive?step.color:isDone?step.color+'bb':'#374151',
                       boxShadow: isActive?`0 0 20px ${step.color}40,0 0 40px ${step.color}15`:'none',
                     }}>
                  <step.Icon/>
                  {isActive && <div className="absolute -inset-1 rounded-2xl animate-dot-pulse" style={{ border:`1px solid ${step.color}50` }}/>}
                  {isDone && !isActive && (
                    <div className="absolute -top-1 -right-1 w-4 h-4 rounded-full flex items-center justify-center text-[8px] font-bold text-slate-900"
                         style={{ background:step.color, boxShadow:`0 0 8px ${step.color}80` }}>✓</div>
                  )}
                </div>
                <span className="text-[9px] text-center font-semibold whitespace-pre-line leading-tight"
                      style={{ color: isActive?step.color:isDone?'rgba(255,255,255,0.5)':'#374151' }}>
                  {step.label}
                </span>
              </div>
              {i < PIPE_STEPS.length-1 && (
                <div className="flex-1 mx-2 mb-6">
                  <div className="relative h-[2px] rounded-full overflow-hidden"
                       style={{ background: isDone||isActive?`${step.color}30`:'rgba(255,255,255,0.04)' }}>
                    {(isDone||isActive) && <div className="pipe-flow absolute inset-0" style={{ color:step.color }}/>}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── ModuleCard ────────────────────────────────────────────────────────────────
const MODULE_DEFS = [
  { key:'github',      name:'GitHub Intel',       Icon:Github,       metricKey:'github_score',    metricLabel:'profile score /100', color:'#8B5CF6', screen:'github'       },
  { key:'discovery',   name:'Job Discovery',      Icon:Search,       metricKey:'jobs_found',      metricLabel:'jobs found',          color:'#00D4FF', screen:'discovery'    },
  { key:'application', name:'Application Engine', Icon:FileText,     metricKey:'apps_submitted',  metricLabel:'submitted',           color:'#10B981', screen:'applications' },
  { key:'status',      name:'Status Tracker',     Icon:Activity,     metricKey:'ghosted',         metricLabel:'ghosted',             color:'#F59E0B', screen:'applications' },
  { key:'offer',       name:'Offer Intelligence', Icon:DollarSign,   metricKey:'offers_received', metricLabel:'offers evaluated',    color:'#FBBF24', screen:'offers'       },
  { key:'prep',        name:'Interview Prep',     Icon:MessageSquare,metricKey:'prep_sessions',   metricLabel:'sessions ready',      color:'#EC4899', screen:'interview'    },
];

function ModuleCard({ def, state, metric, onRun, onView, disabled }) {
  const { color, name, metricLabel, Icon } = def;
  const status = state.status || 'idle';
  const running = status === 'running';
  const done = status === 'done';
  const statCfg = {
    running: { label:'Running', dot:'#00D4FF',  bg:'rgba(0,212,255,0.1)',  border:'rgba(0,212,255,0.3)'  },
    done:    { label:'Done',    dot:'#10B981',  bg:'rgba(16,185,129,0.1)', border:'rgba(16,185,129,0.3)' },
    warn:    { label:'Review',  dot:'#F59E0B',  bg:'rgba(245,158,11,0.1)', border:'rgba(245,158,11,0.3)' },
    error:   { label:'Error',   dot:'#EF4444',  bg:'rgba(239,68,68,0.1)',  border:'rgba(239,68,68,0.3)'  },
    idle:    { label:'Idle',    dot:'#334155',  bg:'rgba(255,255,255,0.04)',border:'rgba(255,255,255,0.1)'},
  }[status] || { label:'Idle', dot:'#334155', bg:'rgba(255,255,255,0.04)', border:'rgba(255,255,255,0.1)' };

  return (
    <div className={`relative overflow-hidden rounded-2xl p-5 flex flex-col gap-3 transition-all duration-300 group ${running?'card-running':''}`}
         style={{
           background: done?`linear-gradient(135deg,${color}10,rgba(255,255,255,0.02))`:'linear-gradient(135deg,rgba(255,255,255,0.035),rgba(255,255,255,0.01))',
           border:`1px solid ${running?color+'40':done?color+'25':'rgba(255,255,255,0.08)'}`,
           boxShadow: running?`0 0 24px ${color}15`:done?`0 0 16px ${color}10`:'none',
         }}>
      <div className="absolute right-2 bottom-2 opacity-[0.04] pointer-events-none transition-opacity group-hover:opacity-[0.07]" style={{ color }}>
        <Icon size={72}/>
      </div>
      {/* Header */}
      <div className="flex items-start justify-between relative z-10">
        <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background:`${color}18`, border:`1px solid ${color}35`, color }}>
          <Icon size={17}/>
        </div>
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[9px] font-bold"
             style={{ background:statCfg.bg, border:`1px solid ${statCfg.border}` }}>
          <span className={`w-1.5 h-1.5 rounded-full ${running?'animate-dot-pulse':''}`}
                style={{ background:statCfg.dot, boxShadow:running?`0 0 6px ${statCfg.dot}`:'none' }}/>
          <span style={{ color:statCfg.dot }}>{statCfg.label}</span>
        </div>
      </div>
      {/* Metric */}
      <div className="relative z-10">
        <div className="text-3xl font-black leading-none mb-1 transition-colors"
             style={{ color:(done||running)?color:'rgba(255,255,255,0.25)', textShadow:(done||running)?`0 0 20px ${color}60`:'none' }}>
          {String(metric)}
        </div>
        <div className="text-[9px] text-slate-600 uppercase tracking-widest font-semibold">{metricLabel}</div>
      </div>
      {/* Name + ts */}
      <div className="relative z-10">
        <div className="text-xs font-semibold text-slate-400">{name}</div>
        <div className="text-[9px] text-slate-700 font-mono mt-0.5">{state.ts || 'Never run'}</div>
      </div>
      {/* Buttons */}
      <div className="relative z-10 flex gap-2">
        <button onClick={onRun} disabled={disabled || running}
          className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-xl text-[10px] font-bold uppercase tracking-wider transition-all duration-200 disabled:opacity-30 disabled:cursor-not-allowed"
          style={running
            ? { background:`${color}15`, border:`1px solid ${color}40`, color }
            : { background:'rgba(255,255,255,0.04)', border:'1px solid rgba(255,255,255,0.1)', color:'#64748b' }}
          onMouseEnter={e=>{ if(!disabled&&!running){ e.currentTarget.style.background=`${color}12`; e.currentTarget.style.borderColor=`${color}35`; e.currentTarget.style.color=color; }}}
          onMouseLeave={e=>{ if(!disabled&&!running){ e.currentTarget.style.background='rgba(255,255,255,0.04)'; e.currentTarget.style.borderColor='rgba(255,255,255,0.1)'; e.currentTarget.style.color='#64748b'; }}}>
          {running ? <><Square size={9}/>Running…</> : <><Play size={9}/>Run</>}
        </button>
        {done && (
          <button onClick={onView}
            className="flex items-center justify-center gap-1 px-3 py-2 rounded-xl text-[10px] font-bold uppercase tracking-wider transition-all"
            style={{ background:`${color}12`, border:`1px solid ${color}35`, color }}>
            View →
          </button>
        )}
      </div>
    </div>
  );
}

// ── DashboardScreen ───────────────────────────────────────────────────────────
function DashboardScreen({ summary, moduleStates, onRunModule, onRefresh, activeJobId, onNavigate }) {
  const phase = summary?.current_phase || 'idle';
  const s = summary || {};
  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      <div className="flex items-center justify-between px-6 py-3.5 border-b border-white/[0.06] flex-shrink-0"
           style={{ background:'rgba(7,10,18,0.8)', backdropFilter:'blur(8px)' }}>
        <div className="text-xs text-slate-600">
          Mission Control <span className="mx-1.5 text-slate-700">/</span>
          <span className="text-slate-300 font-semibold">Dashboard</span>
        </div>
        <button onClick={onRefresh}
          className="flex items-center gap-2 px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-all"
          style={{ background:'rgba(255,255,255,0.04)', border:'1px solid rgba(255,255,255,0.1)', color:'#64748b' }}
          onMouseEnter={e=>{ e.currentTarget.style.color='#e2e8f0'; e.currentTarget.style.borderColor='rgba(255,255,255,0.18)'; }}
          onMouseLeave={e=>{ e.currentTarget.style.color='#64748b'; e.currentTarget.style.borderColor='rgba(255,255,255,0.1)'; }}>
          <RefreshCw size={12}/> Refresh
        </button>
      </div>
      <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5 bg-grid" style={{ backgroundSize:'40px 40px' }}>
        {/* Stat row */}
        <div className="grid grid-cols-4 gap-4">
          <StatCard label="Jobs Found"         value={s.jobs_found      ?? '—'} icon={<Search size={18}/>}     accent="#00D4FF"/>
          <StatCard label="Apps Submitted"     value={s.apps_submitted  ?? '—'} icon={<Briefcase size={18}/>}  accent="#10B981"/>
          <StatCard label="Interviews Prepped" value={s.prep_sessions   ?? '—'} icon={<Star size={18}/>}       accent="#8B5CF6"/>
          <StatCard label="Offers Received"    value={s.offers_received ?? '—'} icon={<TrendingUp size={18}/>} accent="#F59E0B"/>
        </div>
        {/* Pipeline */}
        <Pipeline currentPhase={phase} summary={summary}/>
        {/* Module grid */}
        <div>
          <div className="flex items-center gap-2 mb-3">
            <div className="w-1 h-4 rounded-full" style={{ background:'linear-gradient(180deg,#00D4FF,#7C3AED)' }}/>
            <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">Agent Modules</span>
          </div>
          <div className="grid grid-cols-3 gap-3">
            {MODULE_DEFS.map(m => {
              const state  = moduleStates[m.key] || { status:'idle' };
              const metric = s[m.metricKey] ?? state.metric ?? '—';
              return (
                <ModuleCard key={m.key} def={m} state={state} metric={String(metric)}
                  onRun={() => onRunModule(m.key)}
                  onView={() => onNavigate(m.screen)}
                  disabled={!!activeJobId}/>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

export { DashboardScreen, MODULE_DEFS, PIPE_STEPS };
