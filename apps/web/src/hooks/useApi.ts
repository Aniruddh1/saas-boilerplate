/**
 * TanStack Query hooks for API data fetching.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type {
  User,
  Organization,
  OrgMember,
  CreateOrgData,
  UpdateOrgData,
  Project,
  CreateProjectData,
  UpdateProjectData,
  ProjectsResponse,
  APIKey,
  APIKeyWithSecret,
  CreateAPIKeyData,
  Webhook,
  WebhookLog,
  CreateWebhookData,
  UpdateWebhookData,
  WebhookTestResult,
  AuditLog,
  AuditLogFilter,
  OrgsResponse,
  PaginatedResponse,
} from '@/types'

// ============ Query Keys ============

export const queryKeys = {
  user: {
    current: ['user', 'current'] as const,
    byId: (id: string) => ['user', id] as const,
  },
  orgs: {
    all: ['orgs'] as const,
    list: (filters?: Record<string, unknown>) => ['orgs', 'list', filters] as const,
    byId: (id: string) => ['orgs', id] as const,
    members: (orgId: string) => ['orgs', orgId, 'members'] as const,
  },
  projects: {
    all: ['projects'] as const,
    list: (filters?: Record<string, unknown>) => ['projects', 'list', filters] as const,
    byId: (id: string) => ['projects', id] as const,
    byOrg: (orgId: string) => ['projects', 'org', orgId] as const,
  },
  apiKeys: {
    all: ['apiKeys'] as const,
    byOrg: (orgId: string) => ['apiKeys', 'org', orgId] as const,
  },
  webhooks: {
    all: ['webhooks'] as const,
    byOrg: (orgId: string) => ['webhooks', 'org', orgId] as const,
    byId: (orgId: string, id: string) => ['webhooks', orgId, id] as const,
    logs: (orgId: string, webhookId: string) => ['webhooks', orgId, webhookId, 'logs'] as const,
    events: (orgId: string) => ['webhooks', orgId, 'events'] as const,
  },
  auditLogs: {
    all: ['auditLogs'] as const,
    byOrg: (orgId: string, filters?: AuditLogFilter) => ['auditLogs', 'org', orgId, filters] as const,
    byId: (orgId: string, id: string) => ['auditLogs', orgId, id] as const,
  },
}

// ============ User Hooks ============

export function useCurrentUser() {
  return useQuery({
    queryKey: queryKeys.user.current,
    queryFn: async () => {
      const { data } = await api.get<User>('/users/me')
      return data
    },
    staleTime: 5 * 60 * 1000,
  })
}

export function useUpdateProfile() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (data: { name?: string }) => {
      const response = await api.patch<User>('/users/me', data)
      return response.data
    },
    onSuccess: (updatedUser) => {
      queryClient.setQueryData(queryKeys.user.current, updatedUser)
    },
  })
}

// ============ Organizations Hooks ============

export function useOrgs(filters?: { page?: number; per_page?: number }) {
  return useQuery({
    queryKey: queryKeys.orgs.list(filters),
    queryFn: async () => {
      const { data } = await api.get<OrgsResponse>('/orgs', { params: filters })
      return data
    },
  })
}

export function useOrg(id: string) {
  return useQuery({
    queryKey: queryKeys.orgs.byId(id),
    queryFn: async () => {
      const { data } = await api.get<Organization>(`/orgs/${id}`)
      return data
    },
    enabled: !!id,
  })
}

export function useCreateOrg() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (data: CreateOrgData) => {
      const response = await api.post<Organization>('/orgs', data)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.orgs.all })
    },
  })
}

export function useUpdateOrg(orgId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (data: UpdateOrgData) => {
      const response = await api.patch<Organization>(`/orgs/${orgId}`, data)
      return response.data
    },
    onSuccess: (org) => {
      queryClient.setQueryData(queryKeys.orgs.byId(orgId), org)
      queryClient.invalidateQueries({ queryKey: queryKeys.orgs.all })
    },
  })
}

export function useDeleteOrg() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (orgId: string) => {
      await api.delete(`/orgs/${orgId}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.orgs.all })
    },
  })
}

export function useOrgMembers(orgId: string) {
  return useQuery({
    queryKey: queryKeys.orgs.members(orgId),
    queryFn: async () => {
      const { data } = await api.get<OrgMember[]>(`/orgs/${orgId}/members`)
      return data
    },
    enabled: !!orgId,
  })
}

export function useInviteMember(orgId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (data: { email: string; role: string }) => {
      const response = await api.post(`/orgs/${orgId}/members`, data)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.orgs.members(orgId) })
    },
  })
}

export function useRemoveMember(orgId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (userId: string) => {
      await api.delete(`/orgs/${orgId}/members/${userId}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.orgs.members(orgId) })
    },
  })
}

export function useUpdateMemberRole(orgId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ userId, role }: { userId: string; role: string }) => {
      const response = await api.patch(`/orgs/${orgId}/members/${userId}`, { role })
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.orgs.members(orgId) })
    },
  })
}

// ============ Projects Hooks ============

export function useProjects(filters?: { page?: number; per_page?: number; org_id?: string }) {
  return useQuery({
    queryKey: queryKeys.projects.list(filters),
    queryFn: async () => {
      const { data } = await api.get<ProjectsResponse>('/projects', { params: filters })
      return data
    },
  })
}

export function useProject(id: string) {
  return useQuery({
    queryKey: queryKeys.projects.byId(id),
    queryFn: async () => {
      const { data } = await api.get<Project>(`/projects/${id}`)
      return data
    },
    enabled: !!id,
  })
}

export function useCreateProject() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (data: CreateProjectData) => {
      const response = await api.post<Project>('/projects', data)
      return response.data
    },
    onSuccess: () => {
      // Invalidate ALL project queries (not just active ones) so switching filters shows fresh data
      queryClient.invalidateQueries({
        queryKey: queryKeys.projects.all,
        refetchType: 'all'
      })
    },
  })
}

export function useUpdateProject(id: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (data: UpdateProjectData) => {
      const response = await api.patch<Project>(`/projects/${id}`, data)
      return response.data
    },
    onSuccess: (project) => {
      queryClient.setQueryData(queryKeys.projects.byId(id), project)
      queryClient.invalidateQueries({
        queryKey: queryKeys.projects.all,
        refetchType: 'all'
      })
    },
  })
}

export function useDeleteProject() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/projects/${id}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.projects.all,
        refetchType: 'all'
      })
    },
  })
}

// ============ API Keys Hooks ============

export function useAPIKeys(orgId: string) {
  return useQuery({
    queryKey: queryKeys.apiKeys.byOrg(orgId),
    queryFn: async () => {
      const { data } = await api.get<APIKey[]>(`/orgs/${orgId}/api-keys`)
      return data
    },
    enabled: !!orgId,
  })
}

export function useCreateAPIKey(orgId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (data: Omit<CreateAPIKeyData, 'org_id'>) => {
      const response = await api.post<APIKeyWithSecret>(`/orgs/${orgId}/api-keys`, data)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.apiKeys.byOrg(orgId) })
    },
  })
}

export function useRevokeAPIKey(orgId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (keyId: string) => {
      await api.delete(`/orgs/${orgId}/api-keys/${keyId}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.apiKeys.byOrg(orgId) })
    },
  })
}

// ============ Webhooks Hooks ============

export function useWebhooks(orgId: string) {
  return useQuery({
    queryKey: queryKeys.webhooks.byOrg(orgId),
    queryFn: async () => {
      const { data } = await api.get<Webhook[]>(`/orgs/${orgId}/webhooks`)
      return data
    },
    enabled: !!orgId,
  })
}

export function useWebhook(orgId: string, webhookId: string) {
  return useQuery({
    queryKey: queryKeys.webhooks.byId(orgId, webhookId),
    queryFn: async () => {
      const { data } = await api.get<Webhook>(`/orgs/${orgId}/webhooks/${webhookId}`)
      return data
    },
    enabled: !!orgId && !!webhookId,
  })
}

export function useWebhookEvents(orgId: string) {
  return useQuery({
    queryKey: queryKeys.webhooks.events(orgId),
    queryFn: async () => {
      const { data } = await api.get<string[]>(`/orgs/${orgId}/webhooks/events`)
      return data
    },
    enabled: !!orgId,
    staleTime: 60 * 60 * 1000, // 1 hour - events don't change often
  })
}

export function useCreateWebhook(orgId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (data: CreateWebhookData) => {
      const response = await api.post<Webhook>(`/orgs/${orgId}/webhooks`, data)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.webhooks.byOrg(orgId) })
    },
  })
}

export function useUpdateWebhook(orgId: string, webhookId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (data: UpdateWebhookData) => {
      const response = await api.patch<Webhook>(`/orgs/${orgId}/webhooks/${webhookId}`, data)
      return response.data
    },
    onSuccess: (webhook) => {
      queryClient.setQueryData(queryKeys.webhooks.byId(orgId, webhookId), webhook)
      queryClient.invalidateQueries({ queryKey: queryKeys.webhooks.byOrg(orgId) })
    },
  })
}

export function useDeleteWebhook(orgId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (webhookId: string) => {
      await api.delete(`/orgs/${orgId}/webhooks/${webhookId}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.webhooks.byOrg(orgId) })
    },
  })
}

export function useTestWebhook(orgId: string) {
  return useMutation({
    mutationFn: async (webhookId: string) => {
      const response = await api.post<WebhookTestResult>(`/orgs/${orgId}/webhooks/${webhookId}/test`)
      return response.data
    },
  })
}

export function useWebhookLogs(orgId: string, webhookId: string, params?: { limit?: number; offset?: number }) {
  return useQuery({
    queryKey: queryKeys.webhooks.logs(orgId, webhookId),
    queryFn: async () => {
      const { data } = await api.get<WebhookLog[]>(`/orgs/${orgId}/webhooks/${webhookId}/logs`, { params })
      return data
    },
    enabled: !!orgId && !!webhookId,
  })
}

// ============ Audit Logs Hooks ============

export function useAuditLogs(orgId: string, filters?: AuditLogFilter & { limit?: number; offset?: number }) {
  return useQuery({
    queryKey: queryKeys.auditLogs.byOrg(orgId, filters),
    queryFn: async () => {
      const { data } = await api.get<AuditLog[]>(`/orgs/${orgId}/audit-logs`, { params: filters })
      return data
    },
    enabled: !!orgId,
  })
}

export function useAuditLog(orgId: string, logId: string) {
  return useQuery({
    queryKey: queryKeys.auditLogs.byId(orgId, logId),
    queryFn: async () => {
      const { data } = await api.get<AuditLog>(`/orgs/${orgId}/audit-logs/${logId}`)
      return data
    },
    enabled: !!orgId && !!logId,
  })
}
