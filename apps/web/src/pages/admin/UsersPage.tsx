import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { User } from '@/types'
import { useToast } from '@/hooks/use-toast'
import { Button } from '@/components/ui/button'
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
} from '@/components/ui/dialog'
import { Shield, ShieldOff, UserCheck, UserX, Loader2 } from 'lucide-react'

export function UsersPage() {
  const { toast } = useToast()
  const queryClient = useQueryClient()
  const [selectedUser, setSelectedUser] = useState<User | null>(null)
  const [dialogAction, setDialogAction] = useState<'admin' | 'active' | null>(null)

  // Fetch users
  const { data: users, isLoading } = useQuery({
    queryKey: ['admin', 'users'],
    queryFn: async () => {
      const response = await api.get('/users')
      return response.data as User[]
    },
  })

  // Update user mutation
  const updateUser = useMutation({
    mutationFn: async ({ id, data }: { id: string; data: Partial<User> }) => {
      const response = await api.patch(`/users/${id}`, data)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'users'] })
      toast({ title: 'User updated successfully' })
      setSelectedUser(null)
      setDialogAction(null)
    },
    onError: () => {
      toast({ title: 'Failed to update user', variant: 'destructive' })
    },
  })

  const handleToggleAdmin = (user: User) => {
    setSelectedUser(user)
    setDialogAction('admin')
  }

  const handleToggleActive = (user: User) => {
    setSelectedUser(user)
    setDialogAction('active')
  }

  const confirmAction = () => {
    if (!selectedUser || !dialogAction) return

    if (dialogAction === 'admin') {
      updateUser.mutate({
        id: selectedUser.id,
        data: { is_admin: !selectedUser.is_admin },
      })
    } else if (dialogAction === 'active') {
      updateUser.mutate({
        id: selectedUser.id,
        data: { is_active: !selectedUser.is_active },
      })
    }
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
      <div>
        <h1 className="text-3xl font-bold">Users</h1>
        <p className="text-muted-foreground">Manage user accounts and permissions</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>All Users</CardTitle>
          <CardDescription>
            {users?.length || 0} users registered
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Email</TableHead>
                <TableHead>Name</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Role</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {users?.map((user) => (
                <TableRow key={user.id}>
                  <TableCell className="font-medium">{user.email}</TableCell>
                  <TableCell>{user.name}</TableCell>
                  <TableCell>
                    <div className="flex gap-2">
                      {user.is_active ? (
                        <Badge variant="default">Active</Badge>
                      ) : (
                        <Badge variant="secondary">Inactive</Badge>
                      )}
                      {user.is_verified && (
                        <Badge variant="outline">Verified</Badge>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>
                    {user.is_admin ? (
                      <Badge className="bg-purple-500">Admin</Badge>
                    ) : (
                      <Badge variant="outline">User</Badge>
                    )}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleToggleAdmin(user)}
                      >
                        {user.is_admin ? (
                          <>
                            <ShieldOff className="h-4 w-4 mr-1" />
                            Remove Admin
                          </>
                        ) : (
                          <>
                            <Shield className="h-4 w-4 mr-1" />
                            Make Admin
                          </>
                        )}
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleToggleActive(user)}
                      >
                        {user.is_active ? (
                          <>
                            <UserX className="h-4 w-4 mr-1" />
                            Deactivate
                          </>
                        ) : (
                          <>
                            <UserCheck className="h-4 w-4 mr-1" />
                            Activate
                          </>
                        )}
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Confirmation Dialog */}
      <Dialog open={!!selectedUser && !!dialogAction} onOpenChange={() => {
        setSelectedUser(null)
        setDialogAction(null)
      }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {dialogAction === 'admin'
                ? selectedUser?.is_admin
                  ? 'Remove Admin Access'
                  : 'Grant Admin Access'
                : selectedUser?.is_active
                  ? 'Deactivate User'
                  : 'Activate User'}
            </DialogTitle>
            <DialogDescription>
              {dialogAction === 'admin'
                ? selectedUser?.is_admin
                  ? `Remove admin privileges from ${selectedUser?.email}?`
                  : `Grant admin privileges to ${selectedUser?.email}? They will have full access to manage users and settings.`
                : selectedUser?.is_active
                  ? `Deactivate ${selectedUser?.email}? They will not be able to log in.`
                  : `Activate ${selectedUser?.email}? They will be able to log in again.`}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setSelectedUser(null)
                setDialogAction(null)
              }}
            >
              Cancel
            </Button>
            <Button
              onClick={confirmAction}
              disabled={updateUser.isPending}
              variant={dialogAction === 'active' && selectedUser?.is_active ? 'destructive' : 'default'}
            >
              {updateUser.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : null}
              Confirm
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
