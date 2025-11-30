import { useState } from 'react'
import { useOutletContext } from 'react-router-dom'
import { Plus, Webhook, Trash2, CheckCircle, XCircle, Play, ExternalLink } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { useWebhooks, useWebhookEvents, useCreateWebhook, useDeleteWebhook, useTestWebhook } from '@/hooks/useApi'
import { useToast } from '@/hooks/use-toast'
import type { Organization } from '@/types'

interface OrgContext {
  org: Organization
}

export function OrgWebhooksPage() {
  const context = useOutletContext<OrgContext>()
  const org = context?.org
  const { toast } = useToast()
  const { data: webhooks, isLoading } = useWebhooks(org?.id ?? '')
  const { data: availableEvents } = useWebhookEvents(org?.id ?? '')
  const createWebhook = useCreateWebhook(org?.id ?? '')
  const deleteWebhook = useDeleteWebhook(org?.id ?? '')
  const testWebhook = useTestWebhook(org?.id ?? '')

  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [name, setName] = useState('')
  const [url, setUrl] = useState('')
  const [secret, setSecret] = useState('')
  const [description, setDescription] = useState('')
  const [selectedEvents, setSelectedEvents] = useState<string[]>([])
  const [testingId, setTestingId] = useState<string | null>(null)

  if (!org) return null

  const handleCreate = async () => {
    if (!name || !url) {
      toast({ title: 'Error', description: 'Name and URL are required', variant: 'destructive' })
      return
    }

    if (selectedEvents.length === 0) {
      toast({ title: 'Error', description: 'Select at least one event', variant: 'destructive' })
      return
    }

    try {
      await createWebhook.mutateAsync({
        name,
        url,
        secret: secret || undefined,
        description: description || undefined,
        events: selectedEvents,
      })
      toast({ title: 'Success', description: 'Webhook created successfully' })
      setIsCreateOpen(false)
      resetForm()
    } catch {
      toast({ title: 'Error', description: 'Failed to create webhook', variant: 'destructive' })
    }
  }

  const resetForm = () => {
    setName('')
    setUrl('')
    setSecret('')
    setDescription('')
    setSelectedEvents([])
  }

  const handleDelete = async (webhookId: string, webhookName: string) => {
    if (!confirm(`Are you sure you want to delete the webhook "${webhookName}"?`)) return

    try {
      await deleteWebhook.mutateAsync(webhookId)
      toast({ title: 'Success', description: 'Webhook deleted successfully' })
    } catch {
      toast({ title: 'Error', description: 'Failed to delete webhook', variant: 'destructive' })
    }
  }

  const handleTest = async (webhookId: string) => {
    setTestingId(webhookId)
    try {
      const result = await testWebhook.mutateAsync(webhookId)
      if (result.success) {
        toast({ title: 'Success', description: `Test ping successful (${result.response_time_ms}ms)` })
      } else {
        toast({
          title: 'Failed',
          description: result.error || `HTTP ${result.status_code}`,
          variant: 'destructive',
        })
      }
    } catch {
      toast({ title: 'Error', description: 'Failed to send test ping', variant: 'destructive' })
    } finally {
      setTestingId(null)
    }
  }

  const toggleEvent = (event: string) => {
    setSelectedEvents((prev) => (prev.includes(event) ? prev.filter((e) => e !== event) : [...prev, event]))
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">Webhooks</h2>
          <p className="text-muted-foreground">Receive real-time notifications for events</p>
        </div>

        <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Add Webhook
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>Add Webhook</DialogTitle>
              <DialogDescription>Configure a webhook endpoint to receive event notifications.</DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4 max-h-[60vh] overflow-y-auto">
              <div className="space-y-2">
                <Label htmlFor="name">Name</Label>
                <Input id="name" placeholder="My Webhook" value={name} onChange={(e) => setName(e.target.value)} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="url">Endpoint URL</Label>
                <Input
                  id="url"
                  type="url"
                  placeholder="https://example.com/webhook"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="secret">Secret (optional)</Label>
                <Input
                  id="secret"
                  type="password"
                  placeholder="Used for HMAC signature verification"
                  value={secret}
                  onChange={(e) => setSecret(e.target.value)}
                />
                <p className="text-xs text-muted-foreground">
                  If provided, requests will include an X-Webhook-Signature header for verification.
                </p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="description">Description (optional)</Label>
                <Textarea
                  id="description"
                  placeholder="What is this webhook for?"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label>Events</Label>
                <div className="grid grid-cols-2 gap-2 max-h-48 overflow-y-auto border rounded-md p-3">
                  {availableEvents?.map((event) => (
                    <label key={event} className="flex items-center gap-2 text-sm cursor-pointer hover:bg-muted p-1 rounded">
                      <input
                        type="checkbox"
                        checked={selectedEvents.includes(event)}
                        onChange={() => toggleEvent(event)}
                        className="rounded"
                      />
                      {event}
                    </label>
                  ))}
                </div>
                <p className="text-xs text-muted-foreground">{selectedEvents.length} events selected</p>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setIsCreateOpen(false)}>
                Cancel
              </Button>
              <Button onClick={handleCreate} disabled={createWebhook.isPending}>
                {createWebhook.isPending ? 'Creating...' : 'Create Webhook'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-6 space-y-4">
              {[1, 2].map((i) => (
                <div key={i} className="flex items-center gap-4">
                  <Skeleton className="h-10 w-10 rounded" />
                  <div className="flex-1">
                    <Skeleton className="h-4 w-32" />
                    <Skeleton className="h-3 w-48 mt-1" />
                  </div>
                </div>
              ))}
            </div>
          ) : webhooks?.length === 0 ? (
            <div className="p-12 text-center">
              <Webhook className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-semibold mb-2">No webhooks configured</h3>
              <p className="text-muted-foreground mb-4">Add a webhook to receive event notifications.</p>
              <Button onClick={() => setIsCreateOpen(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Add Webhook
              </Button>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Webhook</TableHead>
                  <TableHead>Events</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Last Triggered</TableHead>
                  <TableHead className="w-[120px]"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {webhooks?.map((webhook) => (
                  <TableRow key={webhook.id}>
                    <TableCell>
                      <div>
                        <p className="font-medium">{webhook.name}</p>
                        <p className="text-sm text-muted-foreground flex items-center gap-1">
                          {webhook.url}
                          <ExternalLink className="h-3 w-3" />
                        </p>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        {webhook.events.slice(0, 2).map((event) => (
                          <Badge key={event} variant="outline" className="text-xs">
                            {event}
                          </Badge>
                        ))}
                        {webhook.events.length > 2 && (
                          <Badge variant="outline" className="text-xs">
                            +{webhook.events.length - 2} more
                          </Badge>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      {webhook.is_active ? (
                        webhook.failure_count > 0 ? (
                          <Badge variant="warning">
                            {webhook.failure_count} failures
                          </Badge>
                        ) : (
                          <Badge variant="success">
                            <CheckCircle className="h-3 w-3 mr-1" />
                            Active
                          </Badge>
                        )
                      ) : (
                        <Badge variant="destructive">
                          <XCircle className="h-3 w-3 mr-1" />
                          Disabled
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {webhook.last_triggered_at ? new Date(webhook.last_triggered_at).toLocaleString() : 'Never'}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleTest(webhook.id)}
                          disabled={testingId === webhook.id}
                        >
                          <Play className={`h-4 w-4 ${testingId === webhook.id ? 'animate-pulse' : ''}`} />
                        </Button>
                        <Button variant="ghost" size="icon" onClick={() => handleDelete(webhook.id, webhook.name)}>
                          <Trash2 className="h-4 w-4 text-destructive" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
