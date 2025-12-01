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
  // Query keys
  queryKeys,
} from './useApi'

// Toast
export { useToast } from './use-toast'
