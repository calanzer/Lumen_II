// Mirrors the JSON the API returns (see api/imports.py and api/reference.py).

export type Stage = 'reading' | 'needs_answers' | 'setting_up' | 'drafting' | 'checking' | 'done' | 'error'

/** What the report didn't say, so the BCBA is asked. */
export type Question = 'client' | 'payor' | 'period'

export interface User {
  username: string
  name: string
  /** True when sign-in was skipped because the app is running on this machine. */
  local?: boolean
}

export interface Payor {
  key: string
  display_name: string
  subtitle: string
  has_custom_template: boolean
}

export type PeriodStatus = 'draft' | 'in_progress' | 'generated' | 'exported' | 'submitted'

export interface PeriodSummary {
  id: string
  period_start: string
  period_end: string
  status: PeriodStatus
  /** Negative once the authorization has ended. */
  days_until_end: number
  uploaded_filename: string | null
  has_data: boolean
  has_narrative: boolean
  exported_at: string | null
}

export interface Client {
  id: string
  display_name: string
  client_identifier: string | null
  payor: string
  payor_name: string
  diagnosis_codes: string[]
  period_count: number
  /** The most recent authorization period, the one to watch. */
  latest_period: PeriodSummary | null
}

export interface ClientDetail extends Client {
  periods: PeriodCard[]
  /** VB-MAPP domain scores across periods; null until two periods have them */
  trends: Trends | null
}

export interface NewClient {
  display_name: string
  client_identifier?: string
  diagnosis_codes: string[]
  payor: string
}

export interface DraftSummary {
  section_count: number
  sections_needing_review: number
  flags: string[]
  used_custom_template: boolean
}

export interface ImportResult {
  client_id: string
  period_id: string
  client: { display_name: string; identifier: string | null }
  client_created: boolean
  payor: { key: string; name: string }
  period: { start: string; end: string }
  notes: string[]
  completeness: number
  missing: string[]
  warnings: string[]
  draft: DraftSummary | null
  draft_error: string | null
  /** null means the automatic number check could not run */
  discrepancies: string[] | null
  check_error: string | null
}

export interface ImportJob {
  id: string
  filename: string
  stage: Stage
  questions: Question[]
  error: string | null
  result: ImportResult | null
}

export interface Answers {
  existing_client_id?: string
  new_identifier?: string
  payor_key?: string
  period_start?: string // YYYY-MM-DD
  period_end?: string
}

// ── Authorization period: extracted data, narrative, export (see api/periods.py) ──

/** A calendar date as the API sends it (YYYY-MM-DD), or null when the report didn't say. */
export type IsoDate = string | null

export const ASSESSMENT_TYPES = ['VB-MAPP', 'ABLLS-R', 'Vineland-3', 'PEAK', 'AFLS', 'Other'] as const
export type AssessmentType = (typeof ASSESSMENT_TYPES)[number]

export const CPT_CODES = ['97151', '97153', '97154', '97155', '97156', '97157', '0362T', '0373T', 'H0031', 'H0032', 'H2019', 'H2012', 'S5111'] as const
export type CptCode = (typeof CPT_CODES)[number]

export const BEHAVIOR_TRENDS = ['increasing', 'decreasing', 'stable', 'variable'] as const
export type BehaviorTrend = (typeof BEHAVIOR_TRENDS)[number]

export const MEASUREMENT_TYPES = ['frequency', 'duration', 'rate', 'interval', 'latency'] as const
export const GOAL_STATUSES = ['in progress', 'met', 'modified', 'discontinued'] as const

export interface ClientDemographics {
  client_id: string | null
  age_years: number | null
  diagnosis_codes: string[]
  diagnosis_descriptions: string[]
  auth_period_start: IsoDate
  auth_period_end: IsoDate
  supervising_bcba: string | null
  bcba_credential_number: string | null
  payor_name: string | null
  report_period_start: IsoDate
  report_period_end: IsoDate
}

export interface Assessment {
  assessment_type: AssessmentType
  assessment_name: string
  date_administered: IsoDate
  raw_score: number | null
  standard_score: number | null
  percentile: number | null
  age_equivalent: string | null
  domain_scores: Record<string, number>
  previous_score: number | null
  previous_date: IsoDate
}

export interface SkillTarget {
  domain: string
  target_name: string
  date_introduced: IsoDate
  date_mastered: IsoDate
  is_mastered: boolean
  current_accuracy_pct: number | null
  mastery_criterion_pct: number
  generalization_demonstrated: boolean
  notes: string | null
}

