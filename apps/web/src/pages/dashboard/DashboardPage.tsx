import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { useAuthStore } from '@/stores/auth'
import { api } from '@/lib/api'
import { Settings, User, Activity, Flag, Sparkles, Rocket, Zap, Shield } from 'lucide-react'

export function DashboardPage() {
  const user = useAuthStore((state) => state.user)

  // Fetch feature flags for current user
  const { data: flags } = useQuery({
    queryKey: ['features', 'me'],
    queryFn: async () => {
      try {
        const response = await api.get('/features/me')
        return response.data as Record<string, boolean>
      } catch {
        // Feature flags endpoint might not exist yet
        return {}
      }
    },
  })

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <p className="text-muted-foreground">Welcome back, {user?.name}!</p>
      </div>

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Profile</CardTitle>
            <User className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{user?.name}</div>
            <p className="text-xs text-muted-foreground">{user?.email}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Status</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <div className="text-2xl font-bold">Active</div>
              {user?.is_admin && (
                <Badge className="bg-purple-500">
                  <Shield className="h-3 w-3 mr-1" />
                  Admin
                </Badge>
              )}
            </div>
            <p className="text-xs text-muted-foreground">Account status</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Settings</CardTitle>
            <Settings className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground mb-2">Manage your account</p>
            <Link to="/settings">
              <Button variant="outline" size="sm">
                Go to Settings
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>

      {/* Feature Flag Demo */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Flag className="h-5 w-5" />
            Feature Flags Demo
          </CardTitle>
          <CardDescription>
            These cards appear based on feature flags. {user?.is_admin && (
              <Link to="/admin/feature-flags" className="text-primary hover:underline">
                Manage flags
              </Link>
            )}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-3">
            {/* Beta Feature Card */}
            {flags?.beta_feature && (
              <Card className="border-blue-500/50 bg-blue-500/5">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm flex items-center gap-2">
                    <Sparkles className="h-4 w-4 text-blue-500" />
                    Beta Feature
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-xs text-muted-foreground">
                    You have access to beta features!
                  </p>
                  <Badge variant="outline" className="mt-2 text-blue-500 border-blue-500">
                    beta_feature: ON
                  </Badge>
                </CardContent>
              </Card>
            )}

            {/* New Dashboard Card */}
            {flags?.new_dashboard && (
              <Card className="border-green-500/50 bg-green-500/5">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm flex items-center gap-2">
                    <Rocket className="h-4 w-4 text-green-500" />
                    New Dashboard
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-xs text-muted-foreground">
                    Experience the new dashboard UI!
                  </p>
                  <Badge variant="outline" className="mt-2 text-green-500 border-green-500">
                    new_dashboard: ON
                  </Badge>
                </CardContent>
              </Card>
            )}

            {/* Premium Feature Card */}
            {flags?.premium_feature && (
              <Card className="border-yellow-500/50 bg-yellow-500/5">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm flex items-center gap-2">
                    <Zap className="h-4 w-4 text-yellow-500" />
                    Premium Feature
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-xs text-muted-foreground">
                    Premium features enabled!
                  </p>
                  <Badge variant="outline" className="mt-2 text-yellow-500 border-yellow-500">
                    premium_feature: ON
                  </Badge>
                </CardContent>
              </Card>
            )}

            {/* Show message if no flags are enabled */}
            {(!flags || Object.keys(flags).length === 0 || !Object.values(flags).some(v => v)) && (
              <div className="col-span-full text-center py-4 text-muted-foreground">
                <Flag className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">No feature flags enabled for your account.</p>
                {user?.is_admin && (
                  <p className="text-xs mt-1">
                    <Link to="/admin/feature-flags" className="text-primary hover:underline">
                      Create some flags
                    </Link>
                    {' '}to see them appear here.
                  </p>
                )}
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Getting Started */}
      <Card>
        <CardHeader>
          <CardTitle>Getting Started</CardTitle>
          <CardDescription>Start building your application</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            This is a minimal boilerplate with enterprise-grade authorization and feature flags.
          </p>
          <div className="flex flex-wrap gap-3">
            <Link to="/settings">
              <Button variant="outline">
                <Settings className="h-4 w-4 mr-2" />
                Account Settings
              </Button>
            </Link>
            {user?.is_admin && (
              <>
                <Link to="/admin/users">
                  <Button variant="outline">
                    <User className="h-4 w-4 mr-2" />
                    Manage Users
                  </Button>
                </Link>
                <Link to="/admin/feature-flags">
                  <Button variant="outline">
                    <Flag className="h-4 w-4 mr-2" />
                    Feature Flags
                  </Button>
                </Link>
              </>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
