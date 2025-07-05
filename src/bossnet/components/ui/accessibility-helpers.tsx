"use client"

import React from "react"
import { cn } from "@/lib/utils"

// Screen reader only text
export const ScreenReaderOnly: React.FC<{
  children: React.ReactNode
  className?: string
}> = ({ children, className }) => {
  return <span className={cn("sr-only", className)}>{children}</span>
}

// Skip to main content link
export const SkipToMain: React.FC<{
  href?: string
  className?: string
}> = ({ href = "#main-content", className }) => {
  return (
    <a
      href={href}
      className={cn(
        "absolute left-[-10000px] top-auto w-1 h-1 overflow-hidden",
        "focus:left-6 focus:top-6 focus:w-auto focus:h-auto focus:overflow-visible",
        "bg-primary text-primary-foreground px-4 py-2 rounded-md",
        "focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
        "z-50",
        className,
      )}
    >
      Skip to main content
    </a>
  )
}

// Focus trap for modals and dialogs
export const FocusTrap: React.FC<{
  children: React.ReactNode
  enabled?: boolean
  className?: string
}> = ({ children, enabled = true, className }) => {
  const containerRef = React.useRef<HTMLDivElement>(null)

  React.useEffect(() => {
    if (!enabled || !containerRef.current) return

    const container = containerRef.current
    const focusableElements = container.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
    )

    const firstElement = focusableElements[0] as HTMLElement
    const lastElement = focusableElements[focusableElements.length - 1] as HTMLElement

    const handleTabKey = (e: KeyboardEvent) => {
      if (e.key !== "Tab") return

      if (e.shiftKey) {
        if (document.activeElement === firstElement) {
          lastElement?.focus()
          e.preventDefault()
        }
      } else {
        if (document.activeElement === lastElement) {
          firstElement?.focus()
          e.preventDefault()
        }
      }
    }

    container.addEventListener("keydown", handleTabKey)
    firstElement?.focus()

    return () => {
      container.removeEventListener("keydown", handleTabKey)
    }
  }, [enabled])

  return (
    <div ref={containerRef} className={className}>
      {children}
    </div>
  )
}

// Announce changes to screen readers
export const LiveRegion: React.FC<{
  children: React.ReactNode
  politeness?: "polite" | "assertive" | "off"
  atomic?: boolean
  className?: string
}> = ({ children, politeness = "polite", atomic = false, className }) => {
  return (
    <div aria-live={politeness} aria-atomic={atomic} className={cn("sr-only", className)}>
      {children}
    </div>
  )
}

// High contrast mode detection
export const useHighContrast = () => {
  const [isHighContrast, setIsHighContrast] = React.useState(false)

  React.useEffect(() => {
    const mediaQuery = window.matchMedia("(prefers-contrast: high)")
    setIsHighContrast(mediaQuery.matches)

    const handleChange = (e: MediaQueryListEvent) => {
      setIsHighContrast(e.matches)
    }

    mediaQuery.addEventListener("change", handleChange)
    return () => mediaQuery.removeEventListener("change", handleChange)
  }, [])

  return isHighContrast
}

// Reduced motion detection
export const useReducedMotion = () => {
  const [prefersReducedMotion, setPrefersReducedMotion] = React.useState(false)

  React.useEffect(() => {
    const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)")
    setPrefersReducedMotion(mediaQuery.matches)

    const handleChange = (e: MediaQueryListEvent) => {
      setPrefersReducedMotion(e.matches)
    }

    mediaQuery.addEventListener("change", handleChange)
    return () => mediaQuery.removeEventListener("change", handleChange)
  }, [])

  return prefersReducedMotion
}

// Keyboard navigation helper
export const useKeyboardNavigation = (
  items: React.RefObject<HTMLElement>[],
  options: {
    loop?: boolean
    orientation?: "horizontal" | "vertical"
  } = {},
) => {
  const { loop = true, orientation = "vertical" } = options
  const [currentIndex, setCurrentIndex] = React.useState(0)

  const handleKeyDown = React.useCallback(
    (e: KeyboardEvent) => {
      const isVertical = orientation === "vertical"
      const nextKey = isVertical ? "ArrowDown" : "ArrowRight"
      const prevKey = isVertical ? "ArrowUp" : "ArrowLeft"

      if (e.key === nextKey) {
        e.preventDefault()
        setCurrentIndex((prev) => {
          const next = prev + 1
          if (next >= items.length) {
            return loop ? 0 : prev
          }
          return next
        })
      } else if (e.key === prevKey) {
        e.preventDefault()
        setCurrentIndex((prev) => {
          const next = prev - 1
          if (next < 0) {
            return loop ? items.length - 1 : prev
          }
          return next
        })
      } else if (e.key === "Home") {
        e.preventDefault()
        setCurrentIndex(0)
      } else if (e.key === "End") {
        e.preventDefault()
        setCurrentIndex(items.length - 1)
      }
    },
    [items.length, loop, orientation],
  )

  React.useEffect(() => {
    items[currentIndex]?.current?.focus()
  }, [currentIndex, items])

  return { currentIndex, handleKeyDown }
}

export default ScreenReaderOnly
