import { ArrowDown, ArrowUp, ArrowUpDown, MoreHorizontal } from 'lucide-react'

import { DeadlineBadge } from '@/components/clients/DeadlineBadge'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Table, TableBody, TableCaption, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import type { Sort, SortKey } from '@/lib/clients'
import { formatDate } from '@/lib/deadlines'
import type { Client } from '@/lib/types'
import { cn } from '@/lib/utils'

function SortHeader({ label, sortKey, sort, onSort, className }: { label: string; sortKey: SortKey; sort: Sort; onSort: (key: SortKey) => void; className?: string }) {
  const active = sort.key === sortKey
  const Icon = !active ? ArrowUpDown : sort.dir === 'asc' ? ArrowUp : ArrowDown
  return (
    <TableHead aria-sort={active ? (sort.dir === 'asc' ? 'ascending' : 'descending') : 'none'} className={className}>
      <Button variant="ghost" size="sm" className="-ml-3" onClick={() => onSort(sortKey)}>
        {label}
        <Icon className={cn('size-3.5', !active && 'text-muted-foreground')} aria-hidden />
      </Button>
    </TableHead>
  )
}

export interface ClientsTableProps {
  clients: Client[]
  sort: Sort
  onSort: (key: SortKey) => void
  onOpen: (client: Client) => void
  onImport: (client: Client) => void
  onArchive: (client: Client) => void
}

export function ClientsTable({ clients, sort, onSort, onOpen, onImport, onArchive }: ClientsTableProps) {
  return (
    <div className="rounded-lg border bg-card">
      <Table>
        <TableCaption className="sr-only">Active clients. Double-click a row to open it.</TableCaption>
        <TableHeader>
          <TableRow>
            <SortHeader label="Client" sortKey="name" sort={sort} onSort={onSort} />
            <TableHead className="hidden md:table-cell">Diagnosis</TableHead>
            <SortHeader label="Payor" sortKey="payor" sort={sort} onSort={onSort} className="hidden sm:table-cell" />
            <SortHeader label="Authorization" sortKey="deadline" sort={sort} onSort={onSort} />
            <TableHead className="w-10">
              <span className="sr-only">Actions</span>
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {clients.map((client) => (
            <TableRow key={client.id} onDoubleClick={() => onOpen(client)} className="cursor-pointer">
              <TableCell>
                <button type="button" className="rounded-sm text-left outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50" onClick={() => onOpen(client)}>
                  <div className="font-medium">{client.display_name}</div>
                  <div className="text-xs text-muted-foreground">{client.client_identifier ?? 'No client ID'}</div>
                  <div className="text-xs text-muted-foreground sm:hidden">{client.payor_name}</div>
                </button>
              </TableCell>
              <TableCell className="hidden md:table-cell">
                {client.diagnosis_codes.length ? client.diagnosis_codes.join(', ') : <span className="text-muted-foreground">—</span>}
              </TableCell>
              <TableCell className="hidden sm:table-cell">{client.payor_name}</TableCell>
              <TableCell>
                {client.latest_period ? (
                  <div className="flex flex-col items-start gap-1">
                    <span className="text-sm">Ends {formatDate(client.latest_period.period_end)}</span>
                    <DeadlineBadge period={client.latest_period} />
                  </div>
                ) : (
                  <span className="text-sm text-muted-foreground">No reports yet</span>
                )}
              </TableCell>
              <TableCell>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="ghost" size="icon" aria-label={`Actions for ${client.display_name}`}>
                      <MoreHorizontal />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem onSelect={() => onOpen(client)}>View details</DropdownMenuItem>
                    <DropdownMenuItem onSelect={() => onImport(client)}>Import a report</DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem variant="destructive" onSelect={() => onArchive(client)}>
                      Archive
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
