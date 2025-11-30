import { Link } from 'react-router-dom'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { useAuthStore } from '@/stores/auth'
import { useOrgStore } from '@/stores/org'
import { useOrgs, useProjects } from '@/hooks/useApi'
import { Building2, FolderKanban, TrendingUp, Plus, ArrowRight } from 'lucide-react'

export function DashboardPage() {
  const user = useAuthStore((state) => state.user)
  const { currentOrg } = useOrgStore()
  const { data: orgsData, isLoading: orgsLoading } = useOrgs()
  const { data: projectsData, isLoading: projectsLoading } = useProjects({ org_id: currentOrg?.id })

  const orgs = orgsData?.orgs || []
  const projects = projectsData?.projects || []

  const stats = [
    {
      name: 'Organizations',
      value: orgsLoading ? null : orgs.length,
      icon: Building2,
      href: '/orgs',
      description: orgs.length === 0 ? 'Create your first org' : `${orgs.length} organization${orgs.length !== 1 ? 's' : ''}`,
    },
    {
      name: 'Projects',
      value: projectsLoading ? null : projects.length,
      icon: FolderKanban,
      href: '/projects',
      description: projects.length === 0 ? 'No projects yet' : `${projects.length} project${projects.length !== 1 ? 's' : ''}`,
    },
    {
      name: 'Plan',
      value: currentOrg?.plan || 'Free',
      icon: TrendingUp,
      href: currentOrg ? `/orgs/${currentOrg.id}/settings` : '/orgs',
      description: 'Current subscription',
    },
  ]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <p className="text-muted-foreground">Welcome back, {user?.name}!</p>
      </div>

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {stats.map((stat) => (
          <Card key={stat.name}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">{stat.name}</CardTitle>
              <stat.icon className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              {stat.value === null ? (
                <Skeleton className="h-8 w-16" />
              ) : (
                <div className="text-2xl font-bold">{stat.value}</div>
              )}
              <p className="text-xs text-muted-foreground">{stat.description}</p>
              <Link to={stat.href}>
                <Button variant="link" className="p-0 h-auto mt-2">
                  View <ArrowRight className="ml-1 h-3 w-3" />
                </Button>
              </Link>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Quick Actions */}
      <Card>
        <CardHeader>
          <CardTitle>Quick Actions</CardTitle>
          <CardDescription>Common tasks to get started</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-3">
          {orgs.length === 0 ? (
            <Link to="/orgs">
              <Button>
                <Plus className="h-4 w-4 mr-2" />
                Create Organization
              </Button>
            </Link>
          ) : (
            <>
              <Link to="/projects">
                <Button>
                  <Plus className="h-4 w-4 mr-2" />
                  New Project
                </Button>
              </Link>
              {currentOrg && (
                <Link to={`/orgs/${currentOrg.id}/api-keys`}>
                  <Button variant="outline">
                    <Plus className="h-4 w-4 mr-2" />
                    Create API Key
                  </Button>
                </Link>
              )}
            </>
          )}
        </CardContent>
      </Card>

      {/* Recent Organizations */}
      {orgs.length > 0 && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>Your Organizations</CardTitle>
              <CardDescription>Organizations you belong to</CardDescription>
            </div>
            <Link to="/orgs">
              <Button variant="outline" size="sm">
                View All
              </Button>
            </Link>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {orgs.slice(0, 3).map((org) => (
                <Link
                  key={org.id}
                  to={`/orgs/${org.id}`}
                  className="flex items-center justify-between p-3 rounded-lg border hover:bg-muted/50 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center">
                      <Building2 className="h-5 w-5 text-primary" />
                    </div>
                    <div>
                      <p className="font-medium">{org.name}</p>
                      <p className="text-sm text-muted-foreground">@{org.slug}</p>
                    </div>
                  </div>
                  <ArrowRight className="h-4 w-4 text-muted-foreground" />
                </Link>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Recent Projects */}
      {projects.length > 0 && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>Recent Projects</CardTitle>
              <CardDescription>Your latest projects</CardDescription>
            </div>
            <Link to="/projects">
              <Button variant="outline" size="sm">
                View All
              </Button>
            </Link>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {projects.slice(0, 3).map((project) => (
                <div
                  key={project.id}
                  className="flex items-center justify-between p-3 rounded-lg border"
                >
                  <div className="flex items-center gap-3">
                    <div className="h-10 w-10 rounded-full bg-muted flex items-center justify-center">
                      <FolderKanban className="h-5 w-5 text-muted-foreground" />
                    </div>
                    <div>
                      <p className="font-medium">{project.name}</p>
                      <p className="text-sm text-muted-foreground">@{project.slug}</p>
                    </div>
                  </div>
                  <span className="text-xs text-muted-foreground">
                    {new Date(project.created_at).toLocaleDateString()}
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
