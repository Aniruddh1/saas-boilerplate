import { useState } from 'react'
import { useOutletContext } from 'react-router-dom'
import { Plus, MoreVertical, Shield, User, Eye, Crown, Trash2 } from 'lucide-react'
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
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { useOrgMembers, useInviteMember, useRemoveMember, useUpdateMemberRole } from '@/hooks/useApi'
import { useToast } from '@/hooks/use-toast'
import type { Organization } from '@/types'

interface OrgContext {
  org: Organization
}

const roleIcons = {
  owner: Crown,
  admin: Shield,
  member: User,
  viewer: Eye,
}

const roleColors = {
  owner: 'default',
  admin: 'secondary',
  member: 'outline',
  viewer: 'outline',
} as const

export function OrgMembersPage() {
  const context = useOutletContext<OrgContext>()
  const org = context?.org
  const { toast } = useToast()
  const { data: members, isLoading } = useOrgMembers(org?.id ?? '')
  const inviteMember = useInviteMember(org?.id ?? '')
  const removeMember = useRemoveMember(org?.id ?? '')
  const updateRole = useUpdateMemberRole(org?.id ?? '')

  const [isInviteOpen, setIsInviteOpen] = useState(false)
  const [email, setEmail] = useState('')
  const [role, setRole] = useState('member')

  if (!org) return null

  const handleInvite = async () => {
    if (!email) {
      toast({ title: 'Error', description: 'Email is required', variant: 'destructive' })
      return
    }

    try {
      await inviteMember.mutateAsync({ email, role })
      toast({ title: 'Success', description: 'Invitation sent successfully' })
      setIsInviteOpen(false)
      setEmail('')
      setRole('member')
    } catch {
      toast({ title: 'Error', description: 'Failed to send invitation', variant: 'destructive' })
    }
  }

  const handleRemove = async (userId: string, userName: string) => {
    if (!confirm(`Are you sure you want to remove ${userName} from the organization?`)) return

    try {
      await removeMember.mutateAsync(userId)
      toast({ title: 'Success', description: 'Member removed successfully' })
    } catch {
      toast({ title: 'Error', description: 'Failed to remove member', variant: 'destructive' })
    }
  }

  const handleRoleChange = async (userId: string, newRole: string) => {
    try {
      await updateRole.mutateAsync({ userId, role: newRole })
      toast({ title: 'Success', description: 'Role updated successfully' })
    } catch {
      toast({ title: 'Error', description: 'Failed to update role', variant: 'destructive' })
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">Team Members</h2>
          <p className="text-muted-foreground">
            {members?.length ?? 0} of {org.max_members} members
          </p>
        </div>

        <Dialog open={isInviteOpen} onOpenChange={setIsInviteOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Invite Member
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Invite Team Member</DialogTitle>
              <DialogDescription>Send an invitation to join this organization.</DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="email">Email Address</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="colleague@company.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="role">Role</Label>
                <Select value={role} onValueChange={setRole}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="admin">Admin - Full access</SelectItem>
                    <SelectItem value="member">Member - Standard access</SelectItem>
                    <SelectItem value="viewer">Viewer - Read-only access</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setIsInviteOpen(false)}>
                Cancel
              </Button>
              <Button onClick={handleInvite} disabled={inviteMember.isPending}>
                {inviteMember.isPending ? 'Sending...' : 'Send Invitation'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-6 space-y-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="flex items-center gap-4">
                  <Skeleton className="h-10 w-10 rounded-full" />
                  <div className="flex-1">
                    <Skeleton className="h-4 w-32" />
                    <Skeleton className="h-3 w-48 mt-1" />
                  </div>
                </div>
              ))}
            </div>
          ) : members?.length === 0 ? (
            <div className="p-12 text-center">
              <p className="text-muted-foreground">No team members yet</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Member</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead>Joined</TableHead>
                  <TableHead className="w-[50px]"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {members?.map((member) => {
                  const RoleIcon = roleIcons[member.role] || User
                  return (
                    <TableRow key={member.id}>
                      <TableCell>
                        <div className="flex items-center gap-3">
                          <div className="h-10 w-10 rounded-full bg-muted flex items-center justify-center">
                            {member.user.name?.charAt(0).toUpperCase() || member.user.email.charAt(0).toUpperCase()}
                          </div>
                          <div>
                            <p className="font-medium">{member.user.name || 'Unnamed'}</p>
                            <p className="text-sm text-muted-foreground">{member.user.email}</p>
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>
                        {member.role === 'owner' ? (
                          <Badge variant={roleColors[member.role]}>
                            <RoleIcon className="h-3 w-3 mr-1" />
                            {member.role}
                          </Badge>
                        ) : (
                          <Select value={member.role} onValueChange={(r) => handleRoleChange(member.user_id, r)}>
                            <SelectTrigger className="w-32">
                              <Badge variant={roleColors[member.role]}>
                                <RoleIcon className="h-3 w-3 mr-1" />
                                {member.role}
                              </Badge>
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="admin">Admin</SelectItem>
                              <SelectItem value="member">Member</SelectItem>
                              <SelectItem value="viewer">Viewer</SelectItem>
                            </SelectContent>
                          </Select>
                        )}
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {new Date(member.created_at).toLocaleDateString()}
                      </TableCell>
                      <TableCell>
                        {member.role !== 'owner' && (
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleRemove(member.user_id, member.user.name || member.user.email)}
                          >
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
