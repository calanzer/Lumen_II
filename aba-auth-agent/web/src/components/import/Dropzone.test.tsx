import { fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { Dropzone } from '@/components/import/Dropzone'
import { isAccepted } from '@/lib/files'

describe('isAccepted', () => {
  it('takes PDF and Word files regardless of case, and nothing else', () => {
    expect(isAccepted('report.pdf')).toBe(true)
    expect(isAccepted('REPORT.DOCX')).toBe(true)
    expect(isAccepted('notes.txt')).toBe(false)
    expect(isAccepted('old.doc')).toBe(false)
    expect(isAccepted('pdf')).toBe(false)
  })
})

describe('Dropzone', () => {
  it('passes a chosen file on', async () => {
    const onFile = vi.fn()
    render(<Dropzone onFile={onFile} />)
    const file = new File(['x'], 'report.pdf', { type: 'application/pdf' })
    await userEvent.upload(screen.getByLabelText(/Drop a progress report here/), file)
    expect(onFile).toHaveBeenCalledWith(file)
  })

  it('takes a dropped file', () => {
    const onFile = vi.fn()
    render(<Dropzone onFile={onFile} />)
    const file = new File(['x'], 'report.docx')
    fireEvent.drop(screen.getByText('Drop a progress report here').closest('label')!, { dataTransfer: { files: [file] } })
    expect(onFile).toHaveBeenCalledWith(file)
  })

  it('refuses other file types with a visible message', () => {
    const onFile = vi.fn()
    render(<Dropzone onFile={onFile} />)
    fireEvent.drop(screen.getByText('Drop a progress report here').closest('label')!, {
      dataTransfer: { files: [new File(['x'], 'notes.txt')] },
    })
    expect(onFile).not.toHaveBeenCalled()
    expect(screen.getByRole('alert')).toHaveTextContent('Upload a PDF or Word (.docx) report.')
  })

  it('ignores drops while an import is running', () => {
    const onFile = vi.fn()
    render(<Dropzone onFile={onFile} disabled />)
    fireEvent.drop(screen.getByText('Drop a progress report here').closest('label')!, {
      dataTransfer: { files: [new File(['x'], 'report.pdf')] },
    })
    expect(onFile).not.toHaveBeenCalled()
  })
})
