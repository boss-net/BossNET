"use client"

import type React from "react"
import { cn } from "@/lib/utils"

interface ResponsiveContainerProps {
  children: React.ReactNode
  className?: string
  maxWidth?: "sm" | "md" | "lg" | "xl" | "2xl" | "3xl" | "4xl" | "5xl" | "6xl" | "7xl" | "full"
  padding?: "none" | "sm" | "md" | "lg" | "xl"
  center?: boolean
}

const maxWidthClasses = {
  sm: "max-w-sm",
  md: "max-w-md",
  lg: "max-w-lg",
  xl: "max-w-xl",
  "2xl": "max-w-2xl",
  "3xl": "max-w-3xl",
  "4xl": "max-w-4xl",
  "5xl": "max-w-5xl",
  "6xl": "max-w-6xl",
  "7xl": "max-w-7xl",
  full: "max-w-full",
}

const paddingClasses = {
  none: "",
  sm: "p-2 sm:p-4",
  md: "p-4 sm:p-6",
  lg: "p-6 sm:p-8",
  xl: "p-8 sm:p-12",
}

export const ResponsiveContainer: React.FC<ResponsiveContainerProps> = ({
  children,
  className,
  maxWidth = "full",
  padding = "md",
  center = true,
}) => {
  return (
    <div className={cn("w-full", maxWidthClasses[maxWidth], paddingClasses[padding], center && "mx-auto", className)}>
      {children}
    </div>
  )
}

export const ResponsiveGrid: React.FC<{
  children: React.ReactNode
  columns?: {
    default?: number
    sm?: number
    md?: number
    lg?: number
    xl?: number
  }
  gap?: "sm" | "md" | "lg" | "xl"
  className?: string
}> = ({ children, columns = { default: 1, sm: 2, md: 3, lg: 4 }, gap = "md", className }) => {
  const gapClasses = {
    sm: "gap-2",
    md: "gap-4",
    lg: "gap-6",
    xl: "gap-8",
  }

  const getGridCols = () => {
    const classes = []
    if (columns.default) classes.push(`grid-cols-${columns.default}`)
    if (columns.sm) classes.push(`sm:grid-cols-${columns.sm}`)
    if (columns.md) classes.push(`md:grid-cols-${columns.md}`)
    if (columns.lg) classes.push(`lg:grid-cols-${columns.lg}`)
    if (columns.xl) classes.push(`xl:grid-cols-${columns.xl}`)
    return classes.join(" ")
  }

  return <div className={cn("grid", getGridCols(), gapClasses[gap], className)}>{children}</div>
}

export default ResponsiveContainer
