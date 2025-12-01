/**
 * Shared TypeScript types for the application.
 */

// ============ User Types ============

export interface User {
  id: string
  email: string
  name: string
  avatar_url?: string
  is_active: boolean
  is_admin: boolean
  is_verified: boolean
  timezone: string
  created_at: string
  last_login_at?: string
}

export interface UpdateUserData {
  name?: string
  avatar_url?: string
  timezone?: string
}

export interface AdminUpdateUserData {
  name?: string
  is_active?: boolean
  is_admin?: boolean
  is_verified?: boolean
}

// ============ Feature Flag Types ============

export interface FeatureFlag {
  id: string
  key: string
  name: string
  description?: string
  enabled: boolean
  percentage: number
  conditions: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface CreateFeatureFlagData {
  key: string
  name: string
  description?: string
  enabled?: boolean
  percentage?: number
  conditions?: Record<string, unknown>
}

export interface UpdateFeatureFlagData {
  name?: string
  description?: string
  enabled?: boolean
  percentage?: number
  conditions?: Record<string, unknown>
}

export interface FeatureFlagOverride {
  user_id: string
  flag_key: string
  enabled: boolean
  reason?: string
  expires_at?: string
  created_at: string
}

// ============ Audit Log Types ============

export interface AuditLog {
  id: string
  actor_id?: string
  actor_email?: string
  actor_ip?: string
  resource_type: string
  resource_id: string
  action: string
  changes?: Record<string, { old: unknown; new: unknown }>
  extra_data?: Record<string, unknown>
  summary?: string
  request_id?: string
  created_at: string
}

export interface AuditLogFilter {
  actor_id?: string
  resource_type?: string
  resource_id?: string
  action?: string
  start_date?: string
  end_date?: string
}

// ============ Pagination Types ============

/**
 * Offset pagination response (traditional page-based).
 * Best for: Admin tables with page numbers, random page access.
 */
export interface OffsetPage<T> {
  items: T[]
  total: number
  page: number
  per_page: number
  pages: number
  has_next: boolean
  has_prev: boolean
}

/**
 * Cursor pagination response (keyset-based).
 * Best for: Infinite scroll, real-time feeds, large datasets.
 */
export interface CursorPage<T> {
  items: T[]
  next_cursor: string | null
  prev_cursor: string | null
  has_next: boolean
  has_prev: boolean
  limit: number
}

/**
 * Offset pagination parameters.
 */
export interface OffsetParams {
  page?: number
  per_page?: number
}

/**
 * Cursor pagination parameters.
 */
export interface CursorParams {
  cursor?: string
  limit?: number
}

// Legacy alias for backward compatibility
export type PaginatedResponse<T> = OffsetPage<T>

// ============ Job/Queue Types ============

/**
 * Job status values.
 */
export type JobStatusValue = 'pending' | 'started' | 'success' | 'failure' | 'retry' | 'revoked'

/**
 * Job priority levels.
 */
export type JobPriority = 'low' | 'normal' | 'high' | 'critical'

/**
 * Job status response.
 * Best for: Tracking async task status, polling for completion.
 */
export interface Job {
  id: string
  task: string
  status: JobStatusValue
  created_at?: string
  started_at?: string
  completed_at?: string
  result?: unknown
  error?: string
  retries: number
}

/**
 * Scheduled job (recurring task).
 * Best for: Cron jobs, periodic tasks, admin management.
 */
export interface ScheduledJob {
  id: string
  task: string
  schedule: string
  name?: string
  enabled: boolean
  last_run?: string
  next_run?: string
}

/**
 * Batch job result.
 */
export interface JobBatchResult {
  total: number
  enqueued: number
  task_ids: string[]
}

/**
 * Create scheduled job request.
 */
export interface CreateScheduledJobData {
  task: string
  schedule: string
  name?: string
  args?: unknown[]
  kwargs?: Record<string, unknown>
}

// ============ Notification Types ============

/**
 * Notification type/severity.
 */
export type NotificationType = 'info' | 'success' | 'warning' | 'error'

/**
 * Notification category for filtering and preferences.
 */
export type NotificationCategory = 'system' | 'account' | 'billing' | 'feature' | 'social' | 'marketing'

/**
 * In-app notification.
 * Best for: Notification list, notification bell, inbox.
 */
export interface Notification {
  id: string
  type: NotificationType
  category: NotificationCategory | string
  title: string
  message: string
  action_url?: string
  action_label?: string
  data?: Record<string, unknown>
  read_at?: string
  created_at: string
}

/**
 * Create notification request (admin).
 */
export interface CreateNotificationData {
  type?: NotificationType
  category?: string
  title: string
  message: string
  action_url?: string
  action_label?: string
  data?: Record<string, unknown>
}

/**
 * Broadcast notification request (admin).
 */
export interface BroadcastNotificationData {
  user_ids: string[]
  notification: CreateNotificationData
  channels?: string[]
}

/**
 * Notification preferences per category.
 */
export interface NotificationPreferences {
  categories: Record<string, {
    in_app: boolean
    email: boolean
    webhook?: boolean
  }>
}

// ============ Common Types ============

export interface ApiError {
  detail: string | { msg: string; type: string }[]
}
