import { useState } from 'react'
import { useOutletContext, useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { AlertCircle, Trash2 } from 'lucide-react'
import { useUpdateOrg, useDeleteOrg } from '@/hooks/useApi'
import { useOrgStore } from '@/stores/org'
import { useToast } from '@/hooks/use-toast'
import type { Organization } from '@/types'

interface OrgContext {
  org: Organization
}

export function OrgSettingsPage() {
  const context = useOutletContext<OrgContext>()
  const org = context?.org
  const navigate = useNavigate()
  const { toast } = useToast()
  const { setCurrentOrg, clearCurrentOrg } = useOrgStore()
  const updateOrg = useUpdateOrg(org?.id ?? '')
  const deleteOrg = useDeleteOrg()

  const [name, setName] = useState(org?.name ?? '')
  const [description, setDescription] = useState(org?.description || '')
  const [deleteConfirm, setDeleteConfirm] = useState('')

  if (!org) return null

  const handleSave = async () => {
    try {
      const updated = await updateOrg.mutateAsync({ name, description: description || undefined })
      setCurrentOrg(updated)
      toast({ title: 'Success', description: 'Organization updated successfully' })
    } catch {
      toast({ title: 'Error', description: 'Failed to update organization', variant: 'destructive' })
    }
  }

  const handleDelete = async () => {
    if (deleteConfirm !== org.slug) {
      toast({ title: 'Error', description: 'Please type the organization slug to confirm', variant: 'destructive' })
      return
    }

    try {
      await deleteOrg.mutateAsync(org.id)
      clearCurrentOrg()
      toast({ title: 'Success', description: 'Organization deleted successfully' })
      navigate('/orgs')
    } catch {
      toast({ title: 'Error', description: 'Failed to delete organization', variant: 'destructive' })
    }
  }

  const hasChanges = name !== org.name || description !== (org.description || '')

  return (
    <div className="space-y-6 max-w-2xl">
      <Card>
        <CardHeader>
          <CardTitle>General Settings</CardTitle>
          <CardDescription>Update your organization's basic information.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="name">Organization Name</Label>
            <Input id="name" value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="slug">Slug</Label>
            <Input id="slug" value={org.slug} disabled />
            <p className="text-xs text-muted-foreground">The slug cannot be changed after creation.</p>
          </div>
          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What is this organization for?"
            />
          </div>
          <Button onClick={handleSave} disabled={!hasChanges || updateOrg.isPending}>
            {updateOrg.isPending ? 'Saving...' : 'Save Changes'}
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Plan & Limits</CardTitle>
          <CardDescription>Your current plan and usage limits.</CardDescription>
        </CardHeader>
        <CardContent>
          <dl className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <dt className="text-muted-foreground">Current Plan</dt>
              <dd className="font-medium capitalize">{org.plan}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Max Members</dt>
              <dd className="font-medium">{org.max_members}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Max Projects</dt>
              <dd className="font-medium">{org.max_projects}</dd>
            </div>
          </dl>
        </CardContent>
      </Card>

      <Card className="border-destructive">
        <CardHeader>
          <CardTitle className="text-destructive flex items-center gap-2">
            <Trash2 className="h-5 w-5" />
            Danger Zone
          </CardTitle>
          <CardDescription>Irreversible actions for this organization.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>Warning</AlertTitle>
            <AlertDescription>
              Deleting this organization will permanently remove all projects, members, API keys, webhooks, and data.
              This action cannot be undone.
            </AlertDescription>
          </Alert>

          <div className="space-y-2">
            <Label htmlFor="delete-confirm">
              Type <code className="bg-muted px-1 py-0.5 rounded">{org.slug}</code> to confirm
            </Label>
            <Input
              id="delete-confirm"
              value={deleteConfirm}
              onChange={(e) => setDeleteConfirm(e.target.value)}
              placeholder={org.slug}
            />
          </div>

          <Button
            variant="destructive"
            onClick={handleDelete}
            disabled={deleteConfirm !== org.slug || deleteOrg.isPending}
          >
            {deleteOrg.isPending ? 'Deleting...' : 'Delete Organization'}
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
