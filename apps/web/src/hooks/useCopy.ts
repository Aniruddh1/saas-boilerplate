import { useState, useCallback, useEffect } from 'react'

interface UseCopyOptions {
  resetDelay?: number
  onSuccess?: () => void
  onError?: (error: Error) => void
}

/**
 * Copy text to clipboard with feedback state.
 *
 * @example
 * const { copy, isCopied } = useCopy()
 *
 * <button onClick={() => copy(apiKey)}>
 *   {isCopied ? 'Copied!' : 'Copy API Key'}
 * </button>
 */
export function useCopy(options: UseCopyOptions = {}) {
  const { resetDelay = 2000, onSuccess, onError } = options
  const [isCopied, setIsCopied] = useState(false)

  const copy = useCallback(
    async (text: string) => {
      if (!navigator.clipboard) {
        const error = new Error('Clipboard API not available')
        onError?.(error)
        console.warn('Clipboard API not available. Use HTTPS or localhost.')
        return false
      }

      try {
        await navigator.clipboard.writeText(text)
        setIsCopied(true)
        onSuccess?.()
        return true
      } catch (err) {
        const error = err instanceof Error ? err : new Error('Failed to copy')
        onError?.(error)
        console.error('Failed to copy:', error)
        return false
      }
    },
    [onSuccess, onError]
  )

  // Reset copied state after delay
  useEffect(() => {
    if (isCopied) {
      const timer = setTimeout(() => setIsCopied(false), resetDelay)
      return () => clearTimeout(timer)
    }
  }, [isCopied, resetDelay])

  const reset = useCallback(() => setIsCopied(false), [])

  return { copy, isCopied, reset }
}
