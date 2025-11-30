import { useOutletContext } from 'react-router-dom'
import { Users, FolderKanban, Key, Webhook, Activity } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useOrgMembers, useProjects, useAPIKeys, useWebhooks, useAuditLogs } from '@/hooks/useApi'
import type { Organization } from '@/types'

interface OrgContext {
  org: Organization
}

export function OrgOverviewPage() {
  const context = useOutletContext<OrgContext>()
  const org = context?.org
  const { data: members } = useOrgMembers(org?.id ?? '')
  const { data: projects } = useProjects({ org_id: org?.id })
  const { data: apiKeys } = useAPIKeys(org?.id ?? '')
  const { data: webhooks } = useWebhooks(org?.id ?? '')
  const { data: auditLogs } = useAuditLogs(org?.id ?? '', { limit: 5 })

  if (!org) return null

  const stats = [
    { name: 'Team Members', value: members?.length ?? 0, max: org?.max_members, icon: Users },
    { name: 'Projects', value: projects?.items?.length ?? 0, max: org?.max_projects, icon: FolderKanban },
    { name: 'API Keys', value: apiKeys?.length ?? 0, icon: Key },
    { name: 'Webhooks', value: webhooks?.length ?? 0, icon: Webhook },
  ]

  return (
    <div className="space-y-6">
      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <Card key={stat.name}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">{stat.name}</CardTitle>
              <stat.icon className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {stat.value}
                {stat.max && <span className="text-sm font-normal text-muted-foreground">/{stat.max}</span>}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Recent Activity */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5" />
            Recent Activity
          </CardTitle>
          <CardDescription>Latest changes in this organization</CardDescription>
        </CardHeader>
        <CardContent>
          {auditLogs?.length === 0 ? (
            <p className="text-muted-foreground text-center py-8">No activity yet</p>
          ) : (
            <div className="space-y-4">
              {auditLogs?.map((log) => (
                <div key={log.id} className="flex items-start gap-3 text-sm">
                  <div className="h-8 w-8 rounded-full bg-muted flex items-center justify-center text-xs font-medium">
                    {log.actor_email?.charAt(0).toUpperCase() || '?'}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p>{log.summary || `${log.action} ${log.resource_type}`}</p>
                    <p className="text-xs text-muted-foreground">
                      {log.actor_email || 'System'} &middot; {new Date(log.created_at).toLocaleString()}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Organization Details */}
      <Card>
        <CardHeader>
          <CardTitle>Organization Details</CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <dt className="text-muted-foreground">Name</dt>
              <dd className="font-medium">{org.name}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Slug</dt>
              <dd className="font-medium">@{org.slug}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Plan</dt>
              <dd className="font-medium capitalize">{org.plan}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Created</dt>
              <dd className="font-medium">{new Date(org.created_at).toLocaleDateString()}</dd>
            </div>
            {org.description && (
              <div className="col-span-2">
                <dt className="text-muted-foreground">Description</dt>
                <dd className="font-medium">{org.description}</dd>
              </div>
            )}
          </dl>
        </CardContent>
      </Card>
    </div>
  )
}
