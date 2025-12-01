import { Outlet, Link, useLocation } from 'react-router-dom'
import { useAuthStore } from '@/stores/auth'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ThemeToggle } from '@/components/ui/theme-toggle'
import { LayoutDashboard, Settings, LogOut, Users, Flag, Shield } from 'lucide-react'
import { cn } from '@/lib/utils'

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Settings', href: '/settings', icon: Settings },
]

const adminNavigation = [
  { name: 'Users', href: '/admin/users', icon: Users },
  { name: 'Feature Flags', href: '/admin/feature-flags', icon: Flag },
]

export function DashboardLayout() {
  const location = useLocation()
  const { user, logout } = useAuthStore()
  const isAdmin = user?.is_admin || false

  return (
    <div className="min-h-screen flex">
      {/* Sidebar */}
      <div className="w-64 border-r bg-card flex flex-col">
        {/* Logo */}
        <div className="h-16 flex items-center px-6 border-b">
          <span className="text-xl font-bold">App</span>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-1">
          {navigation.map((item) => {
            const isActive = location.pathname === item.href || location.pathname.startsWith(item.href + '/')
            return (
              <Link
                key={item.name}
                to={item.href}
                className={cn(
                  'flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                )}
              >
                <item.icon className="h-5 w-5" />
                {item.name}
              </Link>
            )
          })}

          {/* Admin Section */}
          {isAdmin && (
            <>
              <div className="pt-4 pb-2">
                <div className="flex items-center gap-2 px-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  <Shield className="h-3 w-3" />
                  Admin
                </div>
              </div>
              {adminNavigation.map((item) => {
                const isActive = location.pathname === item.href || location.pathname.startsWith(item.href + '/')
                return (
                  <Link
                    key={item.name}
                    to={item.href}
                    className={cn(
                      'flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors',
                      isActive
                        ? 'bg-primary text-primary-foreground'
                        : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                    )}
                  >
                    <item.icon className="h-5 w-5" />
                    {item.name}
                  </Link>
                )
              })}
            </>
          )}
        </nav>

        {/* User section */}
        <div className="p-4 border-t">
          <div className="flex items-center gap-3 mb-3">
            <div className="h-10 w-10 rounded-full bg-muted flex items-center justify-center">
              {user?.name?.charAt(0).toUpperCase() || user?.email?.charAt(0).toUpperCase()}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <p className="text-sm font-medium truncate">{user?.name}</p>
                {isAdmin && (
                  <Badge variant="secondary" className="text-xs px-1.5 py-0">
                    Admin
                  </Badge>
                )}
              </div>
              <p className="text-xs text-muted-foreground truncate">{user?.email}</p>
            </div>
          </div>
          <Button variant="outline" size="sm" className="w-full" onClick={logout}>
            <LogOut className="h-4 w-4 mr-2" />
            Logout
          </Button>
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <header className="h-16 border-b flex items-center justify-end px-6">
          <ThemeToggle />
        </header>

        <main className="flex-1 p-6 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
