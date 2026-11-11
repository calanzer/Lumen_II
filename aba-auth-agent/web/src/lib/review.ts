import type { Assessment, BehaviorTarget, HoursEntry, SkillTarget, TreatmentGoal } from '@/lib/types'

export const LOW_UTILIZATION_PCT = 80

export const blankAssessment = (): Assessment => ({
  assessment_type: 'Other',
  assessment_name: 'New assessment',
  date_administered: null,
  raw_score: null,
  standard_score: null,
  percentile: null,
  age_equivalent: null,
  domain_scores: {},
  previous_score: null,
  previous_date: null,
})

export const blankSkill = (): SkillTarget => ({
  domain: '',
  target_name: '',
  date_introduced: null,
  date_mastered: null,
  is_mastered: false,
  current_accuracy_pct: null,
  mastery_criterion_pct: 80,
  generalization_demonstrated: false,
  notes: null,
})

export const blankBehavior = (): BehaviorTarget => ({
  behavior_name: '',
  operational_definition: '',
  measurement_type: 'frequency',
  baseline_value: null,
  baseline_date: null,
  current_value: null,
  current_date: null,
  trend: null,
  unit: 'per hour',
  function_of_behavior: null,
  intervention_strategies: [],
})

export const blankHours = (): HoursEntry => ({
  cpt_code: '97153',
  authorized_units: 0,
  utilized_units: 0,
  utilization_pct: null,
  explanation_if_low: null,
})

export const blankGoal = (existing: TreatmentGoal[]): TreatmentGoal => ({
  goal_number: Math.max(0, ...existing.map((g) => g.goal_number)) + 1,
  goal_area: '',
  goal_statement: '',
  baseline_performance: null,
  current_performance: null,
  target_criterion: '',
  status: 'in progress',
  modification_rationale: null,
  related_targets: [],
})

/** Percent of authorized units used, to one decimal; null when nothing was authorized. */
export function utilizationPct(hours: Pick<HoursEntry, 'authorized_units' | 'utilized_units'>): number | null {
  if (!hours.authorized_units || hours.authorized_units <= 0) return null
  return Math.round((hours.utilized_units / hours.authorized_units) * 1000) / 10
}

/** How far a behavior has come down from baseline, as a percent; null unless it actually fell. */
export function reductionFromBaseline(b: Pick<BehaviorTarget, 'baseline_value' | 'current_value'>): number | null {
  if (!b.baseline_value || b.current_value === null || b.baseline_value <= 0) return null
  const reduction = (1 - b.current_value / b.baseline_value) * 100
  return reduction > 0 ? reduction : null
}

export const wordCount = (text: string) => text.split(/\s+/).filter(Boolean).length

export const TOO_BRIEF_WORDS = 50
export const TOO_LONG_WORDS = 400
