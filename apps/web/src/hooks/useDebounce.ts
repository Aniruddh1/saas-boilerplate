import { useState, useEffect } from 'react'

/**
 * Debounce a value by delaying updates until after a specified delay.
 * Useful for search inputs, form validation, API calls.
 *
 * @example
 * const [search, setSearch] = useState('')
 * const debouncedSearch = useDebounce(search, 300)
 *
 * useEffect(() => {
 *   // This only runs 300ms after user stops typing
 *   fetchResults(debouncedSearch)
 * }, [debouncedSearch])
 */
export function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value)

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedValue(value)
    }, delay)

    return () => {
      clearTimeout(timer)
    }
  }, [value, delay])

  return debouncedValue
}
