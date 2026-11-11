import { BrowserRouter, Navigate, Outlet, Route, Routes } from 'react-router'

import { AuthProvider } from '@/auth/AuthProvider'
import { useAuth } from '@/auth/useAuth'
import { AppShell } from '@/components/AppShell'
import { ServerDown } from '@/components/ServerDown'
import { Skeleton } from '@/components/ui/skeleton'
import { Clients } from '@/pages/Clients'
import { Export } from '@/pages/Export'
import { Generate } from '@/pages/Generate'
import { Import } from '@/pages/Import'
import { Login } from '@/pages/Login'
import { PeriodRedirect } from '@/pages/PeriodRedirect'
import { Review } from '@/pages/Review'
import { Templates } from '@/pages/Templates'

/** Everything inside needs a signed-in user; others are sent to the login screen. */
function RequireAuth() {
  const { user, loading, error, retry } = useAuth()
  if (loading) {
    return (
      <div className="grid min-h-svh place-items-center">
        <Skeleton className="h-8 w-40" />
      </div>
    )
  }
  if (error) return <ServerDown message={error} onRetry={retry} />
  return user ? <Outlet /> : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route element={<RequireAuth />}>
            <Route element={<AppShell />}>
              <Route path="/import" element={<Import />} />
              <Route path="/clients" element={<Clients />} />
              <Route path="/review" element={<PeriodRedirect step="review" />} />
              <Route path="/generate" element={<PeriodRedirect step="generate" />} />
              <Route path="/export" element={<PeriodRedirect step="export" />} />
              <Route path="/periods/:periodId/review" element={<Review />} />
              <Route path="/periods/:periodId/generate" element={<Generate />} />
              <Route path="/periods/:periodId/export" element={<Export />} />
              <Route path="/templates" element={<Templates />} />
              <Route path="*" element={<Navigate to="/import" replace />} />
            </Route>
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}
