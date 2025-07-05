"use client"

import type React from "react"
import { cn } from "@/lib/utils"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { AlertCircle, TrendingUp, TrendingDown, Minus, MoreHorizontal } from "lucide-react"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"

interface DashboardCardProps {
  title: string
  description?: string
  value?: string | number
  previousValue?: string | number
  trend?: "up" | "down" | "neutral"
  trendValue?: string | number
  icon?: React.ComponentType<{ className?: string }>
  status?: "success" | "warning" | "error" | "info"
  isLoading?: boolean
  error?: string
  actions?: Array<{
    label: string
    onClick: () => void
    icon?: React.ComponentType<{ className?: string }>
  }>
  children?: React.ReactNode
  className?: string
  onClick?: () => void
  "aria-label"?: string
}

const getTrendIcon = (trend: "up" | "down" | "neutral") => {
  switch (trend) {
    case "up":
      return TrendingUp
    case "down":
      return TrendingDown
    default:
      return Minus
  }
}

const getTrendColor = (trend: "up" | "down" | "neutral") => {
  switch (trend) {
    case "up":
      return "text-green-600"
    case "down":
      return "text-red-600"
    default:
      return "text-gray-600"
  }
}

const getStatusColor = (status: "success" | "warning" | "error" | "info") => {
  switch (status) {
    case "success":
      return "border-green-200 bg-green-50"
    case "warning":
      return "border-yellow-200 bg-yellow-50"
    case "error":
      return "border-red-200 bg-red-50"
    case "info":
      return "border-blue-200 bg-blue-50"
    default:
      return ""
  }
}

export const DashboardCard: React.FC<DashboardCardProps> = ({
  title,
  description,
  value,
  previousValue,
  trend,
  trendValue,
  icon: Icon,
  status,
  isLoading = false,
  error,
  actions,
  children,
  className,
  onClick,
  "aria-label": ariaLabel,
  ...props
}) => {
  const TrendIcon = trend ? getTrendIcon(trend) : null
  const trendColor = trend ? getTrendColor(trend) : ""
  const statusColor = status ? getStatusColor(status) : ""

  const cardContent = (
    <>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <div className="flex items-center space-x-2">
          {Icon && (
            <div className="p-2 rounded-lg bg-primary/10">
              <Icon className="h-4 w-4 text-primary" aria-hidden="true" />
            </div>
          )}
          <div>
            <CardTitle className="text-sm font-medium">{title}</CardTitle>
            {description && <CardDescription className="text-xs">{description}</CardDescription>}
          </div>
        </div>

        {actions && actions.length > 0 && (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="h-8 w-8" aria-label="Card actions">
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              {actions.map((action, index) => (
                <DropdownMenuItem key={index} onClick={action.onClick}>
                  {action.icon && <action.icon className="mr-2 h-4 w-4" />}
                  {action.label}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
        )}
      </CardHeader>

      <CardContent>
        {isLoading ? (
          <div className="space-y-2">
            <Skeleton className="h-8 w-24" />
            <Skeleton className="h-4 w-16" />
          </div>
        ) : error ? (
          <div className="flex items-center space-x-2 text-red-600">
            <AlertCircle className="h-4 w-4" />
            <span className="text-sm">{error}</span>
          </div>
        ) : (
          <>
            {value !== undefined && (
              <div className="text-2xl font-bold" aria-live="polite">
                {typeof value === "number" ? value.toLocaleString() : value}
              </div>
            )}

            {(trend || trendValue) && (
              <div className={cn("flex items-center text-xs", trendColor)}>
                {TrendIcon && <TrendIcon className="mr-1 h-3 w-3" aria-hidden="true" />}
                {trendValue && (
                  <span>
                    {typeof trendValue === "number" && trendValue > 0 ? "+" : ""}
                    {typeof trendValue === "number" ? trendValue.toLocaleString() : trendValue}
                  </span>
                )}
                {previousValue && (
                  <span className="text-muted-foreground ml-1">
                    from {typeof previousValue === "number" ? previousValue.toLocaleString() : previousValue}
                  </span>
                )}
              </div>
            )}

            {children}
          </>
        )}
      </CardContent>
    </>
  )

  if (onClick) {
    return (
      <Card
        className={cn(
          "cursor-pointer transition-all hover:shadow-md focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
          statusColor,
          className,
        )}
        onClick={onClick}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault()
            onClick()
          }
        }}
        tabIndex={0}
        role="button"
        aria-label={ariaLabel || `${title} card`}
        {...props}
      >
        {cardContent}
      </Card>
    )
  }

  return (
    <Card className={cn(statusColor, className)} aria-label={ariaLabel} {...props}>
      {cardContent}
    </Card>
  )
}

export default DashboardCard
