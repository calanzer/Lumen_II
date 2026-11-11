import type {
  Client,
  ClientDetail,
  ClinicalData,
  GenerationStatus,
  ImportJob,
  ImportResult,
  Narrative,
  Payor,
  PeriodCard,
  PeriodDetail,
  PeriodSummary,
  Validation,
} from '@/lib/types'

export const payors: Payor[] = [
  { key: 'aetna', display_name: 'Aetna', subtitle: 'Six-Criteria', has_custom_template: false },
  { key: 'optum', display_name: 'Optum / UnitedHealthcare', subtitle: 'Nine-Component', has_custom_template: true },
]

export function period(overrides: Partial<PeriodSummary> = {}): PeriodSummary {
  return {
    id: 'p1',
    period_start: '2026-01-01',
    period_end: '2026-06-30',
    status: 'in_progress',
    days_until_end: 40,
    uploaded_filename: 'report.docx',
    has_data: true,
    has_narrative: false,
    exported_at: null,
    ...overrides,
  }
}

export function client(overrides: Partial<Client> = {}): Client {
  return {
    id: 'c1',
    display_name: 'Sam W.',
    client_identifier: 'HB-1',
    payor: 'aetna',
    payor_name: 'Aetna',
    diagnosis_codes: ['F84.0'],
    period_count: 1,
    latest_period: period(),
    ...overrides,
  }
}

export const clients: Client[] = [client()]

export function result(overrides: Partial<ImportResult> = {}): ImportResult {
  return {
    client_id: 'c1',
    period_id: 'p1',
    client: { display_name: 'HB-2025-0311', identifier: 'HB-2025-0311' },
    client_created: true,
    payor: { key: 'aetna', name: 'Aetna' },
    period: { start: '2026-01-01', end: '2026-06-30' },
    notes: ['New client created: HB-2025-0311.'],
    completeness: 0.9,
    missing: [],
    warnings: ['CPT 97153: utilization is 58% with no explanation'],
    draft: { section_count: 9, sections_needing_review: 3, flags: ['Flag one', 'Flag two'], used_custom_template: false },
    draft_error: null,
    discrepancies: ['[S] Claim: x (value: 9) could not be traced'],
    check_error: null,
    ...overrides,
  }
}

export function job(stage: ImportJob['stage'], overrides: Partial<ImportJob> = {}): ImportJob {
  return {
    id: 'job1',
    filename: 'report.docx',
    stage,
    questions: [],
    error: null,
    result: stage === 'done' ? result() : null,
    ...overrides,
  }
}

// ── period screens ──


