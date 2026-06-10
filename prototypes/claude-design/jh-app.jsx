// App.jsx — Main application entry point
import React from 'react';
import { DashboardScreen } from './jh-dashboard';
import { Sidebar, LogPanel } from './jh-ui';
import { GithubIntelScreen, JobDiscoveryScreen, ApplicationsScreen, OffersScreen, InterviewPrepScreen } from './jh-screens';
import './App.css';

export default function App() {
  const [screen, setScreen] = React.useState('dashboard');
  const [logs, setLogs] = React.useState([]);
  const [auth, setAuth] = React.useState({
    username: 'rishab-br',
    avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=rishab'
  });

  // Mock data
  const [summary, setSummary] = React.useState({
    jobs_found: 47,
    apps_submitted: 12,
    prep_sessions: 3,
    offers_received: 2,
    current_phase: 'idle'
  });

  const [moduleStates, setModuleStates] = React.useState({
    github: { status: 'idle', ts: 'Never run' },
    discovery: { status: 'idle', ts: 'Never run' },
    application: { status: 'idle', ts: 'Never run' },
    status: { status: 'idle', ts: 'Never run' },
    offer: { status: 'idle', ts: 'Never run' },
    prep: { status: 'idle', ts: 'Never run' }
  });

  const [activeJobId, setActiveJobId] = React.useState(null);

  // Mock data for screens
  const [jobsData, setJobsData] = React.useState([
    { job_id: 1, company: 'Google', job_title: 'Senior Engineer', relevance_score: 95, platform: 'LinkedIn', priority: 'high', url: '#' },
    { job_id: 2, company: 'Meta', job_title: 'ML Engineer', relevance_score: 88, platform: 'Indeed', priority: 'high', url: '#' },
    { job_id: 3, company: 'Amazon', job_title: 'Backend Engineer', relevance_score: 72, platform: 'LinkedIn', priority: 'medium', url: '#' }
  ]);

  const [appsData, setAppsData] = React.useState([
    { job_id: 1, company: 'Google', job_title: 'Senior Engineer', platform: 'LinkedIn', status: 'shortlisted', submitted_at: '2024-01-15', url: '#' },
    { job_id: 2, company: 'Meta', job_title: 'ML Engineer', platform: 'Indeed', status: 'interview_scheduled', submitted_at: '2024-01-10', url: '#' },
    { job_id: 3, company: 'Amazon', job_title: 'Backend Engineer', platform: 'LinkedIn', status: 'applied', submitted_at: '2024-01-20', url: '#' }
  ]);

  const [offersData, setOffersData] = React.useState([
    { offer_id: 1, company: 'Google', job_title: 'Senior Engineer', total_ctc: '$450K', counter_ask: '$480K', risk_level: 'low' },
    { offer_id: 2, company: 'Meta', job_title: 'ML Engineer', total_ctc: '$420K', counter_ask: '$450K', risk_level: 'medium' }
  ]);

  const [sessionsData, setSessionsData] = React.useState([
    { session_id: 1, company: 'Google', role: 'Senior Engineer', prep_date: '2024-01-25', question_count: 45 },
    { session_id: 2, company: 'Meta', role: 'ML Engineer', prep_date: '2024-01-20', question_count: 38 }
  ]);

  const handleRunModule = (moduleKey) => {
    setModuleStates(prev => ({
      ...prev,
      [moduleKey]: { ...prev[moduleKey], status: 'running' }
    }));

    // Simulate module running
    setTimeout(() => {
      setModuleStates(prev => ({
        ...prev,
        [moduleKey]: { status: 'done', ts: new Date().toLocaleTimeString() }
      }));
      
      // Add a log entry
      const now = new Date();
      const ts = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`;
      setLogs(prev => [{
        id: Date.now(),
        ts,
        tag: moduleKey.split('_')[0].toUpperCase(),
        tagColor: '#00D4FF',
        tagBg: 'rgba(0,212,255,0.1)',
        msg: `Module ${moduleKey} completed successfully`,
        msgColor: '#cbd5e1'
      }, ...prev]);
    }, 2000);
  };

  const handleRefresh = () => {
    setSummary(prev => ({ ...prev, jobs_found: Math.floor(Math.random() * 100) }));
  };

  const handleClearLogs = () => {
    setLogs([]);
  };

  const handleNavigate = (screenId) => {
    setScreen(screenId);
  };

  return (
    <div className="h-screen w-screen flex overflow-hidden bg-[#070a12]">
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');
        
        * {
          font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        }

        @keyframes dot-pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }

        @keyframes pipe-flow {
          0% { background: linear-gradient(90deg, transparent, currentColor, transparent); background-size: 200% 100%; background-position: 200% 0; }
          100% { background-position: -200% 0; }
        }

        @keyframes fade-in {
          from { opacity: 0; }
          to { opacity: 1; }
        }

        @keyframes slide-up {
          from { transform: translateY(20px); opacity: 0; }
          to { transform: translateY(0); opacity: 1; }
        }

        @keyframes log-line-enter {
          from { opacity: 0; transform: translateX(-8px); }
          to { opacity: 1; transform: translateX(0); }
        }

        .animate-dot-pulse { animation: dot-pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite; }
        .pipe-flow { animation: pipe-flow 1.5s linear infinite; }
        .animate-fade-in { animation: fade-in 0.2s ease-out; }
        .animate-slide-up { animation: slide-up 0.3s ease-out; }
        .log-line-enter { animation: log-line-enter 0.3s ease-out; }

        .radar-sweep {
          animation: radar-spin 3s linear infinite;
          transform-origin: 18px 18px;
        }

        .radar-sweep-trail {
          animation: radar-spin 3s linear infinite;
          transform-origin: 18px 18px;
        }

        @keyframes radar-spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }

        .bg-grid {
          background-image: 
            linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px);
        }

        .sidebar-border {
          background: linear-gradient(180deg, rgba(0,212,255,0.3) 0%, rgba(0,212,255,0.05) 50%, transparent 100%);
        }

        .card-running {
          animation: card-pulse 1.5s ease-in-out infinite;
        }

        @keyframes card-pulse {
          0%, 100% { box-shadow: 0 0 0 0 rgba(0,212,255,0.2); }
          50% { box-shadow: 0 0 0 8px rgba(0,212,255,0); }
        }

        ::-webkit-scrollbar {
          width: 8px;
          height: 8px;
        }

        ::-webkit-scrollbar-track {
          background: transparent;
        }

        ::-webkit-scrollbar-thumb {
          background: rgba(255,255,255,0.1);
          border-radius: 4px;
        }

        ::-webkit-scrollbar-thumb:hover {
          background: rgba(255,255,255,0.2);
        }
      `}</style>

      <Sidebar screen={screen} setScreen={setScreen} auth={auth} currentPhase={summary.current_phase} onNewSession={() => {}} />

      <div className="flex-1 flex flex-col overflow-hidden">
        {screen === 'dashboard' && (
          <DashboardScreen
            summary={summary}
            moduleStates={moduleStates}
            onRunModule={handleRunModule}
            onRefresh={handleRefresh}
            activeJobId={activeJobId}
            onNavigate={handleNavigate}
          />
        )}
        {screen === 'github' && (
          <GithubIntelScreen
            data={{ github_audit: { overall_score: 82, bio_quality: 'excellent', top_languages: ['Python', 'JavaScript', 'TypeScript', 'Go', 'Rust'], summary: 'Strong profile with good project diversity' } }}
            moduleState={moduleStates.github}
            onRunModule={handleRunModule}
            activeJobId={activeJobId}
          />
        )}
        {screen === 'discovery' && (
          <JobDiscoveryScreen
            jobs={jobsData}
            moduleState={moduleStates.discovery}
            onRunModule={handleRunModule}
            activeJobId={activeJobId}
          />
        )}
        {screen === 'applications' && (
          <ApplicationsScreen
            apps={appsData}
            moduleState={moduleStates.application}
            onRunModule={handleRunModule}
            activeJobId={activeJobId}
          />
        )}
        {screen === 'offers' && (
          <OffersScreen
            offers={offersData}
            moduleState={moduleStates.offer}
            onRunModule={handleRunModule}
            activeJobId={activeJobId}
          />
        )}
        {screen === 'interview' && (
          <InterviewPrepScreen
            sessions={sessionsData}
            moduleState={moduleStates.prep}
            onOpenPrepModal={() => {}}
            activeJobId={activeJobId}
          />
        )}

        <LogPanel logs={logs} onClear={handleClearLogs} visible={true} />
      </div>
    </div>
  );
}
