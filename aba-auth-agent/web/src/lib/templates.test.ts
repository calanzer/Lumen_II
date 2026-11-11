import { describe, expect, it } from 'vitest'

import { moveRow, newRow, rowsFrom, templateProblem, toDraft } from '@/lib/templates'

const rows = () => rowsFrom([{ title: 'A', guidance: 'a' }, { title: 'B', guidance: '' }, { title: 'C', guidance: '' }])
const titles = (r: ReturnType<typeof rows>) => r.map((x) => x.title)

describe('moveRow', () => {
  it('moves a row up and down', () => {
    expect(titles(moveRow(rows(), 1, -1))).toEqual(['B', 'A', 'C'])
    expect(titles(moveRow(rows(), 1, 1))).toEqual(['A', 'C', 'B'])
  })
  it('leaves the order alone at either end', () => {
    expect(titles(moveRow(rows(), 0, -1))).toEqual(['A', 'B', 'C'])
    expect(titles(moveRow(rows(), 2, 1))).toEqual(['A', 'B', 'C'])
  })
  it('does not change the list it was given', () => {
    const original = rows()
    moveRow(original, 0, 1)
    expect(titles(original)).toEqual(['A', 'B', 'C'])
  })
})

describe('templateProblem', () => {
  it('needs a name and at least two titled sections', () => {
    expect(templateProblem('', rows())).toMatch(/name/)
    expect(templateProblem('   ', rows())).toMatch(/name/)
    expect(templateProblem('Ours', rowsFrom([{ title: 'Only', guidance: '' }]))).toMatch(/two sections/)
    expect(templateProblem('Ours', rowsFrom([{ title: 'A', guidance: '' }, { title: '  ', guidance: 'x' }]))).toMatch(/two sections/)
    expect(templateProblem('Ours', rows())).toBeNull()
  })
})

describe('toDraft', () => {
  it('drops untitled rows and trims the text', () => {
    const draft = toDraft([newRow({ title: ' A ', guidance: ' x ' }), newRow({ title: '' }), newRow({ title: 'B' })], ' Formal. ', 'old.pdf')
    expect(draft).toEqual({
      source_filename: 'old.pdf',
      style_notes: 'Formal.',
      sections: [{ title: 'A', guidance: 'x' }, { title: 'B', guidance: '' }],
    })
  })
})
