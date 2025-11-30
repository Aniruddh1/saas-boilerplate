import { useEffect } from 'react'
import { useParams, useNavigate, Link, Outlet, useLocation } from 'react-router-dom'
import { Building2, Settings, Users, Key, Webhook, FileText, ArrowLeft } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Badge } from '@/components/ui/badge'
import { useOrg } from '@/hooks/useApi'
import { useOrgStore } from '@/stores/org'
import { cn } from '@/lib/utils'

const tabs = [
  { name: 'Overview', href: '', icon: Building2 },
  { name: 'Members', href: '/members', icon: Users },
  { name: 'API Keys', href: '/api-keys', icon: Key },
  { name: 'Webhooks', href: '/webhooks', icon: Webhook },
  { name: 'Audit Log', href: '/audit-log', icon: FileText },
  { name: 'Settings', href: '/settings', icon: Settings },
]

export function OrgDetailPage() {
  const { orgId } = useParams<{ orgId: string }>()
  const navigate = useNavigate()
  const location = useLocation()
  const { data: org, isLoading, error } = useOrg(orgId!)
  const { setCurrentOrg, currentOrg } = useOrgStore()

  useEffect(() => {
    if (org && (!currentOrg || currentOrg.id !== org.id)) {
      setCurrentOrg(org)
    }
  }, [org, currentOrg, setCurrentOrg])

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-64 space-y-4">
        <p className="text-destructive">Failed to load organization</p>
        <Button variant="outline" onClick={() => navigate('/orgs')}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Organizations
        </Button>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Skeleton className="h-10 w-10 rounded-full" />
          <div>
            <Skeleton className="h-8 w-48" />
            <Skeleton className="h-4 w-32 mt-1" />
          </div>
        </div>
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    )
  }

  if (!org) {
    return null
  }

  const basePath = `/orgs/${orgId}`
  const currentTab = location.pathname.replace(basePath, '') || ''

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => navigate('/orgs')}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center">
            <Building2 className="h-6 w-6 text-primary" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold">{org.name}</h1>
              <Badge variant="secondary">{org.plan}</Badge>
            </div>
            <p className="text-muted-foreground">@{org.slug}</p>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <nav className="flex border-b">
        {tabs.map((tab) => {
          const isActive = currentTab === tab.href
          return (
            <Link
              key={tab.name}
              to={`${basePath}${tab.href}`}
              className={cn(
                'flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 -mb-px transition-colors',
                isActive
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground hover:border-muted-foreground/50'
              )}
            >
              <tab.icon className="h-4 w-4" />
              {tab.name}
            </Link>
          )
        })}
      </nav>

      {/* Content */}
      <Outlet context={{ org }} />
    </div>
  )
}
