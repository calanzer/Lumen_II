import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Textarea } from '@/components/ui/textarea'
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion'
import { TOO_BRIEF_WORDS, TOO_LONG_WORDS, wordCount } from '@/lib/review'
import type { NarrativeSection } from '@/lib/types'

export interface SectionText {
  key: string
  content: string
}

function WordCount({ text }: { text: string }) {
  const words = wordCount(text)
  if (words < TOO_BRIEF_WORDS) return <p className="text-xs text-warning-foreground">{words} words — may be too brief for the payor</p>
  if (words > TOO_LONG_WORDS) return <p className="text-xs text-warning-foreground">{words} words — consider condensing</p>
  return <p className="text-xs text-muted-foreground">{words} words</p>
}

/** Every section with its source data on the left and the editable text on the right. */
export function NarrativeEditor({
  sections,
  texts,
  onEdit,
}: {
  sections: NarrativeSection[]
  /** The text as currently edited, by section key */
  texts: SectionText[]
  onEdit: (key: string, content: string) => void
}) {
  const textFor = (key: string) => texts.find((t) => t.key === key)?.content ?? ''
  // Sections that need a look start open
  const initiallyOpen = sections.filter((s) => s.requires_review).map((s) => s.key)

  return (
    <Accordion type="multiple" defaultValue={initiallyOpen} className="rounded-md border">
      {sections.map((section, index) => {
        const text = textFor(section.key)
        const fields = Object.keys(section.source)
        return (
          <AccordionItem key={section.key} value={section.key} className="px-4">
            <AccordionTrigger>
              <span className="flex flex-wrap items-center gap-2">
                <span>
                  {index + 1}. {section.title}
                </span>
                {section.requires_review ? (
                  <Badge className="bg-warning text-warning-foreground">Needs review</Badge>
                ) : (
                  <Badge variant="secondary">OK</Badge>
                )}
              </span>
            </AccordionTrigger>
            <AccordionContent className="grid gap-4 pt-1">
              {section.requires_review && section.review_note && (
                <Alert className="border-warning/50 bg-warning/10">
                  <AlertDescription>Review needed: {section.review_note}</AlertDescription>
                </Alert>
              )}
              <div className="grid gap-4 lg:grid-cols-2">
                <div className="grid content-start gap-1.5">
                  <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Source data (read-only reference)</p>
                  {fields.length > 0 ? (
                    <pre
                      tabIndex={0}
                      aria-label={`Source data for ${section.title}`}
                      className="max-h-72 overflow-auto rounded-md bg-muted p-3 text-xs"
                    >
                      {JSON.stringify(section.source, null, 2)}
                    </pre>
                  ) : (
                    <p className="text-sm text-muted-foreground">The AI did not list specific source fields for this section.</p>
                  )}
                </div>
                <div className="grid content-start gap-1.5">
                  <label htmlFor={`narrative-${section.key}`} className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    Narrative (edit below)
                  </label>
                  <Textarea
                    id={`narrative-${section.key}`}
                    aria-label={`Edit ${section.title}`}
                    className="min-h-64"
                    value={text}
                    onChange={(e) => onEdit(section.key, e.target.value)}
                  />
                  <WordCount text={text} />
                </div>
              </div>
            </AccordionContent>
          </AccordionItem>
        )
      })}
    </Accordion>
  )
}
