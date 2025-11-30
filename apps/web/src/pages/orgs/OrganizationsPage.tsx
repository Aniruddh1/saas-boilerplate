import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, Building2, Users, FolderKanban, ChevronRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
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
import { useOrgs, useCreateOrg } from '@/hooks/useApi'
import { useOrgStore } from '@/stores/org'
import { useToast } from '@/hooks/use-toast'

export function OrganizationsPage() {
  const navigate = useNavigate()
  const { toast } = useToast()
  const { data, isLoading, error } = useOrgs()
  const createOrg = useCreateOrg()
  const setCurrentOrg = useOrgStore((s) => s.setCurrentOrg)

  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [name, setName] = useState('')
  const [slug, setSlug] = useState('')
  const [description, setDescription] = useState('')

  const handleCreateOrg = async () => {
    if (!name || !slug) {
      toast({ title: 'Error', description: 'Name and slug are required', variant: 'destructive' })
      return
    }

    try {
      const org = await createOrg.mutateAsync({ name, slug, description: description || undefined })
      toast({ title: 'Success', description: 'Organization created successfully' })
      setIsCreateOpen(false)
      setName('')
      setSlug('')
      setDescription('')
      setCurrentOrg(org)
      navigate(`/orgs/${org.id}`)
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to create organization'
      toast({ title: 'Error', description: message, variant: 'destructive' })
    }
  }

  const handleSelectOrg = (org: typeof data extends { orgs: (infer T)[] } ? T : never) => {
    setCurrentOrg(org)
    navigate(`/orgs/${org.id}`)
  }

  // Auto-generate slug from name
  const handleNameChange = (value: string) => {
    setName(value)
    if (!slug || slug === name.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '')) {
      setSlug(value.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, ''))
    }
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-destructive">Failed to load organizations</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Organizations</h1>
          <p className="text-muted-foreground">Manage your organizations and teams</p>
        </div>

        <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              New Organization
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create Organization</DialogTitle>
              <DialogDescription>Create a new organization to manage projects and team members.</DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="name">Name</Label>
                <Input
                  id="name"
                  placeholder="My Organization"
                  value={name}
                  onChange={(e) => handleNameChange(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="slug">Slug</Label>
                <Input
                  id="slug"
                  placeholder="my-organization"
                  value={slug}
                  onChange={(e) => setSlug(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ''))}
                />
                <p className="text-xs text-muted-foreground">Used in URLs. Only lowercase letters, numbers, and hyphens.</p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="description">Description (optional)</Label>
                <Textarea
                  id="description"
                  placeholder="What is this organization for?"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setIsCreateOpen(false)}>
                Cancel
              </Button>
              <Button onClick={handleCreateOrg} disabled={createOrg.isPending}>
                {createOrg.isPending ? 'Creating...' : 'Create Organization'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-6 w-32" />
                <Skeleton className="h-4 w-48" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-20 w-full" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : data?.orgs.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Building2 className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">No organizations yet</h3>
            <p className="text-muted-foreground text-center mb-4">
              Create your first organization to start managing projects and team members.
            </p>
            <Button onClick={() => setIsCreateOpen(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Create Organization
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {data?.orgs.map((org) => (
            <Card
              key={org.id}
              className="cursor-pointer hover:border-primary transition-colors"
              onClick={() => handleSelectOrg(org)}
            >
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="flex items-center gap-2">
                    <Building2 className="h-5 w-5" />
                    {org.name}
                  </CardTitle>
                  <Badge variant="secondary">{org.plan}</Badge>
                </div>
                <CardDescription>{org.description || `@${org.slug}`}</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-between text-sm text-muted-foreground">
                  <div className="flex items-center gap-4">
                    <span className="flex items-center gap-1">
                      <Users className="h-4 w-4" />
                      {org.max_members} members
                    </span>
                    <span className="flex items-center gap-1">
                      <FolderKanban className="h-4 w-4" />
                      {org.max_projects} projects
                    </span>
                  </div>
                  <ChevronRight className="h-4 w-4" />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
