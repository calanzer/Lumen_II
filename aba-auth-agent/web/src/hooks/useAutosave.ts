import { useCallback, useEffect, useRef, useState } from 'react'

export type SaveState = 'saved' | 'dirty' | 'saving' | 'error'
export const AUTOSAVE_MS = 800

/**
 * Holds a value being edited and saves it a moment after the last change, so nothing a BCBA
 * types is lost by leaving the page. Edits made while a save is running are sent right after.
 * A refused save (say, an impossible value) keeps the edits on screen and says why.
 */
export function useAutosave<T, R = unknown>(initial: T, save: (value: T) => Promise<R>, onSaved?: (result: R) => void) {
  const [value, setValue] = useState(initial)
  const [state, setState] = useState<SaveState>('saved')
  const [error, setError] = useState<string | null>(null)

  const latest = useRef(initial)
  const pending = useRef(false) // edits exist that the server hasn't confirmed
  const saving = useRef(false)
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)
  const saveRef = useRef(save)
  saveRef.current = save
  const notify = useRef(onSaved)
  notify.current = onSaved

  const flush = useCallback(async () => {
    clearTimeout(timer.current)
    if (saving.current || !pending.current) return // a running save re-checks when it finishes
    const sent = latest.current
    saving.current = true
    setState('saving')
    try {
      const result = await saveRef.current(sent)
      setError(null)
      notify.current?.(result)
      if (latest.current === sent) {
        pending.current = false
        setState('saved')
      } else {
        setState('dirty')
        saving.current = false
        void flush()
        return
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not save.')
      setState('error')
    }
    saving.current = false
  }, [])

  const replace = useCallback(
    (next: T) => {
      latest.current = next
      pending.current = true
      setValue(next)
      setState('dirty')
      clearTimeout(timer.current)
      timer.current = setTimeout(() => void flush(), AUTOSAVE_MS)
    },
    [flush],
  )

  const update = useCallback(
    (recipe: (draft: T) => void) => {
      const next = structuredClone(latest.current)
      recipe(next)
      replace(next)
    },
    [replace],
  )

  /** Forget unsaved edits (they're about to be replaced, e.g. by a regenerated draft). */
  const discard = useCallback(() => {
    clearTimeout(timer.current)
    pending.current = false
    setState('saved')
    setError(null)
  }, [])

  // Leaving the page with unsaved edits sends them now rather than dropping them.
  useEffect(
    () => () => {
      clearTimeout(timer.current)
      void flush()
    },
    [flush],
  )

  // The browser's own "leave site?" prompt, for edits that haven't reached the server.
  useEffect(() => {
    if (state === 'saved') return
    const warn = (event: BeforeUnloadEvent) => event.preventDefault()
    window.addEventListener('beforeunload', warn)
    return () => window.removeEventListener('beforeunload', warn)
  }, [state])

  return { value, update, replace, discard, state, error, saveNow: flush }
}
