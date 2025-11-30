import { useState } from 'react'
import { useOutletContext } from 'react-router-dom'
import { FileText, Filter, User, Calendar, ArrowRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { useAuditLogs } from '@/hooks/useApi'
import type { Organization, AuditLogFilter } from '@/types'

interface OrgContext {
  org: Organization
}

const actionColors: Record<string, 'default' | 'secondary' | 'destructive' | 'success' | 'warning' | 'outline'> = {
  create: 'success',
  update: 'secondary',
  delete: 'destructive',
  login: 'default',
  logout: 'outline',
  login_failed: 'warning',
}

export function OrgAuditLogPage() {
  const context = useOutletContext<OrgContext>()
  const org = context?.org
  const [filters, setFilters] = useState<AuditLogFilter & { limit?: number }>({ limit: 50 })
  const [showFilters, setShowFilters] = useState(false)
  const { data: logs, isLoading } = useAuditLogs(org?.id ?? '', filters)

  if (!org) return null

  const updateFilter = (key: keyof AuditLogFilter, value: string | undefined) => {
    setFilters((prev) => ({ ...prev, [key]: value || undefined }))
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">Audit Log</h2>
          <p className="text-muted-foreground">Track all changes and activities in this organization</p>
        </div>

        <Button variant="outline" onClick={() => setShowFilters(!showFilters)}>
          <Filter className="h-4 w-4 mr-2" />
          Filters
        </Button>
      </div>

      {showFilters && (
        <Card>
          <CardContent className="pt-6">
            <div className="grid gap-4 md:grid-cols-4">
              <div className="space-y-2">
                <Label htmlFor="resource_type">Resource Type</Label>
                <Select value={filters.resource_type || ''} onValueChange={(v) => updateFilter('resource_type', v)}>
                  <SelectTrigger>
                    <SelectValue placeholder="All types" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">All types</SelectItem>
                    <SelectItem value="user">User</SelectItem>
                    <SelectItem value="project">Project</SelectItem>
                    <SelectItem value="org">Organization</SelectItem>
                    <SelectItem value="api_key">API Key</SelectItem>
                    <SelectItem value="webhook">Webhook</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="action">Action</Label>
                <Select value={filters.action || ''} onValueChange={(v) => updateFilter('action', v)}>
                  <SelectTrigger>
                    <SelectValue placeholder="All actions" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">All actions</SelectItem>
                    <SelectItem value="create">Create</SelectItem>
                    <SelectItem value="update">Update</SelectItem>
                    <SelectItem value="delete">Delete</SelectItem>
                    <SelectItem value="login">Login</SelectItem>
                    <SelectItem value="logout">Logout</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="start_date">Start Date</Label>
                <Input
                  id="start_date"
                  type="date"
                  value={filters.start_date || ''}
                  onChange={(e) => updateFilter('start_date', e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="end_date">End Date</Label>
                <Input
                  id="end_date"
                  type="date"
                  value={filters.end_date || ''}
                  onChange={(e) => updateFilter('end_date', e.target.value)}
                />
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-6 space-y-4">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="flex items-start gap-4">
                  <Skeleton className="h-10 w-10 rounded-full" />
                  <div className="flex-1">
                    <Skeleton className="h-4 w-64" />
                    <Skeleton className="h-3 w-48 mt-1" />
                  </div>
                </div>
              ))}
            </div>
          ) : logs?.length === 0 ? (
            <div className="p-12 text-center">
              <FileText className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-semibold mb-2">No activity yet</h3>
              <p className="text-muted-foreground">Activity will appear here as changes are made.</p>
            </div>
          ) : (
            <div className="divide-y">
              {logs?.map((log) => (
                <div key={log.id} className="p-4 hover:bg-muted/50">
                  <div className="flex items-start gap-4">
                    <div className="h-10 w-10 rounded-full bg-muted flex items-center justify-center flex-shrink-0">
                      {log.actor_email ? (
                        log.actor_email.charAt(0).toUpperCase()
                      ) : (
                        <User className="h-4 w-4 text-muted-foreground" />
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-medium">{log.actor_email || 'System'}</span>
                        <Badge variant={actionColors[log.action] || 'outline'} className="text-xs">
                          {log.action}
                        </Badge>
                        <span className="text-muted-foreground">{log.resource_type}</span>
                        {log.resource_id && (
                          <code className="text-xs bg-muted px-1 py-0.5 rounded">{log.resource_id.slice(0, 8)}...</code>
                        )}
                      </div>
                      {log.summary && <p className="text-sm mt-1">{log.summary}</p>}
                      {log.changes && Object.keys(log.changes).length > 0 && (
                        <div className="mt-2 text-sm">
                          {Object.entries(log.changes).map(([field, change]) => (
                            <div key={field} className="flex items-center gap-2 text-muted-foreground">
                              <span className="font-medium">{field}:</span>
                              <span className="line-through">{String(change.old || 'null')}</span>
                              <ArrowRight className="h-3 w-3" />
                              <span>{String(change.new || 'null')}</span>
                            </div>
                          ))}
                        </div>
                      )}
                      <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
                        <span className="flex items-center gap-1">
                          <Calendar className="h-3 w-3" />
                          {new Date(log.created_at).toLocaleString()}
                        </span>
                        {log.actor_ip && <span>IP: {log.actor_ip}</span>}
                        {log.request_id && <span>Request: {log.request_id.slice(0, 8)}...</span>}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
