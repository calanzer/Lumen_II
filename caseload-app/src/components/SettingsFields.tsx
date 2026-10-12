import type { ServiceTypeDraft } from "../db/defaults";
import type { DeliveredBy, Settings } from "../db/types";

export type EditableServiceType = ServiceTypeDraft & { id?: string };

export function ServiceTypesEditor({
  value,
  onChange,
}: {
  value: EditableServiceType[];
  onChange: (v: EditableServiceType[]) => void;
}) {
  const patch = (i: number, p: Partial<EditableServiceType>) =>
    onChange(value.map((row, j) => (j === i ? { ...row, ...p } : row)));
  return (
    <div>
      <div className="table-wrap">
        <table className="data">
          <thead>
            <tr>
              <th scope="col">Code</th>
              <th scope="col">Label</th>
              <th scope="col">Minutes per unit</th>
              <th scope="col">Delivered by</th>
              <th scope="col">Technician direct hours</th>
              <th scope="col">Supervision</th>
              <th scope="col">
                <span className="sr-only">Remove</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {value.map((st, i) => (
              <tr key={st.id ?? i}>
                <td>
                  <input aria-label={`Code, row ${i + 1}`} type="text" value={st.code} style={{ width: 80 }} onChange={(e) => patch(i, { code: e.target.value })} />
                </td>
                <td>
                  <input aria-label={`Label, row ${i + 1}`} type="text" value={st.label} style={{ width: "100%", minWidth: 160 }} onChange={(e) => patch(i, { label: e.target.value })} />
                </td>
                <td>
                  <input
                    aria-label={`Minutes per unit, row ${i + 1}`}
                    type="number"
                    min={1}
                    value={st.minutesPerUnit}
                    style={{ width: 70 }}
                    onChange={(e) => patch(i, { minutesPerUnit: Number(e.target.value) || 15 })}
                  />
                </td>
                <td>
                  <select aria-label={`Delivered by, row ${i + 1}`} value={st.deliveredBy} onChange={(e) => patch(i, { deliveredBy: e.target.value as DeliveredBy })}>
                    <option value="BCBA">BCBA</option>
                    <option value="RBT">Technician</option>
                    <option value="either">Either</option>
                  </select>
                </td>
                <td>
                  <input
                    aria-label={`${st.code || "Row " + (i + 1)} counts as technician direct hours`}
                    type="checkbox"
                    checked={st.countsAsRbtDirect}
                    onChange={(e) => patch(i, { countsAsRbtDirect: e.target.checked })}
                  />
                </td>
                <td>
                  <input
                    aria-label={`${st.code || "Row " + (i + 1)} counts as supervision`}
                    type="checkbox"
                    checked={st.countsAsSupervision}
                    onChange={(e) => patch(i, { countsAsSupervision: e.target.checked })}
                  />
                </td>
                <td>
                  <button className="btn btn-danger" onClick={() => onChange(value.filter((_, j) => j !== i))} aria-label={`Remove ${st.code || "row " + (i + 1)}`}>
                    Remove
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <button
        className="btn"
        style={{ marginTop: 8 }}
        onClick={() =>
          onChange([...value, { code: "", label: "", minutesPerUnit: 15, countsAsRbtDirect: false, countsAsSupervision: false, deliveredBy: "either" }])
        }
      >
        + Add service type
      </button>
    </div>
  );
}

function NumberField({
  id,
  label,
  hint,
  value,
  onChange,
  min = 0,
  step = 1,
  suffix,
}: {
  id: string;
  label: string;
  hint?: string;
  value: number;
  onChange: (n: number) => void;
  min?: number;
  step?: number;
  suffix?: string;
}) {
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <div className="row">
        <input id={id} type="number" min={min} step={step} value={value} style={{ width: 100 }} onChange={(e) => onChange(Number(e.target.value))} />
        {suffix && <span className="muted">{suffix}</span>}
      </div>
      {hint && <span className="hint">{hint}</span>}
    </div>
  );
}

export function ThresholdFields({ value, onChange }: { value: Settings; onChange: (p: Partial<Settings>) => void }) {
  const pct = (x: number) => Math.round(x * 1000) / 10;
  return (
    <div className="grid-2">
      <div>
        <h3>Pacing</h3>
        <NumberField id="pace-green" label="Green when pace is at least" suffix="%" value={pct(value.paceGreenAt)} onChange={(n) => onChange({ paceGreenAt: n / 100 })} hint="Pace = delivered hours ÷ hours expected by today." />
        <NumberField id="pace-yellow" label="Yellow when pace is at least" suffix="% (below this is red)" value={pct(value.paceYellowAt)} onChange={(n) => onChange({ paceYellowAt: n / 100 })} />
        <NumberField id="not-seen" label="Flag a client as not seen after" suffix="days without a completed BCBA session" value={value.notSeenDays} onChange={(n) => onChange({ notSeenDays: n })} />
        <NumberField id="reassess-lead" label="Reassessment due" suffix="days before an authorization ends" value={value.reassessmentLeadDays} onChange={(n) => onChange({ reassessmentLeadDays: n })} />
      </div>
      <div>
        <h3>Supervision</h3>
        <NumberField id="sup-target" label="Supervision target" suffix="% of technician direct hours" step={0.5} value={value.supervisionTargetPercent} onChange={(n) => onChange({ supervisionTargetPercent: n })} hint="Rules vary by credentialing body, insurer and employer. Set yours here." />
        <NumberField id="sup-contacts" label="Minimum supervision contacts" suffix="per technician per month" value={value.minContactsPerMonth} onChange={(n) => onChange({ minContactsPerMonth: n })} />
        <NumberField id="sup-obs" label="Minimum observations" suffix="per technician per month" value={value.minObservationsPerMonth} onChange={(n) => onChange({ minObservationsPerMonth: n })} />
        <div className="field">
          <label htmlFor="week-start">Week starts on</label>
          <select id="week-start" value={value.weekStartsOn} onChange={(e) => onChange({ weekStartsOn: Number(e.target.value) as 0 | 1 })} style={{ width: 160 }}>
            <option value={1}>Monday</option>
            <option value={0}>Sunday</option>
          </select>
        </div>
      </div>
    </div>
  );
}
