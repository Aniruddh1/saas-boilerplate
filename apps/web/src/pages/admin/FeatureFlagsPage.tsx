import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { api } from '@/lib/api'
import { FeatureFlag } from '@/types'
import { useToast } from '@/hooks/use-toast'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Flag, Plus, Trash2, ToggleLeft, ToggleRight, Loader2, Percent } from 'lucide-react'

const createFlagSchema = z.object({
  key: z.string().min(1, 'Key is required').regex(/^[a-z][a-z0-9_]*$/, 'Key must be lowercase with underscores'),
  name: z.string().min(1, 'Name is required'),
  description: z.string().optional(),
  enabled: z.boolean().default(false),
  percentage: z.number().min(0).max(100).default(100),
})

type CreateFlagForm = z.infer<typeof createFlagSchema>

export function FeatureFlagsPage() {
  const { toast } = useToast()
  const queryClient = useQueryClient()
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [deleteFlag, setDeleteFlag] = useState<FeatureFlag | null>(null)

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<CreateFlagForm>({
    resolver: zodResolver(createFlagSchema),
    defaultValues: {
      enabled: false,
      percentage: 100,
    },
  })

  // Fetch feature flags
  const { data: flags, isLoading } = useQuery({
    queryKey: ['admin', 'feature-flags'],
    queryFn: async () => {
      const response = await api.get('/features')
      return response.data as FeatureFlag[]
    },
  })

  // Create flag mutation
  const createFlag = useMutation({
    mutationFn: async (data: CreateFlagForm) => {
      const response = await api.post('/features', data)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'feature-flags'] })
      toast({ title: 'Feature flag created' })
      setIsCreateOpen(false)
      reset()
    },
    onError: () => {
      toast({ title: 'Failed to create flag', variant: 'destructive' })
    },
  })

  // Toggle flag mutation
  const toggleFlag = useMutation({
    mutationFn: async ({ key, enabled }: { key: string; enabled: boolean }) => {
      const response = await api.patch(`/features/${key}`, { enabled })
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'feature-flags'] })
      toast({ title: 'Feature flag updated' })
    },
    onError: () => {
      toast({ title: 'Failed to update flag', variant: 'destructive' })
    },
  })

  // Update percentage mutation
  const updatePercentage = useMutation({
    mutationFn: async ({ key, percentage }: { key: string; percentage: number }) => {
      const response = await api.patch(`/features/${key}`, { percentage })
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'feature-flags'] })
      toast({ title: 'Rollout percentage updated' })
    },
    onError: () => {
      toast({ title: 'Failed to update percentage', variant: 'destructive' })
    },
  })

  // Delete flag mutation
  const deleteFlagMutation = useMutation({
    mutationFn: async (key: string) => {
      await api.delete(`/features/${key}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'feature-flags'] })
      toast({ title: 'Feature flag deleted' })
      setDeleteFlag(null)
    },
    onError: () => {
      toast({ title: 'Failed to delete flag', variant: 'destructive' })
    },
  })

  const onSubmit = (data: CreateFlagForm) => {
    createFlag.mutate(data)
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Feature Flags</h1>
          <p className="text-muted-foreground">Control feature rollouts and experiments</p>
        </div>
        <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Create Flag
            </Button>
          </DialogTrigger>
          <DialogContent>
            <form onSubmit={handleSubmit(onSubmit)}>
              <DialogHeader>
                <DialogTitle>Create Feature Flag</DialogTitle>
                <DialogDescription>
                  Create a new feature flag for controlled rollouts.
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <Label htmlFor="key">Key</Label>
                  <Input
                    id="key"
                    placeholder="new_dashboard"
                    {...register('key')}
                  />
                  {errors.key && (
                    <p className="text-sm text-destructive">{errors.key.message}</p>
                  )}
                  <p className="text-xs text-muted-foreground">
                    Lowercase with underscores (e.g., new_dashboard)
                  </p>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="name">Name</Label>
                  <Input
                    id="name"
                    placeholder="New Dashboard"
                    {...register('name')}
                  />
                  {errors.name && (
                    <p className="text-sm text-destructive">{errors.name.message}</p>
                  )}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="description">Description (optional)</Label>
                  <Input
                    id="description"
                    placeholder="Enables the new dashboard UI"
                    {...register('description')}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="percentage">Rollout Percentage</Label>
                  <div className="flex items-center gap-2">
                    <Input
                      id="percentage"
                      type="number"
                      min={0}
                      max={100}
                      {...register('percentage', { valueAsNumber: true })}
                      className="w-24"
                    />
                    <span className="text-muted-foreground">%</span>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Percentage of users who will see this feature when enabled
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="enabled"
                    {...register('enabled')}
                    className="h-4 w-4"
                  />
                  <Label htmlFor="enabled">Enable immediately</Label>
                </div>
              </div>
              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => setIsCreateOpen(false)}>
                  Cancel
                </Button>
                <Button type="submit" disabled={createFlag.isPending}>
                  {createFlag.isPending && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
                  Create
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Flag className="h-5 w-5" />
            All Flags
          </CardTitle>
          <CardDescription>
            {flags?.length || 0} feature flags configured
          </CardDescription>
        </CardHeader>
        <CardContent>
          {flags && flags.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Key</TableHead>
                  <TableHead>Name</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Rollout</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {flags.map((flag) => (
                  <TableRow key={flag.id}>
                    <TableCell className="font-mono text-sm">{flag.key}</TableCell>
                    <TableCell>
                      <div>
                        <div className="font-medium">{flag.name}</div>
                        {flag.description && (
                          <div className="text-sm text-muted-foreground">{flag.description}</div>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      {flag.enabled ? (
                        <Badge className="bg-green-500">Enabled</Badge>
                      ) : (
                        <Badge variant="secondary">Disabled</Badge>
                      )}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Percent className="h-4 w-4 text-muted-foreground" />
                        <Select
                          value={flag.percentage.toString()}
                          onValueChange={(value) => {
                            updatePercentage.mutate({
                              key: flag.key,
                              percentage: parseInt(value),
                            })
                          }}
                        >
                          <SelectTrigger className="w-20 h-8">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {[0, 10, 25, 50, 75, 100].map((p) => (
                              <SelectItem key={p} value={p.toString()}>
                                {p}%
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => toggleFlag.mutate({
                            key: flag.key,
                            enabled: !flag.enabled,
                          })}
                          disabled={toggleFlag.isPending}
                        >
                          {flag.enabled ? (
                            <>
                              <ToggleRight className="h-4 w-4 mr-1" />
                              Disable
                            </>
                          ) : (
                            <>
                              <ToggleLeft className="h-4 w-4 mr-1" />
                              Enable
                            </>
                          )}
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setDeleteFlag(flag)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              <Flag className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No feature flags yet.</p>
              <p className="text-sm">Create your first flag to start controlling feature rollouts.</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Delete Confirmation Dialog */}
      <Dialog open={!!deleteFlag} onOpenChange={() => setDeleteFlag(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Feature Flag</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete <strong>{deleteFlag?.key}</strong>? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteFlag(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => deleteFlag && deleteFlagMutation.mutate(deleteFlag.key)}
              disabled={deleteFlagMutation.isPending}
            >
              {deleteFlagMutation.isPending && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
