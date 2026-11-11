import { describe, expect, it } from 'vitest'

import { filterClients, nextSort, sortClients } from '@/lib/clients'
import { client, period } from '@/test/fixtures'

const abe = client({ id: 'a', display_name: 'Abe A.', client_identifier: 'CR-100', payor_name: 'Optum', diagnosis_codes: ['F84.0', 'F80.2'], latest_period: period({ days_until_end: 45 }) })
const bea = client({ id: 'b', display_name: 'Bea B.', client_identifier: 'CR-200', payor_name: 'Aetna', diagnosis_codes: ['F84.0'], latest_period: period({ days_until_end: -3 }) })
const cal = client({ id: 'c', display_name: 'Cal C.', client_identifier: null, payor_name: 'Aetna', diagnosis_codes: [], latest_period: period({ days_until_end: 9 }) })
const dee = client({ id: 'd', display_name: 'Dee D.', payor_name: 'Medi-Cal', latest_period: period({ status: 'exported', days_until_end: -40 }) })
const eli = client({ id: 'e', display_name: 'Eli E.', payor_name: 'Anthem', latest_period: null, period_count: 0 })
const all = [abe, bea, cal, dee, eli]
const ids = (list: typeof all) => list.map((c) => c.id).join('')

describe('filterClients', () => {
  it('returns everyone for an empty or blank search', () => {
    expect(filterClients(all, '')).toBe(all)
    expect(filterClients(all, '   ')).toBe(all)
  })

  it('matches name, client ID, diagnosis code and payor, ignoring case', () => {
    expect(ids(filterClients(all, 'bea'))).toBe('b')
    expect(ids(filterClients(all, 'cr-200'))).toBe('b')
    expect(ids(filterClients(all, 'f80.2'))).toBe('a')
    expect(ids(filterClients(all, 'AETNA'))).toBe('bc')
  })

  it('needs every word to match, in any order', () => {
    expect(ids(filterClients(all, 'aetna f84'))).toBe('b')
    expect(ids(filterClients(all, 'f84 aetna'))).toBe('b')
    expect(ids(filterClients(all, 'aetna zzz'))).toBe('')
  })

  it('copes with clients that have no ID or codes', () => {
    expect(filterClients([cal], 'cal')).toEqual([cal]) // no ID, no codes: nothing to trip over
    expect(ids(filterClients(all, 'cal'))).toBe('cd') // 'cal' is also in the Medi-Cal payor
  })
})

describe('sortClients', () => {
  it('puts the most urgent authorization first: expired, then soonest', () => {
    expect(ids(sortClients(all, { key: 'deadline', dir: 'asc' }).slice(0, 3))).toBe('bca')
  })

  it('keeps clients with nothing to act on (finished or no period) at the end, by name', () => {
    expect(ids(sortClients(all, { key: 'deadline', dir: 'asc' }).slice(3))).toBe('de')
  })

  it('reversing the deadline sort lists the least urgent first but still leaves finished clients last', () => {
    const reversed = sortClients(all, { key: 'deadline', dir: 'desc' })
    expect(ids(reversed.slice(0, 3))).toBe('acb')
    expect(ids(reversed.slice(3))).toBe('de')
  })

  it('sorts by name, case-insensitively, and numbers naturally', () => {
    const named = [client({ id: '1', display_name: 'client 10' }), client({ id: '2', display_name: 'Client 2' }), client({ id: '3', display_name: 'amy' })]
    expect(ids(sortClients(named, { key: 'name', dir: 'asc' }))).toBe('321')
    expect(ids(sortClients(named, { key: 'name', dir: 'desc' }))).toBe('123')
  })

  it('sorts by payor, then name', () => {
    // Aetna (Bea, Cal), Anthem (Eli), Medi-Cal (Dee), Optum (Abe)
    expect(ids(sortClients(all, { key: 'payor', dir: 'asc' }))).toBe('bceda')
  })

  it('does not change the list it was given', () => {
    const before = ids(all)
    sortClients(all, { key: 'name', dir: 'desc' })
    expect(ids(all)).toBe(before)
  })
})

describe('nextSort', () => {
  it('starts a new column ascending and flips the same column', () => {
    expect(nextSort({ key: 'deadline', dir: 'asc' }, 'name')).toEqual({ key: 'name', dir: 'asc' })
    expect(nextSort({ key: 'name', dir: 'asc' }, 'name')).toEqual({ key: 'name', dir: 'desc' })
    expect(nextSort({ key: 'name', dir: 'desc' }, 'name')).toEqual({ key: 'name', dir: 'asc' })
  })
})
