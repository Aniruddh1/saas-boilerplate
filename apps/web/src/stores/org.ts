/**
 * Organization state management with Zustand.
 *
 * Manages the currently selected organization context.
 */

import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { Organization } from '@/types'

interface OrgState {
  currentOrg: Organization | null
  setCurrentOrg: (org: Organization | null) => void
  clearCurrentOrg: () => void
}

export const useOrgStore = create<OrgState>()(
  persist(
    (set) => ({
      currentOrg: null,

      setCurrentOrg: (org) => set({ currentOrg: org }),

      clearCurrentOrg: () => set({ currentOrg: null }),
    }),
    {
      name: 'org-storage',
      partialize: (state) => ({ currentOrg: state.currentOrg }),
    }
  )
)
