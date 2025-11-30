import { Moon, Sun, Monitor } from 'lucide-react'
import { useTheme } from '@/hooks/useTheme'
import { Button } from './button'

/**
 * Theme toggle button that cycles through light -> dark -> system.
 *
 * @example
 * <ThemeToggle />
 */
export function ThemeToggle() {
  const { theme, toggleTheme, resolvedTheme } = useTheme()

  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={toggleTheme}
      title={`Current: ${theme} (${resolvedTheme})`}
    >
      {theme === 'system' ? (
        <Monitor className="h-5 w-5" />
      ) : resolvedTheme === 'dark' ? (
        <Moon className="h-5 w-5" />
      ) : (
        <Sun className="h-5 w-5" />
      )}
      <span className="sr-only">Toggle theme</span>
    </Button>
  )
}

/**
 * Theme selector dropdown for more explicit control.
 *
 * @example
 * <ThemeSelect />
 */
export function ThemeSelect() {
  const { theme, setTheme } = useTheme()

  return (
    <select
      value={theme}
      onChange={(e) => setTheme(e.target.value as 'light' | 'dark' | 'system')}
      className="rounded-md border border-input bg-background px-3 py-2 text-sm"
    >
      <option value="light">Light</option>
      <option value="dark">Dark</option>
      <option value="system">System</option>
    </select>
  )
}
