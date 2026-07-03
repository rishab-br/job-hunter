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
  github_score?: number
  resume_score?: number
  ats_tailored_count?: number
  cover_letter_count?: number
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

export type SeniorityLevel = 'fresher' | 'junior' | 'mid' | 'senior' | 'lead'

export interface DiscoveryFilters {
  max_seniority: SeniorityLevel   // highest seniority level to show (inclusive)
  locations: string[]             // preferred cities; empty = no location filter
  remote_ok: boolean              // include remote jobs regardless of location filter
  min_score: number               // drop jobs scored below this (0 = no cut)
}

export const DEFAULT_FILTERS: DiscoveryFilters = {
  max_seniority: 'lead',
  locations: [],
  remote_ok: true,
  min_score: 0,
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

export type Screen = 'dashboard' | 'github' | 'resume-review' | 'discovery' | 'ats-modifier' | 'cover-letter' | 'applications' | 'offers' | 'interview' | 'autopilot'
export type ModalType = null | 'new-session' | 'offer' | 'prep'

// ── Resume Reviewer ───────────────────────────────────────────────────────────

export interface ResumeStrength  { point: string; detail: string }
export interface ResumeWeakness  { point: string; detail: string }
export interface MissingSkill    { skill: string; importance: 'critical' | 'important' | 'nice-to-have'; why: string }
export interface Recommendation  { action: string; impact: 'high' | 'medium' | 'low' }

export interface ResumeReview {
  overall_score: number
  score_rationale: string
  role_fit: 'strong' | 'moderate' | 'weak'
  format_quality: 'excellent' | 'good' | 'average' | 'poor'
  strengths: ResumeStrength[]
  weaknesses: ResumeWeakness[]
  missing_skills: MissingSkill[]
  ats_score: number
  ats_concerns: string[]
  market_alignment: string
  recommendations: Recommendation[]
}

// ── ATS Modifier ──────────────────────────────────────────────────────────────

export interface ATSChange { section: string; change: string }

export interface ATSModifiedResume {
  company: string
  job_title: string
  jd_excerpt: string
  tailored_resume: string
  ats_score_estimate: number
  keywords_matched: string[]
  keywords_added: string[]
  changes: ATSChange[]
  generated_at: string
}

// ── Cover Letter ──────────────────────────────────────────────────────────────

export interface CoverLetter {
  company: string
  job_title: string
  cover_letter: string
  key_points: string[]
  word_count: number | null
  tone: 'professional' | 'conversational' | 'enthusiastic'
  has_jd: boolean
  generated_at: string
}

// ── Autopilot ─────────────────────────────────────────────────────────────────

export interface AutopilotConfig {
  enabled: boolean
  at: string
  role: string
  niche: string
  market: string
  github_username: string
  filters: {
    max_seniority: SeniorityLevel
    locations: string[]
    remote_ok: boolean
    min_score: number
  }
}

export interface AutopilotLastRun {
  ran_at?: string
  total_scored?: number
  new_jobs?: number
  high_priority?: number
  digest_path?: string
  delivered?: { email?: boolean; telegram?: boolean }
  error?: string
}

export interface AutopilotStatus {
  config: AutopilotConfig
  last_run: AutopilotLastRun | null
  next_run: string | null
}
