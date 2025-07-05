"use client"

import type React from "react"
import { cn } from "@/lib/utils"
import { DashboardCard } from "./DashboardCard"
import { ResponsiveGrid } from "@/components/ui/responsive-container"
import { ErrorBoundary, SimpleErrorFallback } from "@/components/ui/error-boundary"
import {
  Users,
  GraduationCap,
  School,
  TrendingUp,
  TrendingDown,
  UserCheck,
  MapPin,
  Calendar,
  BarChart3,
  PieChart,
  Activity,
} from "lucide-react"

interface MetricData {
  id: string
  title: string
  value: string | number
  previousValue?: string | number
  trend?: "up" | "down" | "neutral"
  trendValue?: string | number
  icon: React.ComponentType<{ className?: string }>
  status?: "success" | "warning" | "error" | "info"
  description?: string
  isLoading?: boolean
  error?: string
}

interface DashboardMetricsProps {
  metrics?: MetricData[]
  isLoading?: boolean
  error?: Error | null
  onMetricClick?: (metricId: string) => void
  className?: string
  columns?: {
    default?: number
    sm?: number
    md?: number
    lg?: number
    xl?: number
  }
}

const defaultMetrics: MetricData[] = [
  {
    id: "total-students",
    title: "Total Students",
    value: "1,234,567",
    previousValue: "1,198,432",
    trend: "up",
    trendValue: "+3.0%",
    icon: Users,
    status: "success",
    description: "Total enrolled students across all institutions",
  },
  {
    id: "total-schools",
    title: "Active Schools",
    value: "18,542",
    previousValue: "18,234",
    trend: "up",
    trendValue: "+1.7%",
    icon: School,
    status: "info",
    description: "Number of active educational institutions",
  },
  {
    id: "enrollment-rate",
    title: "Enrollment Rate",
    value: "94.2%",
    previousValue: "92.8%",
    trend: "up",
    trendValue: "+1.4%",
    icon: TrendingUp,
    status: "success",
    description: "Percentage of school-age children enrolled",
  },
  {
    id: "dropout-rate",
    title: "Dropout Rate",
    value: "8.3%",
    previousValue: "9.1%",
    trend: "down",
    trendValue: "-0.8%",
    icon: TrendingDown,
    status: "warning",
    description: "Percentage of students who dropped out",
  },
  {
    id: "attendance-rate",
    title: "Attendance Rate",
    value: "87.5%",
    previousValue: "85.2%",
    trend: "up",
    trendValue: "+2.3%",
    icon: UserCheck,
    status: "success",
    description: "Average daily attendance rate",
  },
  {
    id: "teacher-student-ratio",
    title: "Teacher-Student Ratio",
    value: "1:32",
    previousValue: "1:35",
    trend: "up",
    trendValue: "Improved",
    icon: GraduationCap,
    status: "info",
    description: "Average number of students per teacher",
  },
  {
    id: "completion-rate",
    title: "Completion Rate",
    value: "78.9%",
    previousValue: "76.4%",
    trend: "up",
    trendValue: "+2.5%",
    icon: Activity,
    status: "success",
    description: "Percentage of students completing their education cycle",
  },
  {
    id: "gender-parity",
    title: "Gender Parity Index",
    value: "0.98",
    previousValue: "0.95",
    trend: "up",
    trendValue: "+0.03",
    icon: PieChart,
    status: "success",
    description: "Ratio of female to male enrollment",
  },
]

export const DashboardMetrics: React.FC<DashboardMetricsProps> = ({
  metrics = defaultMetrics,
  isLoading = false,
  error = null,
  onMetricClick,
  className,
  columns = { default: 1, sm: 2, md: 2, lg: 4 },
}) => {
  const handleMetricClick = (metricId: string) => {
    onMetricClick?.(metricId)
  }

  const handleRetry = () => {
    window.location.reload()
  }

  if (error) {
    return (
      <div className={cn("w-full", className)}>
        <SimpleErrorFallback message="Failed to load dashboard metrics" onRetry={handleRetry} />
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className={cn("w-full", className)}>
        <ResponsiveGrid columns={columns} gap="md">
          {Array.from({ length: 8 }).map((_, index) => (
            <DashboardCard key={index} title="" isLoading={true} />
          ))}
        </ResponsiveGrid>
      </div>
    )
  }

  return (
    <ErrorBoundary>
      <div className={cn("w-full", className)}>
        <div className="mb-6">
          <h2 className="text-2xl font-bold tracking-tight">Dashboard Overview</h2>
          <p className="text-muted-foreground">Key performance indicators for Bangladesh education system</p>
        </div>

        <ResponsiveGrid columns={columns} gap="md">
          {metrics.map((metric) => (
            <DashboardCard
              key={metric.id}
              title={metric.title}
              description={metric.description}
              value={metric.value}
              previousValue={metric.previousValue}
              trend={metric.trend}
              trendValue={metric.trendValue}
              icon={metric.icon}
              status={metric.status}
              isLoading={metric.isLoading}
              error={metric.error}
              onClick={onMetricClick ? () => handleMetricClick(metric.id) : undefined}
              aria-label={`${metric.title}: ${metric.value}${metric.trendValue ? `, ${metric.trendValue} change` : ""}`}
              actions={[
                {
                  label: "View Details",
                  onClick: () => handleMetricClick(metric.id),
                  icon: BarChart3,
                },
                {
                  label: "Export Data",
                  onClick: () => console.log(`Exporting ${metric.id} data`),
                  icon: TrendingUp,
                },
              ]}
            />
          ))}
        </ResponsiveGrid>

        {/* Additional insights section */}
        <div className="mt-8 grid grid-cols-1 lg:grid-cols-2 gap-6">
          <DashboardCard
            title="Regional Performance"
            description="Top performing divisions this month"
            icon={MapPin}
            status="info"
          >
            <div className="mt-4 space-y-2">
              <div className="flex justify-between items-center">
                <span className="text-sm">Dhaka Division</span>
                <span className="text-sm font-medium text-green-600">+5.2%</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm">Chittagong Division</span>
                <span className="text-sm font-medium text-green-600">+4.8%</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm">Rajshahi Division</span>
                <span className="text-sm font-medium text-green-600">+3.9%</span>
              </div>
            </div>
          </DashboardCard>

          <DashboardCard
            title="Recent Activities"
            description="Latest system updates and changes"
            icon={Calendar}
            status="info"
          >
            <div className="mt-4 space-y-2">
              <div className="text-sm">
                <span className="font-medium">New school registrations:</span> 23 this week
              </div>
              <div className="text-sm">
                <span className="font-medium">Student transfers:</span> 1,247 processed
              </div>
              <div className="text-sm">
                <span className="font-medium">Data quality checks:</span> 98.7% passed
              </div>
            </div>
          </DashboardCard>
        </div>
      </div>
    </ErrorBoundary>
  )
}

export default DashboardMetrics
