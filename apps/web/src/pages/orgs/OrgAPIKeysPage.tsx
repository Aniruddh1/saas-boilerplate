import { useState } from 'react'
import { useOutletContext } from 'react-router-dom'
import { Plus, Key, Copy, Trash2, CheckCircle, XCircle, AlertCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Skeleton } from '@/components/ui/skeleton'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
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
import { useAPIKeys, useCreateAPIKey, useRevokeAPIKey } from '@/hooks/useApi'
import { useToast } from '@/hooks/use-toast'
import { useCopy } from '@/hooks/useCopy'
import type { Organization, APIKeyWithSecret } from '@/types'

interface OrgContext {
  org: Organization
}

export function OrgAPIKeysPage() {
  const context = useOutletContext<OrgContext>()
  const org = context?.org
  const { toast } = useToast()
  const { copy, copied } = useCopy()
  const { data: apiKeys, isLoading } = useAPIKeys(org?.id ?? '')
  const createKey = useCreateAPIKey(org?.id ?? '')
  const revokeKey = useRevokeAPIKey(org?.id ?? '')

  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [name, setName] = useState('')
  const [expiresIn, setExpiresIn] = useState('90')
  const [newKey, setNewKey] = useState<APIKeyWithSecret | null>(null)

  if (!org) return null

  const handleCreate = async () => {
    if (!name) {
      toast({ title: 'Error', description: 'Name is required', variant: 'destructive' })
      return
    }

    try {
      const key = await createKey.mutateAsync({
        name,
        expires_in_days: parseInt(expiresIn) || undefined,
      })
      setNewKey(key)
      setName('')
      setExpiresIn('90')
    } catch {
      toast({ title: 'Error', description: 'Failed to create API key', variant: 'destructive' })
    }
  }

  const handleRevoke = async (keyId: string, keyName: string) => {
    if (!confirm(`Are you sure you want to revoke the API key "${keyName}"? This action cannot be undone.`)) return

    try {
      await revokeKey.mutateAsync(keyId)
      toast({ title: 'Success', description: 'API key revoked successfully' })
    } catch {
      toast({ title: 'Error', description: 'Failed to revoke API key', variant: 'destructive' })
    }
  }

  const handleCopyKey = () => {
    if (newKey?.key) {
      copy(newKey.key)
      toast({ title: 'Copied', description: 'API key copied to clipboard' })
    }
  }

  const closeNewKeyDialog = () => {
    setNewKey(null)
    setIsCreateOpen(false)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">API Keys</h2>
          <p className="text-muted-foreground">Manage API keys for programmatic access</p>
        </div>

        <Dialog open={isCreateOpen} onOpenChange={(open) => { setIsCreateOpen(open); if (!open) setNewKey(null); }}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Create API Key
            </Button>
          </DialogTrigger>
          <DialogContent>
            {newKey ? (
              <>
                <DialogHeader>
                  <DialogTitle>API Key Created</DialogTitle>
                  <DialogDescription>
                    Make sure to copy your API key now. You won't be able to see it again!
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4 py-4">
                  <Alert variant="warning">
                    <AlertCircle className="h-4 w-4" />
                    <AlertTitle>Important</AlertTitle>
                    <AlertDescription>
                      This is the only time you'll see this key. Store it securely.
                    </AlertDescription>
                  </Alert>
                  <div className="flex gap-2">
                    <Input value={newKey.key} readOnly className="font-mono text-sm" />
                    <Button variant="outline" size="icon" onClick={handleCopyKey}>
                      {copied ? <CheckCircle className="h-4 w-4 text-green-500" /> : <Copy className="h-4 w-4" />}
                    </Button>
                  </div>
                </div>
                <DialogFooter>
                  <Button onClick={closeNewKeyDialog}>Done</Button>
                </DialogFooter>
              </>
            ) : (
              <>
                <DialogHeader>
                  <DialogTitle>Create API Key</DialogTitle>
                  <DialogDescription>Create a new API key for programmatic access.</DialogDescription>
                </DialogHeader>
                <div className="space-y-4 py-4">
                  <div className="space-y-2">
                    <Label htmlFor="name">Name</Label>
                    <Input
                      id="name"
                      placeholder="Production API Key"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                    />
                    <p className="text-xs text-muted-foreground">A descriptive name to identify this key.</p>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="expires">Expiration (days)</Label>
                    <Input
                      id="expires"
                      type="number"
                      placeholder="90"
                      value={expiresIn}
                      onChange={(e) => setExpiresIn(e.target.value)}
                    />
                    <p className="text-xs text-muted-foreground">Leave empty for no expiration.</p>
                  </div>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setIsCreateOpen(false)}>
                    Cancel
                  </Button>
                  <Button onClick={handleCreate} disabled={createKey.isPending}>
                    {createKey.isPending ? 'Creating...' : 'Create Key'}
                  </Button>
                </DialogFooter>
              </>
            )}
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
          ) : apiKeys?.length === 0 ? (
            <div className="p-12 text-center">
              <Key className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-semibold mb-2">No API keys</h3>
              <p className="text-muted-foreground mb-4">Create your first API key to get started.</p>
              <Button onClick={() => setIsCreateOpen(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Create API Key
              </Button>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Key</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Last Used</TableHead>
                  <TableHead>Expires</TableHead>
                  <TableHead className="w-[50px]"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {apiKeys?.map((key) => {
                  const isExpired = key.expires_at && new Date(key.expires_at) < new Date()
                  return (
                    <TableRow key={key.id}>
                      <TableCell className="font-medium">{key.name}</TableCell>
                      <TableCell>
                        <code className="text-sm bg-muted px-2 py-1 rounded">{key.key_prefix}...</code>
                      </TableCell>
                      <TableCell>
                        {!key.is_active ? (
                          <Badge variant="destructive">
                            <XCircle className="h-3 w-3 mr-1" />
                            Revoked
                          </Badge>
                        ) : isExpired ? (
                          <Badge variant="warning">
                            <AlertCircle className="h-3 w-3 mr-1" />
                            Expired
                          </Badge>
                        ) : (
                          <Badge variant="success">
                            <CheckCircle className="h-3 w-3 mr-1" />
                            Active
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {key.last_used_at ? new Date(key.last_used_at).toLocaleDateString() : 'Never'}
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {key.expires_at ? new Date(key.expires_at).toLocaleDateString() : 'Never'}
                      </TableCell>
                      <TableCell>
                        {key.is_active && (
                          <Button variant="ghost" size="icon" onClick={() => handleRevoke(key.id, key.name)}>
                            <Trash2 className="h-4 w-4 text-destructive" />
                          </Button>
                        )}
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
