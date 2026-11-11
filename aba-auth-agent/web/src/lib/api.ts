import type {
  Answers,
  Client,
  ClientDetail,
  ClinicalData,
  GenerationStatus,
  ImportJob,
  Narrative,
  NewClient,
  Payor,
  PeriodCard,
  PeriodDetail,
  SavedData,
  TemplateDraft,
  TemplateInfo,
  User,
} from '@/lib/types'

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export const UNREACHABLE = "Can't reach the server. Check that the API is running, then try again."

/** What a proxy or gateway answers when the real server behind it isn't there. */
const GATEWAY_ERRORS = new Set([502, 503, 504])

/** The message from a failed response: the API's `detail` when it's text, else a generic one. */
export async function errorMessage(response: Response): Promise<string> {
  if (GATEWAY_ERRORS.has(response.status)) return UNREACHABLE
  try {
    const body = await response.json()
    if (typeof body?.detail === 'string') return body.detail
  } catch {
    // not JSON
  }
  return response.status >= 500 ? 'Something went wrong on the server.' : 'The request was not accepted.'
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(path, { credentials: 'same-origin', ...init })
  } catch {
    // The browser only says "Failed to fetch" when nothing answered at all
    throw new ApiError(0, UNREACHABLE)
  }
  if (!response.ok) throw new ApiError(response.status, await errorMessage(response))
  return (await response.json()) as T
}

/** A file the server builds on request (the Word export), with the name it suggests. */
export interface Download {
  blob: Blob
  filename: string
}

async function requestFile(path: string, init: RequestInit, fallbackName: string): Promise<Download> {
  let response: Response
  try {
    response = await fetch(path, { credentials: 'same-origin', ...init })
  } catch {
    throw new ApiError(0, UNREACHABLE)
  }
  if (!response.ok) throw new ApiError(response.status, await errorMessage(response))
  const named = /filename="([^"]+)"/.exec(response.headers.get('Content-Disposition') ?? '')
  return { blob: await response.blob(), filename: named?.[1] ?? fallbackName }
}

function json(method: string, body: unknown): RequestInit {
  return { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }
}

export const api = {
  me: () => request<User>('/api/auth/me'),
  login: (username: string, password: string) => request<User>('/api/auth/login', json('POST', { username, password })),
  logout: () => request<{ ok: boolean }>('/api/auth/logout', { method: 'POST' }),
  payors: () => request<Payor[]>('/api/payors'),
  clients: () => request<Client[]>('/api/clients'),
  createClient: (client: NewClient) => request<Client>('/api/clients', json('POST', client)),
  clientDetail: (id: string) => request<ClientDetail>(`/api/clients/${id}`),
  archiveClient: (id: string) => request<{ ok: boolean }>(`/api/clients/${id}/archive`, { method: 'POST' }),
  startImport: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return request<ImportJob>('/api/imports', { method: 'POST', body: form })
  },
  getImport: (id: string) => request<ImportJob>(`/api/imports/${id}`),
  answerImport: (id: string, answers: Answers) => request<ImportJob>(`/api/imports/${id}/answers`, json('POST', answers)),

  createPeriod: (clientId: string, period_start: string, period_end: string) =>
    request<PeriodCard>(`/api/clients/${clientId}/periods`, json('POST', { period_start, period_end })),
  period: (id: string) => request<PeriodDetail>(`/api/periods/${id}`),
  saveNotes: (id: string, notes: string) => request<{ notes: string }>(`/api/periods/${id}`, json('PATCH', { notes })),
  saveData: (id: string, data: ClinicalData) => request<SavedData>(`/api/periods/${id}/data`, json('PUT', data)),
  saveNarrative: (id: string, sections: { key: string; content: string }[]) =>
    request<Narrative>(`/api/periods/${id}/narrative`, json('PUT', { sections })),
  startGeneration: (id: string) => request<GenerationStatus>(`/api/periods/${id}/generate`, { method: 'POST' }),
  generation: (id: string) => request<GenerationStatus>(`/api/periods/${id}/generate`),
  exportPeriod: (id: string, payor_key?: string) =>
    requestFile(`/api/periods/${id}/export`, json('POST', { confirmed: true, payor_key }), 'reauthorization.docx'),
  markSubmitted: (id: string) => request<{ status: string }>(`/api/periods/${id}/submitted`, { method: 'POST' }),

  template: (payor: string) => request<TemplateInfo>(`/api/templates/${payor}`),
  analyzeTemplate: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return request<TemplateDraft>('/api/templates/analyze', { method: 'POST', body: form })
  },
  saveTemplate: (payor: string, name: string, draft: TemplateDraft) =>
    request<TemplateInfo>(`/api/templates/${payor}`, json('PUT', { name, ...draft })),
  useDefaultTemplate: (payor: string) => request<TemplateInfo>(`/api/templates/${payor}`, { method: 'DELETE' }),
}
