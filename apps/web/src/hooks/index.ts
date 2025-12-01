// Core utility hooks
export { useDebounce } from './useDebounce'
export { useLocalStorage } from './useLocalStorage'
export { useCopy } from './useCopy'
export { useOnClickOutside } from './useOnClickOutside'
export { useMediaQuery, useIsMobile, useIsTablet, useIsDesktop } from './useMediaQuery'
export { useTheme } from './useTheme'

// API hooks (TanStack Query)
export {
  // Users
  useCurrentUser,
  useUpdateProfile,
  useUsers,
  useUpdateUser,
  // Audit logs (with pagination patterns)
  useAuditLogs,        // Offset pagination
  useAuditLogsStream,  // Cursor/infinite scroll
  useAuditLogsCount,   // Count only
  useAuditLog,
  useExportAuditLogs,  // Export/download
  // Feature flags
  useMyFeatureFlags,
  useCheckFeatureFlag,
  // Jobs (with queue patterns)
  useJobs,              // List jobs with pagination
  useJob,               // Single job status (with polling)
  useCancelJob,         // Cancel mutation
  useScheduledJobs,     // List scheduled jobs
  useCreateScheduledJob,// Create scheduled
  useDeleteScheduledJob,// Delete scheduled
  // Notifications (with notification patterns)
  useNotifications,       // List with pagination
  useUnreadCount,         // Count for badges (with polling)
  useNotification,        // Single notification
  useMarkAsRead,          // Mark single as read
  useMarkAllAsRead,       // Mark all as read
  useDeleteNotification,  // Delete single
  useDeleteReadNotifications, // Delete all read
  useBroadcastNotification,   // Admin broadcast
  // Query keys
  queryKeys,
} from './useApi'

// Toast
export { useToast } from './use-toast'
