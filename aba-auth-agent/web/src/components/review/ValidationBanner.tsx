import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Progress } from '@/components/ui/progress'
import type { Validation } from '@/lib/types'

export function ValidationBanner({ validation }: { validation: Validation }) {
  const percent = Math.round(validation.score * 100)
  const missing = validation.missing.length
  return (
    <div className="grid gap-3">
      <Alert className={validation.is_complete ? 'border-success/40 bg-success/10' : 'border-warning/50 bg-warning/10'}>
        <AlertTitle>Data completeness: {percent}%</AlertTitle>
        <AlertDescription className="grid gap-2">
          <span>
            {validation.is_complete
              ? 'All required fields were found.'
              : `${missing} required ${missing === 1 ? 'field is' : 'fields are'} missing. Fill them in below.`}
          </span>
          <Progress value={percent} aria-label="Completeness" />
        </AlertDescription>
      </Alert>
      {!validation.is_complete && (
        <ul className="list-disc pl-6 text-sm" aria-label="Missing fields">
          {validation.missing.map((item) => (
            <li key={item.description}>{item.description}</li>
          ))}
        </ul>
      )}
      {validation.warnings.length > 0 && (
        <details className="rounded-md border px-4 py-2 text-sm">
          <summary className="cursor-pointer font-medium">
            {validation.warnings.length} {validation.warnings.length === 1 ? 'warning' : 'warnings'}
          </summary>
          <ul className="mt-2 list-disc pl-6">
            {validation.warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </details>
      )}
    </div>
  )
}
