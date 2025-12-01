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

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  per_page: number
  pages: number
}

// ============ Common Types ============

export interface ApiError {
  detail: string | { msg: string; type: string }[]
}
