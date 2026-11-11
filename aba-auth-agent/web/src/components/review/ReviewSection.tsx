import { Plus, Trash2 } from 'lucide-react'
import { useState, type ReactNode } from 'react'

import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import type { ClinicalData } from '@/lib/types'

/** What every review section receives: the data, and a way to change it. */
export interface SectionProps {
  data: ClinicalData
  update: (recipe: (draft: ClinicalData) => void) => void
}

export function SectionCard({
  number,
  title,
  summary,
  children,
}: {
  number: number
  title: string
  summary?: string
  children: ReactNode
}) {
  return (
    <Card role="region" aria-labelledby={`section-${number}`}>
      <CardHeader>
        <CardTitle id={`section-${number}`} className="flex items-baseline gap-2">
          <span className="text-muted-foreground">{number}.</span> {title}
        </CardTitle>
        {summary && <CardDescription>{summary}</CardDescription>}
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  )
}

/** A list the BCBA can add to and remove from, one collapsible card per item. */
export function ItemList<T>({
  items,
  title,
  render,
  onAdd,
  onRemove,
  noun,
  empty,
}: {
  items: T[]
  title: (item: T, index: number) => ReactNode
  render: (item: T, index: number) => ReactNode
  onAdd: () => void
  onRemove: (index: number) => void
  /** "assessment", "skill target", ... for the button labels */
  noun: string
  empty?: string
}) {
  const [open, setOpen] = useState<string[]>([])
  const id = (index: number) => `item-${index}`

  const add = () => {
    onAdd()
    setOpen((current) => [...current, id(items.length)]) // show the new, blank item
  }
  const remove = (index: number) => {
    onRemove(index)
    // Items after the removed one move up, and so do their open/closed states.
    setOpen((current) =>
      current.filter((value) => value !== id(index)).map((value) => {
        const at = Number(value.slice('item-'.length))
        return at > index ? id(at - 1) : value
      }),
    )
  }

  return (
    <div className="grid gap-3">
      {items.length === 0 && empty && <p className="text-sm text-muted-foreground">{empty}</p>}
      {items.length > 0 && (
        <Accordion type="multiple" value={open} onValueChange={setOpen} className="rounded-md border">
          {items.map((item, index) => (
            <AccordionItem key={index} value={id(index)} className="px-4">
              <AccordionTrigger>{title(item, index)}</AccordionTrigger>
              <AccordionContent className="grid gap-4 pt-1">
                {render(item, index)}
                <div>
                  <Button type="button" variant="outline" size="sm" onClick={() => remove(index)}>
                    <Trash2 /> Remove this {noun}
                  </Button>
                </div>
              </AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
      )}
      <div>
        <Button type="button" variant="outline" size="sm" onClick={add}>
          <Plus /> Add {noun}
        </Button>
      </div>
    </div>
  )
}

export const grid2 = 'grid gap-4 sm:grid-cols-2'
export const grid3 = 'grid gap-4 sm:grid-cols-3'
export const grid4 = 'grid gap-4 sm:grid-cols-2 lg:grid-cols-4'
