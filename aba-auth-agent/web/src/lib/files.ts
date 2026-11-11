export const ACCEPTED = ['.pdf', '.docx']

export function isAccepted(name: string): boolean {
  return ACCEPTED.some((suffix) => name.toLowerCase().endsWith(suffix))
}

/** Hands a file the server built to the browser's own download, under the name the server chose. */
export function saveBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.append(link)
  link.click()
  link.remove()
  // give the browser a moment to start reading it before letting go
  setTimeout(() => URL.revokeObjectURL(url), 10_000)
}
