import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import {
  CheckField,
  DateField,
  LinesField,
  NumberField,
  RequiredTextAreaField,
  RequiredTextField,
  SelectField,
  TextAreaField,
  TextField,
} from '@/components/fields'
import { grid2, grid3, grid4, ItemList, SectionCard, type SectionProps } from '@/components/review/ReviewSection'
import {
  blankAssessment,
  blankBehavior,
  blankGoal,
  blankHours,
  blankSkill,
  LOW_UTILIZATION_PCT,
  reductionFromBaseline,
  utilizationPct,
} from '@/lib/review'
import { ASSESSMENT_TYPES, BEHAVIOR_TRENDS, CPT_CODES, GOAL_STATUSES, MEASUREMENT_TYPES } from '@/lib/types'

const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? '' : 's'}`

export function Demographics({ data, update }: SectionProps) {
  const client = data.client
  return (
    <SectionCard number={1} title="Client demographics">
      <div className="grid gap-4">
        <div className={grid2}>
          <TextField label="Client ID" value={client.client_id} onChange={(v) => update((d) => void (d.client.client_id = v))} />
          <NumberField
            label="Age (years)"
            value={client.age_years}
            min={0}
            max={99}
            onChange={(v) => update((d) => void (d.client.age_years = v))}
          />
          <TextField
            label="Supervising BCBA"
            value={client.supervising_bcba}
            onChange={(v) => update((d) => void (d.client.supervising_bcba = v))}
          />
          <TextField
            label="BCBA credential #"
            value={client.bcba_credential_number}
            onChange={(v) => update((d) => void (d.client.bcba_credential_number = v))}
          />
          <DateField
            label="Authorization period start"
            value={client.auth_period_start}
            onChange={(v) => update((d) => void (d.client.auth_period_start = v))}
          />
          <DateField
            label="Authorization period end"
            value={client.auth_period_end}
            onChange={(v) => update((d) => void (d.client.auth_period_end = v))}
          />
        </div>
        <LinesField
          label="Diagnosis codes"
          rows={2}
          hint="One per line, e.g. F84.0"
          value={client.diagnosis_codes}
          onChange={(v) => update((d) => void (d.client.diagnosis_codes = v))}
        />
        <LinesField
          label="Diagnosis descriptions"
          value={client.diagnosis_descriptions}
          onChange={(v) => update((d) => void (d.client.diagnosis_descriptions = v))}
        />
      </div>
    </SectionCard>
  )
}

export function Assessments({ data, update }: SectionProps) {
  return (
    <SectionCard number={2} title="Assessments" summary={`${data.assessments.length} found`}>
      <ItemList
        items={data.assessments}
        noun="assessment"
        empty="No assessments were found in the report."
        title={(a) => `${a.assessment_type}: ${a.assessment_name || 'Untitled'}`}
        onAdd={() => update((d) => void d.assessments.push(blankAssessment()))}
        onRemove={(i) => update((d) => void d.assessments.splice(i, 1))}
        render={(a, i) => (
          <>
            <div className={grid3}>
              <SelectField
                label="Type"
                value={a.assessment_type}
                options={ASSESSMENT_TYPES}
                onChange={(v) => update((d) => void (d.assessments[i].assessment_type = v))}
              />
              <RequiredTextField
                label="Name"
                value={a.assessment_name}
                onChange={(v) => update((d) => void (d.assessments[i].assessment_name = v))}
              />
              <DateField
                label="Date administered"
                value={a.date_administered}
                onChange={(v) => update((d) => void (d.assessments[i].date_administered = v))}
              />
            </div>
            <div className={grid4}>
              <NumberField
                label="Raw score"
                placeholder="Not assessed"
                value={a.raw_score}
                onChange={(v) => update((d) => void (d.assessments[i].raw_score = v))}
              />
              <NumberField
                label="Standard score"
                placeholder="Not assessed"
                value={a.standard_score}
                onChange={(v) => update((d) => void (d.assessments[i].standard_score = v))}
              />
              <NumberField
                label="Percentile"
                placeholder="Not assessed"
                value={a.percentile}
                onChange={(v) => update((d) => void (d.assessments[i].percentile = v))}
              />
              <TextField
                label="Age equivalent"
                value={a.age_equivalent}
                onChange={(v) => update((d) => void (d.assessments[i].age_equivalent = v))}
              />
            </div>
            {Object.keys(a.domain_scores).length > 0 && (
              <div className="grid gap-2">
                <p className="text-sm font-medium">Domain scores</p>
                <div className={grid4}>
                  {Object.entries(a.domain_scores).map(([domain, score]) => (
                    <NumberField
                      key={domain}
                      label={domain}
                      value={score}
                      allowEmpty={false}
                      onChange={(v) => update((d) => void (v !== null && (d.assessments[i].domain_scores[domain] = v)))}
                    />
                  ))}
                </div>
              </div>
            )}
            <div className={grid2}>
              <NumberField
                label="Previous score"
                placeholder="Not assessed"
                value={a.previous_score}
                onChange={(v) => update((d) => void (d.assessments[i].previous_score = v))}
              />
              <DateField
                label="Previous date"
                value={a.previous_date}
                onChange={(v) => update((d) => void (d.assessments[i].previous_date = v))}
              />
            </div>
          </>
        )}
      />
    </SectionCard>
  )
}

export function Skills({ data, update }: SectionProps) {
  const mastered = data.skill_acquisition_targets.filter((t) => t.is_mastered).length
  return (
    <SectionCard
      number={3}
      title="Skill acquisition targets"
      summary={`${mastered}/${data.skill_acquisition_targets.length} mastered`}
    >
      <ItemList
        items={data.skill_acquisition_targets}
        noun="skill target"
        empty="No skill targets were found in the report."
        title={(t) => `${t.is_mastered ? '✓' : '○'} ${t.domain || 'No domain'}: ${t.target_name || 'Unnamed target'}`}
        onAdd={() => update((d) => void d.skill_acquisition_targets.push(blankSkill()))}
        onRemove={(i) => update((d) => void d.skill_acquisition_targets.splice(i, 1))}
        render={(t, i) => (
          <>
            <div className={grid2}>
              <RequiredTextField
                label="Domain"
                value={t.domain}
                onChange={(v) => update((d) => void (d.skill_acquisition_targets[i].domain = v))}
              />
              <RequiredTextField
                label="Target name"
                value={t.target_name}
                onChange={(v) => update((d) => void (d.skill_acquisition_targets[i].target_name = v))}
              />
              <DateField
                label="Date introduced"
                value={t.date_introduced}
                onChange={(v) => update((d) => void (d.skill_acquisition_targets[i].date_introduced = v))}
              />
              <NumberField
                label="Current accuracy %"
                min={0}
                max={100}
                value={t.current_accuracy_pct}
                onChange={(v) => update((d) => void (d.skill_acquisition_targets[i].current_accuracy_pct = v))}
              />
              <NumberField
                label="Mastery criterion %"
                min={0}
                max={100}
                allowEmpty={false}
                value={t.mastery_criterion_pct}
                onChange={(v) => update((d) => void (v !== null && (d.skill_acquisition_targets[i].mastery_criterion_pct = v)))}
              />
              {t.is_mastered && (
                <DateField
                  label="Date mastered"
                  value={t.date_mastered}
                  onChange={(v) => update((d) => void (d.skill_acquisition_targets[i].date_mastered = v))}
                />
              )}
            </div>
            <div className="flex flex-wrap gap-6">
              <CheckField
                label="Mastered"
                checked={t.is_mastered}
                onChange={(v) =>
                  update((d) => {
                    d.skill_acquisition_targets[i].is_mastered = v
                    if (!v) d.skill_acquisition_targets[i].date_mastered = null
                  })
                }
              />
              <CheckField
                label="Generalization demonstrated"
                checked={t.generalization_demonstrated}
                onChange={(v) => update((d) => void (d.skill_acquisition_targets[i].generalization_demonstrated = v))}
              />
            </div>
            <TextAreaField
              label="Notes"
              value={t.notes}
              onChange={(v) => update((d) => void (d.skill_acquisition_targets[i].notes = v))}
            />
          </>
        )}
      />
    </SectionCard>
  )
}

export function Behaviors({ data, update }: SectionProps) {
  return (
    <SectionCard number={4} title="Behavior reduction targets" summary={`${data.behavior_reduction_targets.length} tracked`}>
      <ItemList
        items={data.behavior_reduction_targets}
        noun="behavior target"
        empty="No behavior targets were found in the report."
        title={(b) => `[${b.trend ?? '—'}] ${b.behavior_name || 'Unnamed behavior'}`}
        onAdd={() => update((d) => void d.behavior_reduction_targets.push(blankBehavior()))}
        onRemove={(i) => update((d) => void d.behavior_reduction_targets.splice(i, 1))}
        render={(b, i) => {
          const reduction = reductionFromBaseline(b)
          return (
            <>
              <div className={grid2}>
                <RequiredTextField
                  label="Behavior name"
                  value={b.behavior_name}
                  onChange={(v) => update((d) => void (d.behavior_reduction_targets[i].behavior_name = v))}
                />
                <SelectField
                  label="Measurement type"
                  value={b.measurement_type as (typeof MEASUREMENT_TYPES)[number]}
                  options={MEASUREMENT_TYPES}
                  onChange={(v) => update((d) => void (d.behavior_reduction_targets[i].measurement_type = v))}
                />
                <RequiredTextField
                  label="Unit"
                  value={b.unit}
                  onChange={(v) => update((d) => void (d.behavior_reduction_targets[i].unit = v))}
                />
                <SelectField
                  label="Trend"
                  value={b.trend}
                  options={BEHAVIOR_TRENDS}
                  placeholder="Not determined"
                  onChange={(v) => update((d) => void (d.behavior_reduction_targets[i].trend = v))}
                />
                <NumberField
                  label="Baseline value"
                  value={b.baseline_value}
                  onChange={(v) => update((d) => void (d.behavior_reduction_targets[i].baseline_value = v))}
                />
                <DateField
                  label="Baseline date"
                  value={b.baseline_date}
                  onChange={(v) => update((d) => void (d.behavior_reduction_targets[i].baseline_date = v))}
                />
                <NumberField
                  label="Current value"
                  value={b.current_value}
                  onChange={(v) => update((d) => void (d.behavior_reduction_targets[i].current_value = v))}
                />
                <DateField
                  label="Current date"
                  value={b.current_date}
                  onChange={(v) => update((d) => void (d.behavior_reduction_targets[i].current_date = v))}
                />
              </div>
              {reduction !== null && (
                <p>
                  <Badge className="bg-success/15 text-success">Reduction from baseline: {reduction.toFixed(0)}%</Badge>
                </p>
              )}
              <RequiredTextAreaField
                label="Operational definition"
                rows={4}
                value={b.operational_definition}
                onChange={(v) => update((d) => void (d.behavior_reduction_targets[i].operational_definition = v))}
              />
              <TextField
                label="Function of behavior"
                value={b.function_of_behavior}
                onChange={(v) => update((d) => void (d.behavior_reduction_targets[i].function_of_behavior = v))}
              />
              <LinesField
                label="Intervention strategies"
                rows={4}
                value={b.intervention_strategies}
                onChange={(v) => update((d) => void (d.behavior_reduction_targets[i].intervention_strategies = v))}
              />
            </>
          )
        }}
      />
    </SectionCard>
  )
}

export function Hours({ data, update }: SectionProps) {
  return (
    <SectionCard number={5} title="Hours utilization" summary={plural(data.hours_utilization.length, 'code')}>
      <ItemList
        items={data.hours_utilization}
        noun="hours entry"
        empty="No hours were found in the report."
        title={(h) => {
          const pct = h.utilization_pct ?? utilizationPct(h)
          return `${h.cpt_code} — ${h.utilized_units}/${h.authorized_units} units${pct === null ? '' : ` (${pct.toFixed(0)}%)`}`
        }}
        onAdd={() => update((d) => void d.hours_utilization.push(blankHours()))}
        onRemove={(i) => update((d) => void d.hours_utilization.splice(i, 1))}
        render={(h, i) => {
          const pct = utilizationPct(h)
          const low = pct !== null && pct < LOW_UTILIZATION_PCT
          return (
            <>
              <div className={grid3}>
                <SelectField
                  label="CPT code"
                  value={h.cpt_code}
                  options={CPT_CODES}
                  onChange={(v) => update((d) => void (d.hours_utilization[i].cpt_code = v))}
                />
                <NumberField
                  label="Authorized units"
                  min={0}
                  allowEmpty={false}
                  value={h.authorized_units}
                  onChange={(v) =>
                    update((d) => {
                      if (v === null) return
                      d.hours_utilization[i].authorized_units = v
                      d.hours_utilization[i].utilization_pct = utilizationPct(d.hours_utilization[i])
                    })
                  }
                />
                <NumberField
                  label="Utilized units"
                  min={0}
                  allowEmpty={false}
                  value={h.utilized_units}
                  onChange={(v) =>
                    update((d) => {
                      if (v === null) return
                      d.hours_utilization[i].utilized_units = v
                      d.hours_utilization[i].utilization_pct = utilizationPct(d.hours_utilization[i])
                    })
                  }
                />
              </div>
              {pct !== null && (
                <div className="grid gap-1.5">
                  <p className="text-sm">
                    <strong>Utilization:</strong> {pct}%
                  </p>
                  <Progress value={Math.min(pct, 100)} aria-label="Utilization" />
                </div>
              )}
              {(low || h.explanation_if_low) && (
                <TextAreaField
                  label={low ? `Explanation for low utilization (expected below ${LOW_UTILIZATION_PCT}%)` : 'Explanation (optional)'}
                  value={h.explanation_if_low}
                  onChange={(v) => update((d) => void (d.hours_utilization[i].explanation_if_low = v))}
                />
              )}
              {low && !h.explanation_if_low && (
                <Alert>
                  <AlertDescription>The payor may require an explanation for utilization below {LOW_UTILIZATION_PCT}%.</AlertDescription>
                </Alert>
              )}
            </>
          )
        }}
      />
    </SectionCard>
  )
}

export function Goals({ data, update }: SectionProps) {
  return (
    <SectionCard number={6} title="Treatment goals" summary={plural(data.treatment_goals.length, 'goal')}>
      <ItemList
        items={data.treatment_goals}
        noun="treatment goal"
        empty="No treatment goals were found in the report."
        title={(g) => `Goal ${g.goal_number}: ${g.goal_area || 'No area'} — ${g.status}`}
        onAdd={() => update((d) => void d.treatment_goals.push(blankGoal(d.treatment_goals)))}
        onRemove={(i) => update((d) => void d.treatment_goals.splice(i, 1))}
        render={(g, i) => (
          <>
            <div className={grid3}>
              <NumberField
                label="Goal #"
                min={1}
                allowEmpty={false}
                value={g.goal_number}
                onChange={(v) => update((d) => void (v !== null && (d.treatment_goals[i].goal_number = v)))}
              />
              <RequiredTextField
                label="Goal area"
                value={g.goal_area}
                onChange={(v) => update((d) => void (d.treatment_goals[i].goal_area = v))}
              />
              <SelectField
                label="Status"
                value={g.status as (typeof GOAL_STATUSES)[number]}
                options={GOAL_STATUSES}
                onChange={(v) => update((d) => void (d.treatment_goals[i].status = v))}
              />
            </div>
            <RequiredTextAreaField
              label="Goal statement"
              value={g.goal_statement}
              onChange={(v) => update((d) => void (d.treatment_goals[i].goal_statement = v))}
            />
            <TextAreaField
              label="Baseline performance"
              rows={2}
              value={g.baseline_performance}
              onChange={(v) => update((d) => void (d.treatment_goals[i].baseline_performance = v))}
            />
            <TextAreaField
              label="Current performance"
              rows={2}
              value={g.current_performance}
              onChange={(v) => update((d) => void (d.treatment_goals[i].current_performance = v))}
            />
            <RequiredTextField
              label="Target criterion"
              value={g.target_criterion}
              onChange={(v) => update((d) => void (d.treatment_goals[i].target_criterion = v))}
            />
            {(g.status === 'modified' || g.status === 'discontinued') && (
              <>
                <TextAreaField
                  label="Modification rationale (required)"
                  value={g.modification_rationale}
                  onChange={(v) => update((d) => void (d.treatment_goals[i].modification_rationale = v))}
                />
                {!g.modification_rationale && (
                  <Alert>
                    <AlertDescription>A rationale is required for modified or discontinued goals.</AlertDescription>
                  </Alert>
                )}
              </>
            )}
          </>
        )}
      />
    </SectionCard>
  )
}

export function Caregiver({ data, update }: SectionProps) {
  const training = data.caregiver_training
  return (
    <SectionCard number={7} title="Caregiver training">
      <div className="grid gap-4">
        <NumberField
          label="Total sessions"
          min={0}
          allowEmpty={false}
          className="sm:max-w-48"
          value={training.total_sessions}
          onChange={(v) => update((d) => void (v !== null && (d.caregiver_training.total_sessions = v)))}
        />
        <LinesField
          label="Topics covered"
          rows={4}
          value={training.topics_covered}
          onChange={(v) => update((d) => void (d.caregiver_training.topics_covered = v))}
        />
        <TextAreaField
          label="Caregiver skill acquisition"
          value={training.caregiver_skill_acquisition}
          onChange={(v) => update((d) => void (d.caregiver_training.caregiver_skill_acquisition = v))}
        />
        <TextAreaField
          label="Barriers to participation"
          value={training.barriers_to_participation}
          onChange={(v) => update((d) => void (d.caregiver_training.barriers_to_participation = v))}
        />
      </div>
    </SectionCard>
  )
}

export function Discharge({ data, update }: SectionProps) {
  const plan = data.discharge_plan
  return (
    <SectionCard number={8} title="Discharge plan">
      <div className="grid gap-4">
        <LinesField
          label="Measurable discharge criteria"
          rows={4}
          value={plan.measurable_criteria}
          onChange={(v) => update((d) => void (d.discharge_plan.measurable_criteria = v))}
        />
        <DateField
          label="Estimated discharge date"
          className="sm:max-w-64"
          value={plan.estimated_discharge_date}
          onChange={(v) => update((d) => void (d.discharge_plan.estimated_discharge_date = v))}
        />
        <TextAreaField
          label="Transition plan"
          value={plan.transition_plan}
          onChange={(v) => update((d) => void (d.discharge_plan.transition_plan = v))}
        />
        <TextAreaField
          label="Current discharge readiness"
          value={plan.current_discharge_readiness}
          onChange={(v) => update((d) => void (d.discharge_plan.current_discharge_readiness = v))}
        />
      </div>
    </SectionCard>
  )
}

export function RequestedHours({ data, update }: SectionProps) {
  const codes = Object.entries(data.requested_hours_by_code)
  return (
    <SectionCard number={9} title="Requested hours for next authorization">
      <div className="grid gap-4">
        {codes.length > 0 && (
          <div className={grid4}>
            {codes.map(([code, units]) => (
              <NumberField
                key={code}
                label={`${code} (weekly units)`}
                min={0}
                allowEmpty={false}
                value={units}
                onChange={(v) => update((d) => void (v !== null && (d.requested_hours_by_code[code] = v)))}
              />
            ))}
          </div>
        )}
        <TextAreaField
          label="Clinical justification for requested hours"
          rows={5}
          value={data.clinical_justification_for_hours}
          onChange={(v) => update((d) => void (d.clinical_justification_for_hours = v))}
        />
      </div>
    </SectionCard>
  )
}
