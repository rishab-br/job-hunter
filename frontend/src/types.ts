export interface AuthState {
  userId: string
  username: string
  avatar: string
}

export interface Session {
  thread_id: string
  github_username: string
  target_role: string
  target_market: string
  target_niche: string
  current_phase: string
}

export interface DashboardSummary {
  jobs_found: number
  apps_submitted: number
  prep_sessions: number
  offers_received: number
  ghosted: number
  current_phase: string
  logs: string[]
  has_github_analysis?: boolean
  has_job_discovery?: boolean
  has_applying?: boolean
  has_tracking?: boolean
  has_offer_evaluation?: boolean
  has_interview_prep?: boolean
}

export interface GitHubAudit {
  overall_score: number
  bio_quality: string
  top_languages: string[]
  key_strengths: string[]
  immediate_red_flags: string[]
  summary: string
  repos_analyzed?: number
}

export interface GapAnalysis {
  gap_severity: 'high' | 'medium' | 'low'
  missing_critical_skills: string[]
  missing_project_types: { project_type: string; why_it_matters: string }[]
  profile_presentation_gaps: string[]
  summary: string
}

export interface ImprovementItem {
  priority: number
  title: string
  category: string
  effort: 'small' | 'medium' | 'large'
  impact: 'high' | 'medium' | 'low'
  description?: string
}

export interface GitHubIntelData {
  github_audit?: GitHubAudit
  gap_analysis?: GapAnalysis
  improvement_plan?: ImprovementItem[]
}

export interface Job {
  job_id: string
  company: string
  job_title: string
  relevance_score: number
  platform: 'LinkedIn' | 'Indeed' | 'Naukri'
  priority: 'high' | 'medium' | 'low'
  url: string
  location?: string
  salary_range?: string
}

export interface Application {
  job_id: string
  company: string
  job_title: string
  platform: string
  status: 'applied' | 'submitted' | 'viewed' | 'shortlisted' | 'interview_scheduled' | 'rejected' | 'offer'
  submitted_at: string
  url?: string
}

export interface OfferEvaluation {
  offer_id: string
  company: string
  job_title: string
  total_ctc?: string
  fair_value_range?: string
  offer_percentile?: string
  risk_level: 'high' | 'medium' | 'low'
  counter_ask?: string
  walk_away_floor?: string
  coaching_move?: 'accept' | 'counter_again' | 'decline' | 'request_time'
  script_path?: string
}

export interface PrepSession {
  session_id: string
  company: string
  role: string
  prep_date: string
  question_count: number
  technical_count?: number
  behavioral_count?: number
  system_design_count?: number
  company_specific_count?: number
  cheat_sheet_path?: string
  quick_card_path?: string
}

export interface LogEntry {
  id: number
  ts: string
  tag: string
  tagClass: string
  msg: string
  msgClass: string
  raw: string
}

export type ModuleStatus = 'idle' | 'running' | 'done' | 'warn' | 'error'

export interface ModuleState {
  status: ModuleStatus
  ts?: string
  metric?: string | number
}

export interface PendingApprovalJob {
  job_id: string
  job_title: string
  company: string
  platform: string
  job_url: string
  resume_path?: string
  cover_letter_path?: string
  cover_letter_content?: string
  form_screenshot_path?: string
  filled_fields?: Record<string, string>
}

export interface PendingApproval {
  awaiting: boolean
  message?: string
  job?: PendingApprovalJob
  remaining?: number
}

export type Screen = 'dashboard' | 'github' | 'discovery' | 'applications' | 'offers' | 'interview'
export type ModalType = null | 'new-session' | 'offer' | 'prep'
