import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { AnswersForm } from '@/components/import/AnswersForm'
import { Dropzone } from '@/components/import/Dropzone'
import { ImportResultView } from '@/components/import/ImportResultView'
import { StageProgress } from '@/components/import/StageProgress'
import { PageHeader } from '@/components/PageHeader'
import { useImportJob } from '@/hooks/useImportJob'
import { useReference } from '@/hooks/useReference'

export function Import() {
  const { job, error, busy, start, answer, reset } = useImportJob()
  const { payors, clients } = useReference(job?.stage === 'needs_answers')

  return (
    <>
      <PageHeader title="Import a report" description="Drop in a progress report. Everything else happens automatically." />

      {!job && (
        <div className="grid gap-4">
          <Dropzone onFile={(file) => void start(file)} disabled={busy} />
          {error && (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
          <p className="text-sm text-muted-foreground">
            The client, payor and authorization period are read from the report, and you'll only be asked about anything it doesn't say.
          </p>
        </div>
      )}

      {job && job.stage === 'error' && (
        <div className="grid gap-4">
          <Alert variant="destructive">
            <AlertTitle>Couldn't read that report</AlertTitle>
            <AlertDescription>{job.error}</AlertDescription>
          </Alert>
          <div>
            <Button variant="outline" onClick={reset}>
              Try another report
            </Button>
          </div>
        </div>
      )}

      {job && job.stage === 'needs_answers' && (
        <AnswersForm questions={job.questions} clients={clients} payors={payors} busy={busy} error={error} onSubmit={(answers) => void answer(answers)} />
      )}

      {job && ['reading', 'setting_up', 'drafting', 'checking'].includes(job.stage) && (
        <div className="grid gap-4">
          <StageProgress stage={job.stage} filename={job.filename} />
          {error && (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
        </div>
      )}

      {job && job.stage === 'done' && job.result && <ImportResultView result={job.result} filename={job.filename} onAnother={reset} />}
    </>
  )
}
