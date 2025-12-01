/**
 * TanStack Query hooks for API data fetching.
 *
 * Demonstrates enterprise pagination patterns:
 * - Offset pagination (useAuditLogs) - for admin tables
 * - Cursor pagination (useAuditLogsStream) - for infinite scroll
 * - Count queries (useAuditLogsCount) - for badges
 */

import { useQuery, useMutation, useQueryClient, useInfiniteQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type {
  User,
  AuditLog,
  AuditLogFilter,
  OffsetPage,
  CursorPage,
  OffsetParams,
} from '@/types'

// ============ Query Keys ============

export const queryKeys = {
  user: {
    current: ['user', 'current'] as const,
    byId: (id: string) => ['user', id] as const,
    list: (filters?: Record<string, unknown>) => ['users', 'list', filters] as const,
  },
  auditLogs: {
    all: ['auditLogs'] as const,
    list: (filters?: AuditLogFilter & OffsetParams) => ['auditLogs', 'list', filters] as const,
    stream: (filters?: AuditLogFilter) => ['auditLogs', 'stream', filters] as const,
    count: (filters?: AuditLogFilter) => ['auditLogs', 'count', filters] as const,
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
      const { data } = await api.get<OffsetPage<User>>('/users', { params: filters })
      return data
    },
  })
}

export function useUpdateUser() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ userId, data }: { userId: string; data: { is_admin?: boolean; is_active?: boolean } }) => {
      const response = await api.patch(`/users/${userId}`, data)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
    },
  })
}

// ============ Audit Logs Hooks ============

/**
 * Offset pagination for audit logs.
 * Best for: Admin tables with page numbers.
 */
export function useAuditLogs(filters?: AuditLogFilter & OffsetParams) {
  return useQuery({
    queryKey: queryKeys.auditLogs.list(filters),
    queryFn: async () => {
      const { data } = await api.get<OffsetPage<AuditLog>>('/audit-logs', { params: filters })
      return data
    },
  })
}

/**
 * Cursor pagination for audit logs (infinite scroll).
 * Best for: Real-time feeds, infinite scroll UIs.
 */
export function useAuditLogsStream(filters?: AuditLogFilter & { limit?: number }) {
  return useInfiniteQuery({
    queryKey: queryKeys.auditLogs.stream(filters),
    queryFn: async ({ pageParam }) => {
      const params = {
        ...filters,
        cursor: pageParam,
        limit: filters?.limit || 20,
      }
      const { data } = await api.get<CursorPage<AuditLog>>('/audit-logs/stream', { params })
      return data
    },
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage) => lastPage.next_cursor ?? undefined,
    getPreviousPageParam: (firstPage) => firstPage.prev_cursor ?? undefined,
  })
}

/**
 * Count audit logs matching filters.
 * Best for: Dashboard stats, badges.
 */
export function useAuditLogsCount(filters?: AuditLogFilter) {
  return useQuery({
    queryKey: queryKeys.auditLogs.count(filters),
    queryFn: async () => {
      const { data } = await api.get<{ count: number }>('/audit-logs/count', { params: filters })
      return data.count
    },
  })
}

/**
 * Get single audit log by ID.
 */
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

/**
 * Export audit logs as file.
 * Returns download URL.
 */
export function useExportAuditLogs() {
  return useMutation({
    mutationFn: async (params: AuditLogFilter & { format?: 'csv' | 'jsonl' }) => {
      const response = await api.get('/audit-logs/export', {
        params,
        responseType: 'blob',
      })
      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      const format = params.format || 'csv'
      link.setAttribute('download', `audit_logs.${format}`)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
    },
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
