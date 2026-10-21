import * as React from "react"

const MOBILE_BREAKPOINT = 768
const QUERY = `(max-width: ${MOBILE_BREAKPOINT - 1}px)`

function subscribe(onChange: () => void) {
  const mql = window.matchMedia(QUERY)
  mql.addEventListener("change", onChange)
  return () => mql.removeEventListener("change", onChange)
}

/** Phone-width screen. The server can't know the width, so the first render (and hydration) always says "not a
 * phone" - the same as the server - and React switches to the real answer straight after. Reading the width during
 * the first render made the sidebar's server and browser markup differ on phones (a hydration error). */
export function useIsMobile() {
  return React.useSyncExternalStore(
    subscribe,
    () => window.matchMedia(QUERY).matches,
    () => false
  )
}
