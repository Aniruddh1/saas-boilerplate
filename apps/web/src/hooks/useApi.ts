/**
 * TanStack Query hooks for API data fetching.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { User, AuditLog, AuditLogFilter } from '@/types'

// ============ Query Keys ============

export const queryKeys = {
  user: {
    current: ['user', 'current'] as const,
    byId: (id: string) => ['user', id] as const,
    list: (filters?: Record<string, unknown>) => ['users', 'list', filters] as const,
  },
  auditLogs: {
    all: ['auditLogs'] as const,
    list: (filters?: AuditLogFilter & { limit?: number; offset?: number }) =>
      ['auditLogs', 'list', filters] as const,
    byId: (id: string) => ['auditLogs', id] as const,
  },
  features: {
    all: ['features'] as const,
    myFlags: ['features', 'me'] as const,
    byKey: (key: string) => ['features', key] as const,
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

// ============ Admin User Hooks ============

export function useUsers(filters?: { page?: number; per_page?: number; search?: string }) {
  return useQuery({
    queryKey: queryKeys.user.list(filters),
    queryFn: async () => {
      const { data } = await api.get('/admin/users', { params: filters })
      return data as { items: User[]; total: number; page: number; per_page: number }
    },
  })
}

export function useUpdateUser() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ userId, data }: { userId: string; data: { is_admin?: boolean; is_active?: boolean } }) => {
      const response = await api.patch(`/admin/users/${userId}`, data)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
    },
  })
}

// ============ Audit Logs Hooks ============

export function useAuditLogs(filters?: AuditLogFilter & { limit?: number; offset?: number }) {
  return useQuery({
    queryKey: queryKeys.auditLogs.list(filters),
    queryFn: async () => {
      const { data } = await api.get<AuditLog[]>('/audit-logs', { params: filters })
      return data
    },
  })
}

export function useAuditLog(logId: string) {
  return useQuery({
    queryKey: queryKeys.auditLogs.byId(logId),
    queryFn: async () => {
      const { data } = await api.get<AuditLog>(`/audit-logs/${logId}`)
      return data
    },
    enabled: !!logId,
  })
}

// ============ Feature Flag Hooks ============

export function useMyFeatureFlags() {
  return useQuery({
    queryKey: queryKeys.features.myFlags,
    queryFn: async () => {
      const { data } = await api.get<Record<string, boolean>>('/features/me')
      return data
    },
    staleTime: 60 * 1000, // 1 minute
  })
}

export function useCheckFeatureFlag(key: string) {
  return useQuery({
    queryKey: queryKeys.features.byKey(key),
    queryFn: async () => {
      const { data } = await api.get<{ key: string; enabled: boolean; reason: string }>(`/features/check/${key}`)
      return data
    },
    enabled: !!key,
  })
}