export function clinicalData(overrides: Partial<ClinicalData> = {}): ClinicalData {
  return {
    source_filename: 'report.docx',
    extraction_timestamp: '2026-01-02T00:00:00',
    extraction_model: 'claude-sonnet-5-5',
    confidence_notes: [],
    client: {
      client_id: 'HB-1',
      age_years: 4,
      diagnosis_codes: ['F84.0'],
      diagnosis_descriptions: ['Autism Spectrum Disorder'],
      auth_period_start: '2026-01-01',
      auth_period_end: '2026-06-30',
      supervising_bcba: 'Dr. Gonzalez',
      bcba_credential_number: '1-19-42831',
      payor_name: 'Aetna',
      report_period_start: null,
      report_period_end: null,
    },
    assessments: [
      {
        assessment_type: 'VB-MAPP',
        assessment_name: 'VB-MAPP Milestones',
        date_administered: '2026-01-10',
        raw_score: 80,
        standard_score: null,
        percentile: null,
        age_equivalent: '3y',
        domain_scores: { Mand: 6, Tact: 5 },
        previous_score: null,
        previous_date: null,
      },
    ],
    skill_acquisition_targets: [
      {
        domain: 'Manding',
        target_name: 'Mands for 20 items',
        date_introduced: '2026-01-05',
        date_mastered: null,
        is_mastered: false,
        current_accuracy_pct: 60,
        mastery_criterion_pct: 80,
        generalization_demonstrated: false,
        notes: null,
      },
      {
        domain: 'Tacting',
        target_name: 'Tacts 30 objects',
        date_introduced: null,
        date_mastered: '2026-03-01',
        is_mastered: true,
        current_accuracy_pct: 95,
        mastery_criterion_pct: 80,
        generalization_demonstrated: true,
        notes: null,
      },
    ],
    behavior_reduction_targets: [
      {
        behavior_name: 'Elopement',
        operational_definition: 'Leaving the area',
        measurement_type: 'frequency',
        baseline_value: 10,
        baseline_date: '2026-01-01',
        current_value: 4,
        current_date: '2026-06-01',
        trend: 'decreasing',
        unit: 'per week',
        function_of_behavior: null,
        intervention_strategies: ['NCR'],
      },
    ],
    hours_utilization: [{ cpt_code: '97153', authorized_units: 100, utilized_units: 58, utilization_pct: 58, explanation_if_low: null }],
    treatment_goals: [
      {
        goal_number: 1,
        goal_area: 'Communication',
        goal_statement: 'Mand for 20 items',
        baseline_performance: null,
        current_performance: null,
        target_criterion: '80% across 3 sessions',
        status: 'modified',
        modification_rationale: null,
        related_targets: [],
      },
    ],
    caregiver_training: { total_sessions: 6, topics_covered: ['Prompting'], caregiver_skill_acquisition: null, barriers_to_participation: null },
    discharge_plan: { measurable_criteria: ['Meets 80% of goals'], estimated_discharge_date: null, transition_plan: null, current_discharge_readiness: null },
    requested_hours_by_code: { '97153': 25 },
    clinical_justification_for_hours: 'Needs continued support.',
    missing_fields: [],
    ...overrides,
  }
}

export function validation(overrides: Partial<Validation> = {}): Validation {
  return { is_complete: true, score: 1, missing: [], warnings: [], ...overrides }
}

export function narrative(overrides: Partial<Narrative> = {}): Narrative {
  return {
    kind: 'default',
    payor_key: null,
    template_name: null,
    overall_confidence: 0.85,
    flags: ['Check the utilization explanation'],
    stale: false,
    sections: [
      {
        key: 'client_overview',
        title: 'Client Overview',
        content: 'Short overview of the client.',
        requires_review: false,
        review_note: null,
        source: { client: { client_id: 'HB-1' } },
      },
      {
        key: 'hours_justification',
        title: 'Hours Utilization & Justification',
        content: 'Hours were used. '.repeat(60),
        requires_review: true,
        review_note: 'Utilization is low.',
        source: { hours_utilization: [{ cpt_code: '97153' }] },
      },
    ],
    ...overrides,
  }
}

export function periodDetail(overrides: Partial<PeriodDetail> = {}): PeriodDetail {
  return {
    id: 'p1',
    period_start: '2026-01-01',
    period_end: '2026-06-30',
    status: 'generated',
    notes: '',
    uploaded_filename: 'report.docx',
    extracted_at: '2026-01-02T00:00:00',
    generated_at: '2026-01-03T00:00:00',
    exported_at: null,
    client: { id: 'c1', display_name: 'Sam W.', client_identifier: 'HB-1', payor: 'aetna', payor_name: 'Aetna' },
    data: clinicalData(),
    validation: validation(),
    narrative: narrative(),
    template: null,
    comparison: null,
    ...overrides,
  }
}

export function generation(overrides: Partial<GenerationStatus> = {}): GenerationStatus {
  return { stage: 'idle', error: null, discrepancies: null, check_error: null, ...overrides }
}

export function periodCard(overrides: Partial<PeriodCard> = {}): PeriodCard {
  return { ...period(), notes: '', extracted_at: '2026-01-02T00:00:00', validation: null, counts: null, narrative: null, ...overrides }
}

export function clientDetail(overrides: Partial<ClientDetail> = {}): ClientDetail {
  return { ...client(), periods: [], trends: null, ...overrides }
}
