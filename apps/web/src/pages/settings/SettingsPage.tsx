import { useState } from 'react'
import { useAuthStore } from '@/stores/auth'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { AlertCircle, User, Shield, Trash2 } from 'lucide-react'
import { useUpdateProfile } from '@/hooks/useApi'
import { useToast } from '@/hooks/use-toast'

export function SettingsPage() {
  const { toast } = useToast()
  const { user, setUser } = useAuthStore()
  const updateProfile = useUpdateProfile()

  const [name, setName] = useState(user?.name || '')
  const [deleteConfirm, setDeleteConfirm] = useState('')

  const handleSave = async () => {
    if (!name.trim()) {
      toast({ title: 'Error', description: 'Name is required', variant: 'destructive' })
      return
    }

    try {
      const updated = await updateProfile.mutateAsync({ name })
      setUser(updated)
      toast({ title: 'Success', description: 'Profile updated successfully' })
    } catch {
      toast({ title: 'Error', description: 'Failed to update profile', variant: 'destructive' })
    }
  }

  const handleDeleteAccount = () => {
    if (deleteConfirm !== user?.email) {
      toast({ title: 'Error', description: 'Please type your email to confirm', variant: 'destructive' })
      return
    }
    // TODO: Implement account deletion API
    toast({ title: 'Error', description: 'Account deletion not implemented', variant: 'destructive' })
  }

  const hasChanges = name !== user?.name

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="text-3xl font-bold">Settings</h1>
        <p className="text-muted-foreground">Manage your account settings</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <User className="h-5 w-5" />
            Profile
          </CardTitle>
          <CardDescription>Update your personal information</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="name">Name</Label>
            <Input id="name" value={name} onChange={(e) => setName(e.target.value)} placeholder="Your name" />
          </div>
          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input id="email" value={user?.email || ''} disabled />
            <p className="text-xs text-muted-foreground">Email cannot be changed.</p>
          </div>
          <Button onClick={handleSave} disabled={!hasChanges || updateProfile.isPending}>
            {updateProfile.isPending ? 'Saving...' : 'Save Changes'}
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            Account Info
          </CardTitle>
          <CardDescription>Your account details</CardDescription>
        </CardHeader>
        <CardContent>
          <dl className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <dt className="text-muted-foreground">Account ID</dt>
              <dd className="font-mono text-xs">{user?.id}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Status</dt>
              <dd className="font-medium">{user?.is_active ? 'Active' : 'Inactive'}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Verified</dt>
              <dd className="font-medium">{user?.is_verified ? 'Yes' : 'No'}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Timezone</dt>
              <dd className="font-medium">{user?.timezone || 'UTC'}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Member Since</dt>
              <dd className="font-medium">
                {user?.created_at ? new Date(user.created_at).toLocaleDateString() : '-'}
              </dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Last Login</dt>
              <dd className="font-medium">
                {user?.last_login_at ? new Date(user.last_login_at).toLocaleString() : 'Never'}
              </dd>
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
          <CardDescription>Irreversible actions for your account</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>Warning</AlertTitle>
            <AlertDescription>
              Deleting your account will permanently remove all your data, organizations you own, and cannot be undone.
            </AlertDescription>
          </Alert>

          <div className="space-y-2">
            <Label htmlFor="delete-confirm">
              Type <code className="bg-muted px-1 py-0.5 rounded">{user?.email}</code> to confirm
            </Label>
            <Input
              id="delete-confirm"
              value={deleteConfirm}
              onChange={(e) => setDeleteConfirm(e.target.value)}
              placeholder={user?.email}
            />
          </div>

          <Button variant="destructive" onClick={handleDeleteAccount} disabled={deleteConfirm !== user?.email}>
            Delete Account
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
