import { useState, type FormEvent } from 'react'

import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { api } from '@/lib/api'
import type { Client, NewClient, Payor } from '@/lib/types'

/** "F84.0, F80.2" -> ["F84.0", "F80.2"] */
export function parseCodes(text: string): string[] {
  return text
    .split(/[,;\n]/)
    .map((code) => code.trim())
    .filter(Boolean)
}

export function AddClientDialog({
  open,
  onOpenChange,
  payors,
  onCreated,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  payors: Payor[]
  onCreated: (client: Client) => void
}) {
  const [name, setName] = useState('')
  const [identifier, setIdentifier] = useState('')
  const [codes, setCodes] = useState('')
  const [payor, setPayor] = useState<string | undefined>(undefined)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  function change(next: boolean) {
    if (!next) {
      setName('')
      setIdentifier('')
      setCodes('')
      setPayor(undefined)
      setError(null)
    }
    onOpenChange(next)
  }

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!name.trim()) return setError('Enter a name.')
    if (!payor) return setError('Choose a payor.')
    const client: NewClient = { display_name: name, diagnosis_codes: parseCodes(codes), payor }
    if (identifier.trim()) client.client_identifier = identifier
    setBusy(true)
    setError(null)
    try {
      const created = await api.createClient(client)
      change(false)
      onCreated(created)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not add the client.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={change}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add client</DialogTitle>
          <DialogDescription>You can also just import a report and the client is created from it.</DialogDescription>
        </DialogHeader>
        <form onSubmit={submit} className="grid gap-4">
          <div className="grid gap-2">
            <Label htmlFor="client-name">Name</Label>
            <Input id="client-name" placeholder="Martinez, A." value={name} onChange={(e) => setName(e.target.value)} autoFocus />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="client-identifier">Client ID</Label>
            <Input id="client-identifier" placeholder="CR-2024-0847" value={identifier} onChange={(e) => setIdentifier(e.target.value)} />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="client-codes">Diagnosis codes</Label>
            <Input id="client-codes" placeholder="F84.0, F80.2" value={codes} onChange={(e) => setCodes(e.target.value)} />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="client-payor">Payor</Label>
            <Select value={payor} onValueChange={setPayor}>
              <SelectTrigger id="client-payor" className="w-full">
                <SelectValue placeholder="Choose a payor" />
              </SelectTrigger>
              <SelectContent>
                {payors.map((p) => (
                  <SelectItem key={p.key} value={p.key}>
                    {p.display_name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          {error && (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => change(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={busy}>
              {busy ? 'Adding…' : 'Add client'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
