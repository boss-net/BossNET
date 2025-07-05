"use client"

/**
 * Removes all style tags injected by the Dark Reader browser extension.
 * Doing this before React hydrates prevents the notorious
 * “hydration failed because the server rendered HTML didn't match the client”
 * error caused by those extra nodes. Safe-no-op if Dark Reader isn’t present.
 */
import { useEffect } from "react"

export default function useRemoveDarkreader() {
  useEffect(() => {
    const darkReaderStyles =
      typeof document !== "undefined" ? Array.from(document.querySelectorAll<HTMLStyleElement>("style.darkreader")) : []

    if (darkReaderStyles.length) {
      darkReaderStyles.forEach((el) => el.parentElement?.removeChild(el))
    }
  }, [])
}
