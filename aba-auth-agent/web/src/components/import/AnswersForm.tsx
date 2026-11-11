import { addDays, format } from 'date-fns'
import { useState } from 'react'

import { DatePicker } from '@/components/DatePicker'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import type { Answers, Client, Payor, Question } from '@/lib/types'

export const NEW_CLIENT = '__new__'
const DEFAULT_PERIOD_DAYS = 182
const iso = (date: Date) => format(date, 'yyyy-MM-dd')

/** Only asks about what the report didn't say. */
export function AnswersForm({
  questions,
  clients,
  payors,
  busy,
  error,
  onSubmit,
}: {
  questions: Question[]
  clients: Client[]
  payors: Payor[]
  busy: boolean
  error: string | null
  onSubmit: (answers: Answers) => void
}) {
  const [clientChoice, setClientChoice] = useState(NEW_CLIENT)
  const [newIdentifier, setNewIdentifier] = useState('')
  const [payorKey, setPayorKey] = useState<string | undefined>(undefined)
  const [start, setStart] = useState<Date | undefined>(() => new Date())
  const [end, setEnd] = useState<Date | undefined>(() => addDays(new Date(), DEFAULT_PERIOD_DAYS))
  // The refusal shown last time stays up until the BCBA changes something, then clears
  const [dismissedError, setDismissedError] = useState<string | null>(null)
  const edited = <T,>(setter: (value: T) => void) => (value: T) => {
    setDismissedError(error)
    setter(value)
  }

  const askClient = questions.includes('client')
  const askPayor = questions.includes('payor')
  const askPeriod = questions.includes('period')
  // A payor is only needed when this would create a client; an existing client already has one.
  const creatingClient = !askClient || clientChoice === NEW_CLIENT

  function submit() {
    setDismissedError(null)
    const answers: Answers = {}
    if (askClient) {
      if (clientChoice === NEW_CLIENT) answers.new_identifier = newIdentifier.trim()
      else answers.existing_client_id = clientChoice
    }
    if (askPayor && creatingClient) answers.payor_key = payorKey
    if (askPeriod) {
      if (start) answers.period_start = iso(start)
      if (end) answers.period_end = iso(end)
    }
    onSubmit(answers)
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">A few things the report didn't say</CardTitle>
        <CardDescription>Everything else was read from the report.</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-5">
        {askClient && (
          <div className="grid gap-2">
            <Label htmlFor="client-choice">Which client is this report for?</Label>
            <Select value={clientChoice} onValueChange={edited(setClientChoice)}>
              <SelectTrigger id="client-choice" className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={NEW_CLIENT}>A new client</SelectItem>
                {clients.map((client) => (
                  <SelectItem key={client.id} value={client.id}>
                    {client.display_name}
                    {client.client_identifier ? ` (${client.client_identifier})` : ''}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {clientChoice === NEW_CLIENT && (
              <div className="grid gap-2">
                <Label htmlFor="new-identifier">New client ID</Label>
                <Input
                  id="new-identifier"
                  placeholder="CR-2024-0847"
                  value={newIdentifier}
                  onChange={(e) => edited(setNewIdentifier)(e.target.value)}
                />
              </div>
            )}
          </div>
        )}

        {askPayor && creatingClient && (
          <div className="grid gap-2">
            <Label htmlFor="payor">Payor</Label>
            <Select value={payorKey} onValueChange={edited(setPayorKey)}>
              <SelectTrigger id="payor" className="w-full">
                <SelectValue placeholder="Choose a payor" />
              </SelectTrigger>
              <SelectContent>
                {payors.map((payor) => (
                  <SelectItem key={payor.key} value={payor.key}>
                    {payor.display_name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        )}

        {askPeriod && (
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="grid gap-2">
              <Label htmlFor="period-start">Authorization period start</Label>
              <DatePicker id="period-start" label="Authorization period start" value={start} onChange={edited(setStart)} />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="period-end">Authorization period end</Label>
              <DatePicker id="period-end" label="Authorization period end" value={end} onChange={edited(setEnd)} />
            </div>
          </div>
        )}

        {error && error !== dismissedError && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
        <div>
          <Button onClick={submit} disabled={busy}>
            {busy ? 'Continuing…' : 'Continue'}
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
