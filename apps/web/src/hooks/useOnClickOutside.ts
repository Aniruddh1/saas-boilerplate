import { useEffect, type RefObject } from 'react'

type EventType = MouseEvent | TouchEvent

/**
 * Detect clicks outside of a referenced element.
 * Useful for closing modals, dropdowns, popovers.
 *
 * @example
 * const dropdownRef = useRef<HTMLDivElement>(null)
 * const [isOpen, setIsOpen] = useState(false)
 *
 * useOnClickOutside(dropdownRef, () => setIsOpen(false))
 *
 * return (
 *   <div ref={dropdownRef}>
 *     {isOpen && <DropdownMenu />}
 *   </div>
 * )
 */
export function useOnClickOutside<T extends HTMLElement = HTMLElement>(
  ref: RefObject<T>,
  handler: (event: EventType) => void,
  enabled: boolean = true
) {
  useEffect(() => {
    if (!enabled) return

    const listener = (event: EventType) => {
      const el = ref.current

      // Do nothing if clicking ref's element or descendent elements
      if (!el || el.contains(event.target as Node)) {
        return
      }

      handler(event)
    }

    document.addEventListener('mousedown', listener)
    document.addEventListener('touchstart', listener)

    return () => {
      document.removeEventListener('mousedown', listener)
      document.removeEventListener('touchstart', listener)
    }
  }, [ref, handler, enabled])
}
