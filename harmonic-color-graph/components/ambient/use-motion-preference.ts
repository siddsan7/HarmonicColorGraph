"use client"
import { useSyncExternalStore } from "react"

const query = "(prefers-reduced-motion: reduce)"
const subscribe = (notify: () => void) => {
  const media = window.matchMedia(query)
  media.addEventListener("change", notify)
  return () => media.removeEventListener("change", notify)
}

/** True when the visitor asked the system for less motion. Server renders as false. */
export function useReducedMotion() {
  return useSyncExternalStore(subscribe, () => window.matchMedia(query).matches, () => false)
}
