import { format } from 'date-fns'
import { CalendarIcon } from 'lucide-react'
import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { Calendar } from '@/components/ui/calendar'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'

export function DatePicker({
  id,
  value,
  onChange,
  label,
}: {
  id: string
  value: Date | undefined
  onChange: (date: Date) => void
  label: string
}) {
  const [open, setOpen] = useState(false)
  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button id={id} variant="outline" className="w-full justify-start font-normal" aria-label={label}>
          <CalendarIcon />
          {value ? format(value, 'MMM d, yyyy') : <span className="text-muted-foreground">Pick a date</span>}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-auto p-0" align="start">
        <Calendar
          mode="single"
          required
          selected={value}
          onSelect={(date) => {
            onChange(date)
            setOpen(false) // choosing a date is the end of the interaction
          }}
          defaultMonth={value}
        />
      </PopoverContent>
    </Popover>
  )
}