export interface BehaviorTarget {
  behavior_name: string
  operational_definition: string
  measurement_type: string
  baseline_value: number | null
  baseline_date: IsoDate
  current_value: number | null
  current_date: IsoDate
  trend: BehaviorTrend | null
  unit: string
  function_of_behavior: string | null
  intervention_strategies: string[]
}

export interface HoursEntry {
  cpt_code: CptCode
  authorized_units: number
  utilized_units: number
  utilization_pct: number | null
  explanation_if_low: string | null
}

export interface TreatmentGoal {
  goal_number: number
  goal_area: string
  goal_statement: string
  baseline_performance: string | null
  current_performance: string | null
  target_criterion: string
  status: string
  modification_rationale: string | null
  related_targets: string[]
}

export interface CaregiverTraining {
  total_sessions: number
  topics_covered: string[]
  caregiver_skill_acquisition: string | null
  barriers_to_participation: string | null
}

export interface DischargePlan {
  measurable_criteria: string[]
  estimated_discharge_date: IsoDate
  transition_plan: string | null
  current_discharge_readiness: string | null
}

export interface ClinicalData {
  source_filename: string
  extraction_timestamp: string
  extraction_model: string
  confidence_notes: string[]
  client: ClientDemographics
  assessments: Assessment[]
  skill_acquisition_targets: SkillTarget[]
  behavior_reduction_targets: BehaviorTarget[]
  hours_utilization: HoursEntry[]
  treatment_goals: TreatmentGoal[]
  caregiver_training: CaregiverTraining
  discharge_plan: DischargePlan
  requested_hours_by_code: Record<string, number>
  clinical_justification_for_hours: string | null
  missing_fields: string[]
}

export interface Validation {
  is_complete: boolean
  /** 0 to 1 */
  score: number
  missing: { description: string }[]
  warnings: string[]
}

export interface NarrativeSection {
  key: string
  title: string
  content: string
  requires_review: boolean
  review_note: string | null
  /** The extracted data this section was written from. */
  source: Record<string, unknown>
}

export interface Narrative {
  kind: 'default' | 'custom'
  payor_key: string | null
  template_name: string | null
  overall_confidence: number
  flags: string[]
  /** The data changed after this draft was written. */
  stale: boolean
  sections: NarrativeSection[]
}

export interface Comparison {
  prior_start: string
  prior_end: string
  skills_mastered_prior: number
  skills_mastered: number
  skill_targets: number
  behavior_targets: number
  behavior_changes: { name: string; prior: number; current: number; unit: string; percent_change: number }[]
}

export interface PeriodDetail {
  id: string
  period_start: string
  period_end: string
  status: PeriodStatus
  notes: string
  uploaded_filename: string | null
  extracted_at: string | null
  generated_at: string | null
  exported_at: string | null
  client: { id: string; display_name: string; client_identifier: string | null; payor: string; payor_name: string }
  data: ClinicalData | null
  validation: Validation | null
  narrative: Narrative | null
  template: { name: string; section_count: number } | null
  comparison: Comparison | null
}

export interface SavedData {
  data: ClinicalData
  validation: Validation
  narrative_stale: boolean
}

export type GenerationStage = 'idle' | 'drafting' | 'checking' | 'done' | 'error'

export interface GenerationStatus {
  stage: GenerationStage
  error: string | null
  /** null means the automatic number check could not run (see check_error) */
  discrepancies: string[] | null
  check_error: string | null
}

/** What the client details screen shows for one period (extends the roster fields). */
export interface PeriodCard extends PeriodSummary {
  notes: string
  extracted_at: string | null
  validation: { score: number; missing: number; warnings: number } | null
  counts: { assessments: number; skill_targets: number; behaviors: number; goals: number; hours_codes: number } | null
  narrative: { confidence: number; flags: number } | null
}

export interface Trends {
  /** One column per period, oldest first */
  columns: string[]
  rows: { domain: string; values: (number | null)[] }[]
}

export interface TemplateSection {
  title: string
  guidance: string
}

export interface TemplateDraft {
  source_filename: string | null
  style_notes: string
  sections: TemplateSection[]
}

export interface ActiveTemplate extends TemplateDraft {
  name: string
}

export interface TemplateInfo {
  payor: string
  payor_name: string
  active: ActiveTemplate | null
  default_sections: string[]
}
