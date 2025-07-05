import {
  Home,
  BarChart3,
  Users,
  GraduationCap,
  MapPin,
  TrendingUp,
  Calendar,
  FileText,
  HelpCircle,
  type LucideIcon,
} from "lucide-react"

export interface NavigationItem {
  id: string
  label: string
  icon: LucideIcon
  href?: string
  badge?: string | number
  children?: NavigationItem[]
  isActive?: boolean
  className?: string
}

const navigationItems: NavigationItem[] = [
  {
    id: "dashboard",
    label: "Dashboard",
    icon: Home,
    href: "/dashboard"
  },
  {
    id: "analytics",
    label: "Analytics",
    icon: BarChart3,
    children: [
      {
        id: "overview",
        label: "Overview",
        icon: BarChart3,
        href: "/analytics/overview"
      },
      {
        id: "reports",
        label: "Reports",
        icon: FileText,
        href: "/analytics/reports"
      },
      {
        id: "export",
        label: "Export",
        icon: TrendingUp,
        href: "/analytics/export"
      }
    ]
  },
  {
    id: "students",
    label: "Students",
    icon: GraduationCap,
    href: "/students"
  },
  {
    id: "teachers",
    label: "Teachers",
    icon: Users,
    href: "/teachers"
  },
  {
    id: "locations",
    label: "Locations",
    icon: MapPin,
    href: "/locations"
  },
  {
    id: "performance",
    label: "Performance",
    icon: TrendingUp,
    href: "/performance"
  },
  {
    id: "schedule",
    label: "Schedule",
    icon: Calendar,
    href: "/schedule"
  },
  {
    id: "documents",
    label: "Documents",
    icon: FileText,
    href: "/documents"
  },
  {
    id: "support",
    label: "Support",
    icon: HelpCircle,
    href: "/support"
  }
]

export { navigationItems }
