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
  is_verified: boolean
  timezone: string
  created_at: string
  last_login_at?: string
}

// ============ Organization Types ============

export interface Organization {
  id: string
  name: string
  slug: string
  description?: string
  plan: string
  max_members: number
  max_projects: number
  created_at: string
  updated_at: string
}

export interface OrgMember {
  id: string
  org_id: string
  user_id: string
  role: 'owner' | 'admin' | 'member' | 'viewer'
  user: User
  created_at: string
}

export interface CreateOrgData {
  name: string
  slug: string
  description?: string
}

export interface UpdateOrgData {
  name?: string
  description?: string
}

// ============ Project Types ============

export interface Project {
  id: string
  name: string
  slug: string
  description?: string
  org_id: string
  settings: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface CreateProjectData {
  name: string
  slug?: string
  description?: string
  org_id: string
}

export interface UpdateProjectData {
  name?: string
  description?: string
  settings?: Record<string, unknown>
}

export interface ProjectsResponse {
  projects: Project[]
  total: number
  page: number
  per_page: number
}

// ============ API Key Types ============

export interface APIKey {
  id: string
  name: string
  key_prefix: string
  org_id: string
  scopes: string[]
  expires_at?: string
  last_used_at?: string
  is_active: boolean
  created_at: string
}

export interface APIKeyWithSecret extends APIKey {
  key: string // Only returned on creation
}

export interface CreateAPIKeyData {
  name: string
  org_id: string
  scopes?: string[]
  expires_in_days?: number
}

// ============ Webhook Types ============

export interface Webhook {
  id: string
  org_id: string
  name: string
  url: string
  events: string[]
  is_active: boolean
  description?: string
  headers?: Record<string, string>
  max_failures: number
  failure_count: number
  last_triggered_at?: string
  created_at: string
  updated_at: string
}

export interface WebhookLog {
  id: string
  webhook_id: string
  event_type: string
  payload: Record<string, unknown>
  response_status?: number
  response_body?: string
  response_time_ms?: number
  success: boolean
  error_message?: string
  attempt: number
  created_at: string
}

export interface CreateWebhookData {
  name: string
  url: string
  events: string[]
  secret?: string
  description?: string
  headers?: Record<string, string>
}

export interface UpdateWebhookData {
  name?: string
  url?: string
  events?: string[]
  secret?: string
  description?: string
  headers?: Record<string, string>
  is_active?: boolean
}

export interface WebhookTestResult {
  success: boolean
  status_code?: number
  response_time_ms: number
  error?: string
}

// ============ Audit Log Types ============

export interface AuditLog {
  id: string
  actor_id?: string
  actor_email?: string
  actor_ip?: string
  org_id?: string
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

export interface OrgsResponse {
  orgs: Organization[]
  total: number
  page: number
  per_page: number
}

// ============ Common Types ============

export interface ApiError {
  detail: string | { msg: string; type: string }[]
}
