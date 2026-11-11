import { Plus, Search } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router'

import { AddClientDialog } from '@/components/clients/AddClientDialog'
import { ArchiveClientDialog } from '@/components/clients/ArchiveClientDialog'
import { ClientDetailDialog } from '@/components/clients/ClientDetailDialog'
import { ClientsTable } from '@/components/clients/ClientsTable'
import { PageHeader } from '@/components/PageHeader'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { useClients } from '@/hooks/useClients'
import { useReference } from '@/hooks/useReference'
import { filterClients, nextSort, sortClients, type Sort } from '@/lib/clients'
import type { Client } from '@/lib/types'

export function Clients() {
  const navigate = useNavigate()
  const { clients, loading, error, reload } = useClients()
  const [query, setQuery] = useState('')
  // Most urgent authorization first: the clients who need a reauthorization soonest
  const [sort, setSort] = useState<Sort>({ key: 'deadline', dir: 'asc' })
  const [adding, setAdding] = useState(false)
  const [viewing, setViewing] = useState<Client | null>(null)
  const [archiving, setArchiving] = useState<Client | null>(null)
  const { payors } = useReference(adding)

  const visible = useMemo(() => sortClients(filterClients(clients, query), sort), [clients, query, sort])
  const goToImport = () => navigate('/import')

  const count = query.trim()
    ? `${visible.length} of ${clients.length} clients`
    : `${clients.length} active client${clients.length === 1 ? '' : 's'}`

  return (
    <>
      <PageHeader title="Clients" description="Your active client roster, with the authorization that needs attention next.">
        <div className="flex items-center gap-3">
          {!loading && !error && <Badge variant="secondary">{count}</Badge>}
          <Button onClick={() => setAdding(true)}>
            <Plus /> Add client
          </Button>
        </div>
      </PageHeader>

      {error && (
        <Alert variant="destructive" className="mb-4">
          <AlertDescription className="flex items-center justify-between gap-3">
            {error}
            <Button variant="outline" size="sm" onClick={() => void reload()}>
              Try again
            </Button>
          </AlertDescription>
        </Alert>
      )}

      {loading && (
        <div className="grid gap-2" aria-label="Loading clients">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
        </div>
      )}

      {!loading && !error && clients.length === 0 && (
        <Card>
          <CardHeader>
            <CardTitle>No clients yet</CardTitle>
            <CardDescription>Add a client, or import a progress report and the client is created from it.</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-3">
            <Button onClick={() => setAdding(true)}>Add client</Button>
            <Button variant="outline" onClick={goToImport}>
              Import a report
            </Button>
          </CardContent>
        </Card>
      )}

      {!loading && clients.length > 0 && (
        // minmax(0, 1fr) lets the table scroll sideways instead of stretching the page
        <div className="grid grid-cols-[minmax(0,1fr)] gap-4">
          <div className="relative">
            <Search className="pointer-events-none absolute top-2.5 left-3 size-4 text-muted-foreground" aria-hidden />
            <Input
              aria-label="Search clients"
              className="pl-9"
              placeholder="Search by name, ID, diagnosis or payor…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>
          {visible.length === 0 ? (
            <p className="py-8 text-center text-sm text-muted-foreground">No clients match “{query.trim()}”.</p>
          ) : (
            <ClientsTable
              clients={visible}
              sort={sort}
              onSort={(key) => setSort((current) => nextSort(current, key))}
              onOpen={setViewing}
              onImport={goToImport}
              onArchive={setArchiving}
            />
          )}
        </div>
      )}

      <AddClientDialog open={adding} onOpenChange={setAdding} payors={payors} onCreated={() => void reload()} />
      <ClientDetailDialog
        client={viewing}
        onClose={() => setViewing(null)}
        onImport={goToImport}
        onChanged={() => void reload()}
        onArchive={(client) => {
          setViewing(null)
          setArchiving(client)
        }}
      />
      <ArchiveClientDialog client={archiving} onClose={() => setArchiving(null)} onArchived={() => void reload()} />
    </>
  )
}
