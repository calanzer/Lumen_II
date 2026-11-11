import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'

import { AuthContext } from '@/auth/context'
import { api, ApiError } from '@/lib/api'
import type { User } from '@/lib/types'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const check = useCallback(() => {
    setLoading(true)
    setError(null)
    api
      .me()
      .then(setUser)
      .catch((e) => {
        setUser(null)
        // Only a 401 means "not signed in". Anything else (server down, server error) is a
        // problem with the server, and showing the login form for it would be misleading.
        if (!(e instanceof ApiError && e.status === 401)) setError(e instanceof Error ? e.message : 'Something went wrong.')
      })
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    check()
  }, [check])

  const login = useCallback(async (username: string, password: string) => {
    setUser(await api.login(username, password))
  }, [])

  const logout = useCallback(async () => {
    await api.logout()
    setUser(null)
  }, [])

  const value = useMemo(() => ({ user, loading, error, retry: check, login, logout }), [user, loading, error, check, login, logout])
  return <AuthContext value={value}>{children}</AuthContext>
}
