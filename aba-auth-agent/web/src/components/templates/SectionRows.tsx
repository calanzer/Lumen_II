import { ArrowDown, ArrowUp, Plus, Trash2 } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { moveRow, newRow, type Row } from '@/lib/templates'

/** The detected sections as an editable list: rename, describe, reorder, add and delete. */
export function SectionRows({ rows, onChange }: { rows: Row[]; onChange: (rows: Row[]) => void }) {
  const edit = (id: number, patch: Partial<Row>) => onChange(rows.map((row) => (row.id === id ? { ...row, ...patch } : row)))

  return (
    <div className="grid gap-3">
      <ol className="grid gap-3">
        {rows.map((row, index) => (
          <li key={row.id} className="grid gap-3 rounded-md border p-3 sm:grid-cols-[2rem_1fr_auto]">
            <span className="pt-2 text-sm font-medium text-muted-foreground">{index + 1}.</span>
            <div className="grid gap-2">
              <Input
                aria-label={`Section ${index + 1} title`}
                placeholder="Section title"
                value={row.title}
                onChange={(e) => edit(row.id, { title: e.target.value })}
              />
              <Textarea
                aria-label={`Section ${index + 1} covers`}
                placeholder="What this section covers"
                rows={2}
                value={row.guidance}
                onChange={(e) => edit(row.id, { guidance: e.target.value })}
              />
            </div>
            <div className="flex gap-1 sm:flex-col">
              <Button
                variant="ghost"
                size="icon"
                aria-label={`Move section ${index + 1} up`}
                disabled={index === 0}
                onClick={() => onChange(moveRow(rows, index, -1))}
              >
                <ArrowUp />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                aria-label={`Move section ${index + 1} down`}
                disabled={index === rows.length - 1}
                onClick={() => onChange(moveRow(rows, index, 1))}
              >
                <ArrowDown />
              </Button>
              <Button variant="ghost" size="icon" aria-label={`Delete section ${index + 1}`} onClick={() => onChange(rows.filter((r) => r.id !== row.id))}>
                <Trash2 />
              </Button>
            </div>
          </li>
        ))}
      </ol>
      <div>
        <Button variant="outline" size="sm" onClick={() => onChange([...rows, newRow()])}>
          <Plus /> Add section
        </Button>
      </div>
    </div>
  )
}
