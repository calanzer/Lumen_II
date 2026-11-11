import { UploadCloud } from 'lucide-react'
import { useState, type DragEvent } from 'react'

import { ACCEPTED, isAccepted } from '@/lib/files'
import { cn } from '@/lib/utils'

export function Dropzone({ onFile, disabled = false }: { onFile: (file: File) => void; disabled?: boolean }) {
  const [dragging, setDragging] = useState(false)
  const [problem, setProblem] = useState<string | null>(null)

  function take(file: File | undefined) {
    if (!file) return
    if (!isAccepted(file.name)) {
      setProblem('Upload a PDF or Word (.docx) report.')
      return
    }
    setProblem(null)
    onFile(file)
  }

  function onDrop(event: DragEvent) {
    event.preventDefault()
    setDragging(false)
    if (!disabled) take(event.dataTransfer.files[0])
  }

  return (
    <div>
      <label
        htmlFor="report-file"
        onDragOver={(event) => {
          event.preventDefault()
          if (!disabled) setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={cn(
          'flex cursor-pointer flex-col items-center gap-3 rounded-xl border-2 border-dashed bg-card px-6 py-14 text-center transition-colors',
          'focus-within:ring-[3px] focus-within:ring-ring/50 hover:bg-accent/40',
          dragging && 'border-primary bg-accent',
          disabled && 'pointer-events-none opacity-60',
        )}
      >
        <UploadCloud className="size-9 text-primary" aria-hidden />
        <div>
          <p className="font-medium">Drop a progress report here</p>
          <p className="mt-1 text-sm text-muted-foreground">or click to choose a file. PDF or Word, up to 50 MB.</p>
        </div>
        <input
          id="report-file"
          type="file"
          accept={ACCEPTED.join(',')}
          className="sr-only"
          disabled={disabled}
          onChange={(event) => {
            take(event.target.files?.[0])
            event.target.value = '' // allows choosing the same file again
          }}
        />
      </label>
      {problem && (
        <p role="alert" className="mt-2 text-sm text-destructive">
          {problem}
        </p>
      )}
    </div>
  )
}
