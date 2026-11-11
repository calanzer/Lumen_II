import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { describe, expect, it, vi } from 'vitest'

import { DateField, LinesField, NumberField, TextField } from '@/components/fields'

function Number({ initial, onChange, ...rest }: { initial: number | null; onChange: (v: number | null) => void } & Partial<Parameters<typeof NumberField>[0]>) {
  const [value, setValue] = useState(initial)
  return (
    <>
      <NumberField
        label="Score"
        {...rest}
        value={value}
        onChange={(v) => {
          setValue(v)
          onChange(v)
        }}
      />
      <button onClick={() => setValue(42)}>external</button>
    </>
  )
}

describe('NumberField', () => {
  it('reports a cleared box as unknown (null), never as 0', async () => {
    const onChange = vi.fn()
    render(<Number initial={7} onChange={onChange} />)
    await userEvent.clear(screen.getByLabelText('Score'))
    expect(onChange).toHaveBeenLastCalledWith(null)
    expect(screen.getByLabelText('Score')).toHaveValue('')
  })

  it('reports typed numbers, including decimals', async () => {
    const onChange = vi.fn()
    render(<Number initial={null} onChange={onChange} />)
    await userEvent.type(screen.getByLabelText('Score'), '12.5')
    expect(onChange).toHaveBeenLastCalledWith(12.5)
    expect(screen.getByLabelText('Score')).toHaveValue('12.5')
  })

  it('keeps half-typed input on screen and does not report it', async () => {
    const onChange = vi.fn()
    render(<Number initial={null} onChange={onChange} />)
    await userEvent.type(screen.getByLabelText('Score'), '-')
    expect(screen.getByLabelText('Score')).toHaveValue('-')
    expect(screen.getByRole('alert')).toHaveTextContent('Enter a number')
    expect(onChange).not.toHaveBeenCalled()
  })

  it('refuses values outside the range, saying why', async () => {
    const onChange = vi.fn()
    render(<Number initial={50} onChange={onChange} min={0} max={100} />)
    const input = screen.getByLabelText('Score')
    await userEvent.clear(input)
    onChange.mockClear()
    await userEvent.type(input, '150')
    expect(screen.getByRole('alert')).toHaveTextContent('Must be at most 100')
    expect(onChange).not.toHaveBeenCalledWith(150)
    expect(onChange).toHaveBeenLastCalledWith(15) // the last acceptable value stays in force
  })

  it('does not accept an empty box when a value is required', async () => {
    const onChange = vi.fn()
    render(<Number initial={5} onChange={onChange} allowEmpty={false} />)
    await userEvent.clear(screen.getByLabelText('Score'))
    expect(screen.getByRole('alert')).toHaveTextContent('Required')
    expect(onChange).not.toHaveBeenCalledWith(null)
  })

  it('shows a value that changed from outside (like pasted JSON)', async () => {
    render(<Number initial={1} onChange={() => {}} />)
    await userEvent.click(screen.getByText('external'))
    expect(screen.getByLabelText('Score')).toHaveValue('42')
  })
})

describe('LinesField', () => {
  function Lines({ onChange }: { onChange: (v: string[]) => void }) {
    const [value, setValue] = useState(['F84.0'])
    return (
      <LinesField
        label="Codes"
        value={value}
        onChange={(v) => {
          setValue(v)
          onChange(v)
        }}
      />
    )
  }

  it('lets you press Enter to start a new line, but saves only the filled-in lines', async () => {
    const onChange = vi.fn()
    render(<Lines onChange={onChange} />)
    const box = screen.getByLabelText('Codes')
    await userEvent.type(box, '{Enter}')
    expect(box).toHaveValue('F84.0\n') // the new blank line stays in the box
    expect(onChange).toHaveBeenLastCalledWith(['F84.0'])
    await userEvent.type(box, 'F80.2')
    expect(onChange).toHaveBeenLastCalledWith(['F84.0', 'F80.2'])
  })

  it('trims each line', async () => {
    const onChange = vi.fn()
    render(<Lines onChange={onChange} />)
    await userEvent.type(screen.getByLabelText('Codes'), '{Enter}   F80.2  ')
    expect(onChange).toHaveBeenLastCalledWith(['F84.0', 'F80.2'])
  })
})

describe('TextField and DateField', () => {
  it('an emptied text box means "not stated" (null), not an empty string', async () => {
    const onChange = vi.fn()
    render(<TextField label="BCBA" value="Dr. G" onChange={onChange} />)
    await userEvent.clear(screen.getByLabelText('BCBA'))
    expect(onChange).toHaveBeenLastCalledWith(null)
  })

  it('a cleared date is null, and a chosen date is the plain YYYY-MM-DD the API uses', async () => {
    const onChange = vi.fn()
    const { rerender } = render(<DateField label="Start" value="2026-01-05" onChange={onChange} />)
    expect(screen.getByLabelText('Start')).toHaveValue('2026-01-05')
    await userEvent.clear(screen.getByLabelText('Start'))
    expect(onChange).toHaveBeenLastCalledWith(null)
    rerender(<DateField label="Start" value={null} onChange={onChange} />)
    await userEvent.type(screen.getByLabelText('Start'), '2026-02-03')
    expect(onChange).toHaveBeenLastCalledWith('2026-02-03')
  })
})
