import { useThemeStore } from '@/stores/theme'
import { useMediaQuery } from './useMediaQuery'

/**
 * Hook for managing theme (light/dark/system).
 *
 * @example
 * function ThemeToggle() {
 *   const { theme, setTheme, resolvedTheme } = useTheme()
 *
 *   return (
 *     <select value={theme} onChange={(e) => setTheme(e.target.value)}>
 *       <option value="light">Light</option>
 *       <option value="dark">Dark</option>
 *       <option value="system">System</option>
 *     </select>
 *   )
 * }
 */
export function useTheme() {
  const { theme, setTheme } = useThemeStore()
  const prefersDark = useMediaQuery('(prefers-color-scheme: dark)')

  // The actual theme being displayed
  const resolvedTheme = theme === 'system' ? (prefersDark ? 'dark' : 'light') : theme

  const toggleTheme = () => {
    if (theme === 'light') {
      setTheme('dark')
    } else if (theme === 'dark') {
      setTheme('system')
    } else {
      setTheme('light')
    }
  }

  return {
    theme,
    setTheme,
    resolvedTheme,
    toggleTheme,
    isDark: resolvedTheme === 'dark',
    isLight: resolvedTheme === 'light',
  }
}
