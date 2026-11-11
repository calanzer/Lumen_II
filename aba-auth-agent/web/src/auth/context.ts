import { createContext } from 'react'

import type { User } from '@/lib/types'

export interface AuthState {
  user: User | null
  /** True until we know whether there's a signed-in session. */
  loading: boolean
  /** Set when the server couldn't be asked at all, which is different from being signed out. */
  error: string | null
  /** Ask the server again whether there's a session. */
  retry: () => void
  login: (username: string, password: string) => Promise<void>
  logout: () => Promise<void>
}

export const AuthContext = createContext<AuthState | null>(null)
