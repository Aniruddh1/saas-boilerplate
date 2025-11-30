import { create } from 'zustand'
import { persist } from 'zustand/middleware'

type Theme = 'light' | 'dark' | 'system'

interface ThemeState {
  theme: Theme
  setTheme: (theme: Theme) => void
}

// Get the resolved theme (handles 'system' preference)
function getResolvedTheme(theme: Theme): 'light' | 'dark' {
  if (theme === 'system') {
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  }
  return theme
}

// Apply theme to document
function applyTheme(theme: Theme) {
  const resolved = getResolvedTheme(theme)
  const root = window.document.documentElement

  root.classList.remove('light', 'dark')
  root.classList.add(resolved)
}

export const useThemeStore = create<ThemeState>()(
  persist(
    (set) => ({
      theme: 'system',

      setTheme: (theme: Theme) => {
        applyTheme(theme)
        set({ theme })
      },
    }),
    {
      name: 'theme-storage',
      onRehydrateStorage: () => (state) => {
        // Apply theme on initial load
        if (state) {
          applyTheme(state.theme)
        }
      },
    }
  )
)

// Initialize theme on module load (handles SSR/initial render)
if (typeof window !== 'undefined') {
  const stored = localStorage.getItem('theme-storage')
  if (stored) {
    try {
      const { state } = JSON.parse(stored)
      applyTheme(state.theme || 'system')
    } catch {
      applyTheme('system')
    }
  } else {
    applyTheme('system')
  }

  // Listen for system theme changes
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
    const currentTheme = useThemeStore.getState().theme
    if (currentTheme === 'system') {
      applyTheme('system')
    }
  })
}
