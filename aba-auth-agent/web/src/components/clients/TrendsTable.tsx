import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import type { Trends } from '@/lib/types'

/** VB-MAPP domain scores across periods, oldest on the left. */
export function TrendsTable({ trends }: { trends: Trends }) {
  return (
    <div>
      <h3 className="mb-2 text-sm font-medium">VB-MAPP domain scores over time</h3>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Domain</TableHead>
            {trends.columns.map((column, index) => (
              <TableHead key={`${column}-${index}`}>{column}</TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {trends.rows.map((row) => (
            <TableRow key={row.domain}>
              <TableCell>{row.domain}</TableCell>
              {row.values.map((value, index) => (
                <TableCell key={index}>{value ?? '—'}</TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
