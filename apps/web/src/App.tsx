import { useEffect } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from '@/components/ui/toaster'
import { useAuthStore } from '@/stores/auth'

// Layouts
import { AuthLayout } from '@/components/layouts/AuthLayout'
import { DashboardLayout } from '@/components/layouts/DashboardLayout'

// Auth Pages
import { LoginPage } from '@/pages/auth/LoginPage'
import { RegisterPage } from '@/pages/auth/RegisterPage'

// Dashboard Pages
import { DashboardPage } from '@/pages/dashboard/DashboardPage'
import { SettingsPage } from '@/pages/settings/SettingsPage'

// Admin Pages
import { UsersPage, FeatureFlagsPage } from '@/pages/admin'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}

function AdminRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  const user = useAuthStore((state) => state.user)

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  if (!user?.is_admin) {
    return <Navigate to="/dashboard" replace />
  }

  return <>{children}</>
}

function App() {
  const isInitialized = useAuthStore((state) => state.isInitialized)
  const validateSession = useAuthStore((state) => state.validateSession)

  useEffect(() => {
    validateSession()
  }, [validateSession])

  // Show loading while validating session
  if (!isInitialized) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-muted-foreground">Loading...</div>
      </div>
    )
  }

  return (
    <>
      <Routes>
        {/* Auth routes */}
        <Route element={<AuthLayout />}>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
        </Route>

        {/* Protected routes */}
        <Route
          element={
            <ProtectedRoute>
              <DashboardLayout />
            </ProtectedRoute>
          }
        >
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/settings" element={<SettingsPage />} />

          {/* Admin routes */}
          <Route
            path="/admin/users"
            element={
              <AdminRoute>
                <UsersPage />
              </AdminRoute>
            }
          />
          <Route
            path="/admin/feature-flags"
            element={
              <AdminRoute>
                <FeatureFlagsPage />
              </AdminRoute>
            }
          />
        </Route>
      </Routes>
      <Toaster />
    </>
  )
}

export default App
