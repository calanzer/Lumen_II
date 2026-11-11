import { useState } from 'react'

import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { api } from '@/lib/api'
import type { Client } from '@/lib/types'

export function ArchiveClientDialog({ client, onClose, onArchived }: { client: Client | null; onClose: () => void; onArchived: (client: Client) => void }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  function close() {
    setError(null)
    onClose()
  }

  async function confirm() {
    if (!client) return
    setBusy(true)
    setError(null)
    try {
      await api.archiveClient(client.id)
      onArchived(client)
      close()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not archive the client.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Dialog open={client !== null} onOpenChange={(open) => !open && close()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Archive {client?.display_name}?</DialogTitle>
          <DialogDescription>They'll be removed from the active roster. Their reports and drafts are kept.</DialogDescription>
        </DialogHeader>
        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
        <DialogFooter>
          <Button variant="outline" onClick={close}>
            Cancel
          </Button>
          <Button variant="destructive" onClick={() => void confirm()} disabled={busy}>
            {busy ? 'Archiving…' : 'Archive'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
