import { useEffect, useId, useRef, useState, type ReactNode } from 'react'

import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import type { IsoDate } from '@/lib/types'
import { cn } from '@/lib/utils'

/** A label above a control, with an optional hint or problem underneath. */
export function Field({
  label,
  htmlFor,
  hint,
  error,
  className,
  children,
}: {
  label: string
  htmlFor: string
  hint?: ReactNode
  error?: string | null
  className?: string
  children: ReactNode
}) {
  return (
    <div className={cn('grid gap-1.5', className)}>
      <Label htmlFor={htmlFor}>{label}</Label>
      {children}
      {error ? (
        <p className="text-xs text-destructive" role="alert">
          {error}
        </p>
      ) : (
        hint && <p className="text-xs text-muted-foreground">{hint}</p>
      )}
    </div>
  )
}

/** Text that may be absent: an empty box means "not stated" (null), never an empty string. */
export function TextField({
  label,
  value,
  onChange,
  hint,
  className,
}: {
  label: string
  value: string | null
  onChange: (value: string | null) => void
  hint?: ReactNode
  className?: string
}) {
  const id = useId()
  return (
    <Field label={label} htmlFor={id} hint={hint} className={className}>
      <Input id={id} value={value ?? ''} onChange={(e) => onChange(e.target.value === '' ? null : e.target.value)} />
    </Field>
  )
}

/** Text that is always present (an empty box is an empty string). */
export function RequiredTextField({
  label,
  value,
  onChange,
  className,
}: {
  label: string
  value: string
  onChange: (value: string) => void
  className?: string
}) {
  const id = useId()
  return (
    <Field label={label} htmlFor={id} className={className}>
      <Input id={id} value={value} onChange={(e) => onChange(e.target.value)} />
    </Field>
  )
}

export function TextAreaField({
  label,
  value,
  onChange,
  rows = 3,
  hint,
  className,
}: {
  label: string
  value: string | null
  onChange: (value: string | null) => void
  rows?: number
  hint?: ReactNode
  className?: string
}) {
  const id = useId()
  return (
    <Field label={label} htmlFor={id} hint={hint} className={className}>
      <Textarea id={id} rows={rows} value={value ?? ''} onChange={(e) => onChange(e.target.value === '' ? null : e.target.value)} />
    </Field>
  )
}

export function RequiredTextAreaField({
  label,
  value,
  onChange,
  rows = 3,
  className,
}: {
  label: string
  value: string
  onChange: (value: string) => void
  rows?: number
  className?: string
}) {
  const id = useId()
  return (
    <Field label={label} htmlFor={id} className={className}>
      <Textarea id={id} rows={rows} value={value} onChange={(e) => onChange(e.target.value)} />
    </Field>
  )
}

const asText = (value: number | null) => (value === null ? '' : String(value))

/** What the box holds as a number: null when empty, undefined while it isn't a usable number yet. */
function parseNumber(text: string): number | null | undefined {
  const trimmed = text.trim()
  if (trimmed === '') return null
  const n = Number(trimmed)
  return Number.isFinite(n) ? n : undefined
}

/**
 * A number that may be unknown. Clearing the box gives null (not 0), and half-typed input like
 * "-" or "1." stays on screen instead of being rewritten under the cursor.
 */
export function NumberField({
  label,
  value,
  onChange,
  min,
  max,
  placeholder = 'Not stated',
  allowEmpty = true,
  hint,
  className,
}: {
  label: string
  value: number | null
  onChange: (value: number | null) => void
  min?: number
  max?: number
  placeholder?: string
  /** false for values that must be a number (units, goal numbers): an empty box is a problem */
  allowEmpty?: boolean
  hint?: ReactNode
  className?: string
}) {
  const id = useId()
  const [text, setText] = useState(asText(value))
  const sent = useRef<number | null>(value) // the last value we reported (or were given)

  // A change that didn't come from typing here (Raw JSON, reload) replaces what's shown.
  useEffect(() => {
    if (value !== sent.current) {
      sent.current = value
      setText(asText(value))
    }
  }, [value])

  const parsed = parseNumber(text)
  let error: string | null = null
  if (parsed === undefined) error = 'Enter a number.'
  else if (parsed === null && !allowEmpty) error = 'Required.'
  else if (parsed !== null && min !== undefined && parsed < min) error = `Must be at least ${min}.`
  else if (parsed !== null && max !== undefined && parsed > max) error = `Must be at most ${max}.`

  return (
    <Field label={label} htmlFor={id} hint={hint} error={error} className={className}>
      <Input
        id={id}
        inputMode="decimal"
        value={text}
        placeholder={placeholder}
        aria-invalid={error ? true : undefined}
        onChange={(e) => {
          const next = e.target.value
          setText(next)
          const n = parseNumber(next)
          if (n === undefined) return
          if (n === null ? !allowEmpty : (min !== undefined && n < min) || (max !== undefined && n > max)) return
          sent.current = n
          onChange(n)
        }}
      />
    </Field>
  )
}

/** A date that may be unknown. The browser's own date box allows typing, picking and clearing. */
export function DateField({
  label,
  value,
  onChange,
  className,
}: {
  label: string
  value: IsoDate
  onChange: (value: IsoDate) => void
  className?: string
}) {
  const id = useId()
  return (
    <Field label={label} htmlFor={id} className={className}>
      <Input id={id} type="date" value={value ?? ''} onChange={(e) => onChange(e.target.value === '' ? null : e.target.value)} />
    </Field>
  )
}

export function SelectField<T extends string>({
  label,
  value,
  options,
  onChange,
  placeholder,
  className,
}: {
  label: string
  value: T | null
  options: readonly T[]
  onChange: (value: T) => void
  placeholder?: string
  className?: string
}) {
  const id = useId()
  return (
    <Field label={label} htmlFor={id} className={className}>
      <Select value={value ?? undefined} onValueChange={(v) => onChange(v as T)}>
        <SelectTrigger id={id} className="w-full">
          <SelectValue placeholder={placeholder ?? 'Choose'} />
        </SelectTrigger>
        <SelectContent>
          {options.map((option) => (
            <SelectItem key={option} value={option}>
              {option}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </Field>
  )
}

export function CheckField({
  label,
  checked,
  onChange,
  className,
}: {
  label: string
  checked: boolean
  onChange: (checked: boolean) => void
  className?: string
}) {
  const id = useId()
  return (
    <div className={cn('flex items-center gap-2', className)}>
      <Checkbox id={id} checked={checked} onCheckedChange={(state) => onChange(state === true)} />
      <Label htmlFor={id}>{label}</Label>
    </div>
  )
}

const toLines = (text: string) =>
  text
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)

/** One item per line. The box keeps what's typed (blank lines and all); the saved list drops blanks. */
export function LinesField({
  label,
  value,
  onChange,
  rows = 3,
  hint = 'One per line',
  className,
}: {
  label: string
  value: string[]
  onChange: (value: string[]) => void
  rows?: number
  hint?: ReactNode
  className?: string
}) {
  const id = useId()
  const [text, setText] = useState(value.join('\n'))
  const sent = useRef(value.join('\n'))

  useEffect(() => {
    const incoming = value.join('\n')
    if (incoming !== sent.current) {
      sent.current = incoming
      setText(incoming)
    }
  }, [value])

  return (
    <Field label={label} htmlFor={id} hint={hint} className={className}>
      <Textarea
        id={id}
        rows={rows}
        value={text}
        onChange={(e) => {
          setText(e.target.value)
          const lines = toLines(e.target.value)
          sent.current = lines.join('\n')
          onChange(lines)
        }}
      />
    </Field>
  )
}
