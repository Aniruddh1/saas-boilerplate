import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Plus, FolderKanban, Trash2, Building2 } from 'lucide-react'
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
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { useProjects, useCreateProject, useDeleteProject, useOrgs } from '@/hooks/useApi'
import { useOrgStore } from '@/stores/org'
import { useToast } from '@/hooks/use-toast'

export function ProjectsPage() {
  const { toast } = useToast()
  const { currentOrg, setCurrentOrg } = useOrgStore()
  const { data: orgsData, isLoading: orgsLoading } = useOrgs()

  // Filter state - "all" means all projects
  const [filterOrgId, setFilterOrgId] = useState<string>('all')

  // Fetch projects based on filter
  const { data: projectsData, isLoading: projectsLoading } = useProjects({
    org_id: filterOrgId === 'all' ? undefined : filterOrgId
  })
  const createProject = useCreateProject()
  const deleteProject = useDeleteProject()

  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [name, setName] = useState('')
  const [slug, setSlug] = useState('')
  const [description, setDescription] = useState('')
  const [selectedOrgId, setSelectedOrgId] = useState('')

  const projects = projectsData?.projects || []
  const orgs = orgsData?.orgs || []

  // Sync filter with currentOrg on mount (only if user hasn't selected a filter yet)
  useEffect(() => {
    if (currentOrg?.id && filterOrgId === 'all') {
      setFilterOrgId(currentOrg.id)
    }
  }, [currentOrg?.id])

  // Auto-select org for creation when only one exists
  useEffect(() => {
    if (orgs.length === 1 && !selectedOrgId) {
      setSelectedOrgId(orgs[0].id)
    }
  }, [orgs, selectedOrgId])

  const handleFilterChange = (value: string) => {
    setFilterOrgId(value)
    // Update currentOrg when filter changes to a specific org
    if (value && value !== 'all') {
      const org = orgs.find(o => o.id === value)
      if (org) setCurrentOrg(org)
    }
  }

  const handleCreate = async () => {
    if (!name) {
      toast({ title: 'Error', description: 'Name is required', variant: 'destructive' })
      return
    }

    if (!selectedOrgId) {
      toast({ title: 'Error', description: 'Please select an organization', variant: 'destructive' })
      return
    }

    try {
      await createProject.mutateAsync({
        name,
        slug: slug || undefined,
        description: description || undefined,
        org_id: selectedOrgId,
      })

      // Set the filter to the org we just created in, so user sees the new project
      setFilterOrgId(selectedOrgId)
      const org = orgs.find(o => o.id === selectedOrgId)
      if (org) setCurrentOrg(org)

      toast({ title: 'Success', description: 'Project created successfully' })
      setIsCreateOpen(false)
      resetForm()
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to create project'
      toast({ title: 'Error', description: message, variant: 'destructive' })
    }
  }

  const resetForm = () => {
    setName('')
    setSlug('')
    setDescription('')
  }

  const handleDelete = async (projectId: string, projectName: string) => {
    if (!confirm(`Are you sure you want to delete "${projectName}"? This action cannot be undone.`)) return

    try {
      await deleteProject.mutateAsync(projectId)
      toast({ title: 'Success', description: 'Project deleted successfully' })
    } catch {
      toast({ title: 'Error', description: 'Failed to delete project', variant: 'destructive' })
    }
  }

  const handleNameChange = (value: string) => {
    setName(value)
    if (!slug || slug === name.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '')) {
      setSlug(value.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, ''))
    }
  }

  // Get org name for a project
  const getOrgName = (orgId: string) => {
    return orgs.find(o => o.id === orgId)?.name || 'Unknown'
  }

  const isLoading = projectsLoading || orgsLoading

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Projects</h1>
          <p className="text-muted-foreground">
            Manage your projects across organizations
          </p>
        </div>

        <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
          <DialogTrigger asChild>
            <Button disabled={orgs.length === 0}>
              <Plus className="h-4 w-4 mr-2" />
              New Project
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create Project</DialogTitle>
              <DialogDescription>Create a new project in an organization.</DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="org">Organization *</Label>
                <Select value={selectedOrgId} onValueChange={setSelectedOrgId}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select organization" />
                  </SelectTrigger>
                  <SelectContent>
                    {orgs.map((org) => (
                      <SelectItem key={org.id} value={org.id}>
                        {org.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="name">Name *</Label>
                <Input
                  id="name"
                  placeholder="My Project"
                  value={name}
                  onChange={(e) => handleNameChange(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="slug">Slug</Label>
                <Input
                  id="slug"
                  placeholder="my-project"
                  value={slug}
                  onChange={(e) => setSlug(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ''))}
                />
                <p className="text-xs text-muted-foreground">Auto-generated from name if left empty.</p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  placeholder="What is this project for?"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setIsCreateOpen(false)}>
                Cancel
              </Button>
              <Button
                onClick={handleCreate}
                disabled={createProject.isPending || !selectedOrgId || !name}
              >
                {createProject.isPending ? 'Creating...' : 'Create Project'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {/* Filter by Organization */}
      {orgs.length > 0 && (
        <div className="flex items-center gap-4">
          <Label className="text-sm text-muted-foreground">Filter by:</Label>
          <Select value={filterOrgId} onValueChange={handleFilterChange}>
            <SelectTrigger className="w-[200px]">
              <SelectValue placeholder="All organizations" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All organizations</SelectItem>
              {orgs.map((org) => (
                <SelectItem key={org.id} value={org.id}>
                  {org.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {filterOrgId !== 'all' && (
            <Button variant="ghost" size="sm" onClick={() => setFilterOrgId('all')}>
              Clear filter
            </Button>
          )}
        </div>
      )}

      {/* No orgs warning */}
      {!orgsLoading && orgs.length === 0 && (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Building2 className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">No organizations yet</h3>
            <p className="text-muted-foreground text-center mb-4">
              Create an organization first to start creating projects.
            </p>
            <Link to="/orgs">
              <Button>
                <Plus className="h-4 w-4 mr-2" />
                Create Organization
              </Button>
            </Link>
          </CardContent>
        </Card>
      )}

      {/* Projects list */}
      {orgs.length > 0 && (
        <>
          {isLoading ? (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {[1, 2, 3].map((i) => (
                <Card key={i}>
                  <CardHeader>
                    <Skeleton className="h-6 w-32" />
                    <Skeleton className="h-4 w-48" />
                  </CardHeader>
                  <CardContent>
                    <Skeleton className="h-16 w-full" />
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : projects.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <FolderKanban className="h-12 w-12 text-muted-foreground mb-4" />
                <h3 className="text-lg font-semibold mb-2">No projects yet</h3>
                <p className="text-muted-foreground text-center mb-4">
                  {filterOrgId !== 'all'
                    ? 'No projects in this organization. Create your first one!'
                    : 'Create your first project to get started.'}
                </p>
                <Button onClick={() => {
                  if (filterOrgId !== 'all') setSelectedOrgId(filterOrgId)
                  setIsCreateOpen(true)
                }}>
                  <Plus className="h-4 w-4 mr-2" />
                  Create Project
                </Button>
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {projects.map((project) => (
                <Card key={project.id} className="group relative">
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-2">
                        <FolderKanban className="h-5 w-5 text-muted-foreground" />
                        <CardTitle className="text-lg">{project.name}</CardTitle>
                      </div>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 opacity-0 group-hover:opacity-100 transition-opacity"
                        onClick={() => handleDelete(project.id, project.name)}
                      >
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </div>
                    <CardDescription className="flex items-center gap-2">
                      <span>@{project.slug}</span>
                      {filterOrgId === 'all' && (
                        <Badge variant="outline" className="text-xs">
                          <Building2 className="h-3 w-3 mr-1" />
                          {getOrgName(project.org_id)}
                        </Badge>
                      )}
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    {project.description ? (
                      <p className="text-sm text-muted-foreground line-clamp-2">{project.description}</p>
                    ) : (
                      <p className="text-sm text-muted-foreground italic">No description</p>
                    )}
                    <p className="text-xs text-muted-foreground mt-4">
                      Created {new Date(project.created_at).toLocaleDateString()}
                    </p>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}
