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
  Job,
  ScheduledJob,
  CreateScheduledJobData,
  Notification,
  BroadcastNotificationData,
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
  jobs: {
    all: ['jobs'] as const,
    list: (filters?: OffsetParams) => ['jobs', 'list', filters] as const,
    byId: (id: string) => ['jobs', id] as const,
    scheduled: ['jobs', 'scheduled'] as const,
  },
  notifications: {
    all: ['notifications'] as const,
    list: (filters?: OffsetParams & { read?: boolean }) => ['notifications', 'list', filters] as const,
    unreadCount: ['notifications', 'unread-count'] as const,
    byId: (id: string) => ['notifications', id] as const,
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

// ============ Job Hooks ============

/**
 * List jobs with offset pagination.
 * Best for: Admin job management tables.
 */
export function useJobs(filters?: OffsetParams) {
  return useQuery({
    queryKey: queryKeys.jobs.list(filters),
    queryFn: async () => {
      const { data } = await api.get<OffsetPage<Job>>('/jobs', { params: filters })
      return data
    },
  })
}

/**
 * Get single job status.
 * Best for: Polling job completion, status display.
 *
 * Use refetchInterval for polling:
 *   useJob(jobId, { refetchInterval: 2000 })
 */
export function useJob(jobId: string, options?: { refetchInterval?: number }) {
  return useQuery({
    queryKey: queryKeys.jobs.byId(jobId),
    queryFn: async () => {
      const { data } = await api.get<Job>(`/jobs/${jobId}`)
      return data
    },
    enabled: !!jobId,
    refetchInterval: options?.refetchInterval,
  })
}

/**
 * Cancel a pending or running job.
 */
export function useCancelJob() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ jobId, terminate = false }: { jobId: string; terminate?: boolean }) => {
      const response = await api.post(`/jobs/${jobId}/cancel`, { terminate })
      return response.data
    },
    onSuccess: (_, { jobId }) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.jobs.byId(jobId) })
      queryClient.invalidateQueries({ queryKey: queryKeys.jobs.all })
    },
  })
}

/**
 * List scheduled (recurring) jobs.
 * Best for: Admin scheduled job management.
 */
export function useScheduledJobs() {
  return useQuery({
    queryKey: queryKeys.jobs.scheduled,
    queryFn: async () => {
      const { data } = await api.get<ScheduledJob[]>('/jobs/scheduled')
      return data
    },
  })
}

/**
 * Create a new scheduled job.
 */
export function useCreateScheduledJob() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (jobData: CreateScheduledJobData) => {
      const response = await api.post<ScheduledJob>('/jobs/scheduled', jobData)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.jobs.scheduled })
    },
  })
}

/**
 * Delete a scheduled job.
 */
export function useDeleteScheduledJob() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (scheduleId: string) => {
      await api.delete(`/jobs/scheduled/${scheduleId}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.jobs.scheduled })
    },
  })
}

// ============ Notification Hooks ============

/**
 * List notifications with offset pagination.
 * Best for: Notification inbox, history view.
 */
export function useNotifications(filters?: OffsetParams & { read?: boolean }) {
  return useQuery({
    queryKey: queryKeys.notifications.list(filters),
    queryFn: async () => {
      const { data } = await api.get<OffsetPage<Notification>>('/notifications', { params: filters })
      return data
    },
  })
}

/**
 * Get unread notification count.
 * Best for: Badge display on notification bell.
 *
 * Use refetchInterval for real-time updates:
 *   useUnreadCount({ refetchInterval: 30000 })
 */
export function useUnreadCount(options?: { refetchInterval?: number }) {
  return useQuery({
    queryKey: queryKeys.notifications.unreadCount,
    queryFn: async () => {
      const { data } = await api.get<{ count: number }>('/notifications/unread-count')
      return data.count
    },
    refetchInterval: options?.refetchInterval,
  })
}

/**
 * Get a single notification.
 */
export function useNotification(notificationId: string) {
  return useQuery({
    queryKey: queryKeys.notifications.byId(notificationId),
    queryFn: async () => {
      const { data } = await api.get<Notification>(`/notifications/${notificationId}`)
      return data
    },
    enabled: !!notificationId,
  })
}

/**
 * Mark a notification as read.
 */
export function useMarkAsRead() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (notificationId: string) => {
      const response = await api.post(`/notifications/${notificationId}/read`)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.notifications.all })
    },
  })
}

/**
 * Mark all notifications as read.
 */
export function useMarkAllAsRead() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async () => {
      const response = await api.post('/notifications/read-all')
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.notifications.all })
    },
  })
}

/**
 * Delete a notification.
 */
export function useDeleteNotification() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (notificationId: string) => {
      await api.delete(`/notifications/${notificationId}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.notifications.all })
    },
  })
}

/**
 * Delete all read notifications.
 */
export function useDeleteReadNotifications() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async () => {
      const response = await api.delete('/notifications')
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.notifications.all })
    },
  })
}

/**
 * Broadcast notification to users (admin only).
 */
export function useBroadcastNotification() {
  return useMutation({
    mutationFn: async (data: BroadcastNotificationData) => {
      const response = await api.post('/notifications/broadcast', data)
      return response.data
    },
  })
}
