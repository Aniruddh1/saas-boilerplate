import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { api } from '@/lib/api'

interface User {
  id: string
  email: string
  name: string
  avatar_url?: string
  is_admin: boolean
  is_active: boolean
  is_verified: boolean
  timezone?: string
  created_at?: string
  last_login_at?: string
}

interface AuthState {
  user: User | null
  accessToken: string | null
  refreshToken: string | null
  isAuthenticated: boolean
  isLoading: boolean
  isInitialized: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, name: string) => Promise<void>
  logout: () => void
  refreshAuth: () => Promise<void>
  validateSession: () => Promise<void>
  setUser: (user: User) => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,
      isInitialized: false,

      login: async (email: string, password: string) => {
        set({ isLoading: true })
        try {
          const formData = new FormData()
          formData.append('username', email)
          formData.append('password', password)

          const response = await api.post('/auth/login', formData, {
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          })

          const { access_token, refresh_token } = response.data
          set({
            accessToken: access_token,
            refreshToken: refresh_token,
            isAuthenticated: true,
          })

          // Fetch user profile
          const userResponse = await api.get('/auth/me')
          set({ user: userResponse.data })
        } finally {
          set({ isLoading: false })
        }
      },

      register: async (email: string, password: string, name: string) => {
        set({ isLoading: true })
        try {
          const response = await api.post('/auth/register', {
            email,
            password,
            name,
          })

          const { user, access_token, refresh_token } = response.data
          set({
            user,
            accessToken: access_token,
            refreshToken: refresh_token,
            isAuthenticated: true,
          })
        } finally {
          set({ isLoading: false })
        }
      },

      logout: () => {
        set({
          user: null,
          accessToken: null,
          refreshToken: null,
          isAuthenticated: false,
        })
      },

      setUser: (user: User) => {
        set({ user })
      },

      refreshAuth: async () => {
        const { refreshToken } = get()
        if (!refreshToken) return

        try {
          const response = await api.post('/auth/refresh', {
            refresh_token: refreshToken,
          })

          const { access_token, refresh_token } = response.data
          set({
            accessToken: access_token,
            refreshToken: refresh_token,
          })
        } catch {
          get().logout()
        }
      },

      validateSession: async () => {
        const { accessToken, isAuthenticated } = get()

        // No token stored - nothing to validate
        if (!accessToken || !isAuthenticated) {
          set({ isInitialized: true })
          return
        }

        // Validate token by fetching current user
        try {
          const response = await api.get('/auth/me')
          set({ user: response.data, isInitialized: true })
        } catch {
          // Token is invalid - clear auth state
          get().logout()
          set({ isInitialized: true })
        }
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
)
