import { afterEach, describe, expect, it, vi } from 'vitest'

import { api, ApiError, errorMessage, UNREACHABLE } from '@/lib/api'

const respond = (body: unknown, status = 200) =>
  Promise.resolve(new Response(typeof body === 'string' ? body : JSON.stringify(body), { status }))

afterEach(() => vi.restoreAllMocks())

describe('errorMessage', () => {
  it('uses the API detail when it is text', async () => {
    expect(await errorMessage(new Response(JSON.stringify({ detail: 'Choose a payor.' }), { status: 422 }))).toBe('Choose a payor.')
  })

  it('does not show raw validation arrays to the user', async () => {
    const message = await errorMessage(new Response(JSON.stringify({ detail: [{ loc: ['body'], msg: 'bad' }] }), { status: 422 }))
    expect(message).toBe('The request was not accepted.')
  })

  it('says something plain for a server error with no JSON', async () => {
    expect(await errorMessage(new Response('<html>oops</html>', { status: 500 }))).toBe('Something went wrong on the server.')
  })
})

describe('errorMessage when the server is not there', () => {
  it.each([502, 503, 504])('treats a %i from a proxy as the API being unreachable', async (status) => {
    expect(await errorMessage(new Response('', { status }))).toBe(UNREACHABLE)
  })

  it('still calls a genuine 500 a server error', async () => {
    expect(await errorMessage(new Response('Internal Server Error', { status: 500 }))).toBe('Something went wrong on the server.')
  })
})

describe('api', () => {
  it('throws ApiError carrying the status and message', async () => {
    vi.stubGlobal('fetch', vi.fn(() => respond({ detail: 'Not signed in.' }, 401)))
    await expect(api.me()).rejects.toMatchObject({ name: 'ApiError', status: 401, message: 'Not signed in.' })
    await expect(api.me()).rejects.toBeInstanceOf(ApiError)
  })

  it('sends the session cookie and JSON for login', async () => {
    const fetchMock = vi.fn(() => respond({ username: 'u', name: 'U' }))
    vi.stubGlobal('fetch', fetchMock)
    await api.login('u', 'pw')
    const [path, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit]
    expect(path).toBe('/api/auth/login')
    expect(init.credentials).toBe('same-origin')
    expect(init.method).toBe('POST')
    expect(JSON.parse(init.body as string)).toEqual({ username: 'u', password: 'pw' })
  })

  it('says plainly that the server is unreachable instead of "Failed to fetch"', async () => {
    vi.stubGlobal('fetch', vi.fn(() => Promise.reject(new TypeError('Failed to fetch'))))
    const error = await api.clients().catch((e) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect(error.status).toBe(0)
    expect(error.message).toBe(UNREACHABLE)
    expect(error.message).not.toMatch(/Failed to fetch/)
  })

  it('uploads the report as multipart form data under "file"', async () => {
    const fetchMock = vi.fn(() => respond({ id: 'j', stage: 'reading' }, 202))
    vi.stubGlobal('fetch', fetchMock)
    await api.startImport(new File(['x'], 'r.pdf'))
    const [, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit]
    expect(init.body).toBeInstanceOf(FormData)
    expect((init.body as FormData).get('file')).toBeInstanceOf(File)
  })
})
