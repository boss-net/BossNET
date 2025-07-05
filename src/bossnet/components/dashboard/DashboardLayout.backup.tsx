"use client"

import type React from "react"
import { useState, useEffect } from "react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Sheet, SheetContent } from "@/components/ui/sheet"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import { Badge } from "@/components/ui/badge"
import {
  Menu,
  Bell,
  Search,
  Settings,
  User,
  Home,
  BarChart3,
  Users,
  GraduationCap,
  MapPin,
  TrendingUp,
  Calendar,
  FileText,
  HelpCircle,
  LogOut,
  ChevronRight,
} from "lucide-react"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Input } from "@/components/ui/input"
import { LoadingSpinner } from "@/components/ui/loading-spinner"
import { ErrorBoundary } from "@/lib/error-boundary"
// Remove toast import for now as it's causing issues

interface NavigationItem {
  id: string
  label: string
  icon: React.ComponentType<{ className?: string }>
  href?: string
  badge?: string | number
  children?: NavigationItem[]
  isActive?: boolean
  className?: string
}

interface DashboardLayoutProps {
  children: React.ReactNode
  title?: string
  subtitle?: string
  isLoading?: boolean
  error?: Error | null
  user?: {
    name: string
    email: string
    avatar?: string
    role: string
  }
  notifications?: number
  onSearch?: (query: string) => void
  onNavigate?: (itemId: string) => void
  className?: string
}

const navigationItems: NavigationItem[] = [
  {
    id: "dashboard",
    label: "Dashboard",
    icon: Home,
    href: "/dashboard",
    isActive: true,
  },
  {
    id: "analytics",
    label: "Analytics",
    icon: BarChart3,
    children: [
      {
        id: "enrollment-trends",
        label: "Enrollment Trends",
        icon: TrendingUp,
        href: "/dashboard/enrollment-trends",
      },
      {
        id: "performance-metrics",
        label: "Performance Metrics",
        icon: BarChart3,
        href: "/dashboard/performance",
      },
      {
        id: "demographic-analysis",
        label: "Demographics",
        icon: Users,
        href: "/dashboard/demographics",
      },
    ],
  },
  {
    id: "students",
    label: "Students",
    icon: GraduationCap,
    href: "/dashboard/students",
    badge: "1.2M",
  },
  {
    id: "schools",
    label: "Schools",
    icon: MapPin,
    href: "/dashboard/schools",
    badge: "18.5K",
  },
  {
    id: "reports",
    label: "Reports",
    icon: FileText,
    children: [
      {
        id: "enrollment-reports",
        label: "Enrollment Reports",
        icon: FileText,
        href: "/dashboard/reports/enrollment",
      },
      {
        id: "performance-reports",
        label: "Performance Reports",
        icon: FileText,
        href: "/dashboard/reports/performance",
      },
      {
        id: "custom-reports",
        label: "Custom Reports",
        icon: FileText,
        href: "/dashboard/reports/custom",
      },
    ],
  },
  {
    id: "calendar",
    label: "Academic Calendar",
    icon: Calendar,
    href: "/dashboard/calendar",
  },
  {
    id: "settings",
    label: "Settings",
    icon: Settings,
    href: "/dashboard/settings",
  },
  {
    id: "help",
    label: "Help & Support",
    icon: HelpCircle,
    href: "/dashboard/help",
  },
]

interface NavigationItemProps {
  item: NavigationItem;
  level?: number;
  onNavigate?: (itemId: string) => void;
  children?: React.ReactNode;
}

const NavigationItem: React.FC<NavigationItemProps> = (props) => {
  const { item, level = 0, onNavigate, children } = props;
  const [isExpanded, setIsExpanded] = useState(false);
  const hasChildren = item.children && item.children.length > 0;

  const handleClick = () => {
    if (hasChildren) {
      setIsExpanded(!isExpanded);
    } else if (onNavigate) {
      onNavigate(item.id);
    }
  };

  const handleSearch = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (onNavigate) {
      onNavigate(`search:${e.target.value}`);
    }
  };

  const handleKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      handleClick();
    }
  };

  return (
    <div className="space-y-1">
      <button
        type="button"
        onClick={handleClick}
        onKeyDown={handleKeyDown}
        className={cn(
          'flex w-full items-center rounded-md px-3 py-2 text-sm font-medium',
          item.isActive
            ? 'bg-accent text-accent-foreground'
            : 'text-foreground hover:bg-accent/50',
          level > 0 && 'pl-8',
          item.className
        )}
      >
        <item.icon className="mr-3 h-4 w-4 flex-shrink-0" />
        <span className="flex-1 text-left">{item.label}</span>
        {hasChildren && (
          <ChevronRight
            className={cn(
              'h-4 w-4 transition-transform',
              isExpanded && 'rotate-90'
            )}
          />
        )}
        {item.badge && (
          <Badge variant="secondary" className="ml-2">
            {item.badge}
          </Badge>
        )}
      </button>
      {hasChildren && isExpanded && (
        <div className="mt-1 space-y-1 pl-4">
          {item.children?.map((child) => (
            <NavigationItem
              key={child.id}
              item={child}
              level={level + 1}
              onNavigate={onNavigate}
            />
          ))}
        </div>
      )}
    </div>
  );
}

  return (
    <div className="w-full">
      <button
        onClick={handleClick}
        onKeyDown={handleKeyDown}
        className={cn(
          "w-full flex items-center justify-between px-3 py-2 text-sm font-medium rounded-lg transition-colors",
          "hover:bg-accent hover:text-accent-foreground",
          "focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
          item.isActive && "bg-accent text-accent-foreground",
          level > 0 && "ml-4",
        )}
        aria-expanded={hasChildren ? isExpanded : undefined}
        aria-haspopup={hasChildren ? "true" : undefined}
      >
        <div className="flex items-center space-x-3">
          <item.icon className="h-4 w-4 flex-shrink-0" aria-hidden="true" />
          <span className="truncate">{item.label}</span>
          {item.badge && (
            <Badge variant="secondary" className="ml-auto text-xs" aria-label={`${item.badge} items`}>
              {item.badge}
            </Badge>
          )}
        </div>
        {hasChildren && (
          <ChevronRight className={cn("h-4 w-4 transition-transform", isExpanded && "rotate-90")} aria-hidden="true" />
        )}
      </button>

      {hasChildren && isExpanded && (
        <div className="mt-1 space-y-1" role="group" aria-label={`${item.label} submenu`}>
          {item.children?.map((child) => (
            <NavigationItem key={child.id} item={child} level={level + 1} onNavigate={onNavigate} />
          ))}
        </div>
      )}
    </div>
  )
}

const Sidebar: React.FC<{
  onNavigate?: (itemId: string) => void
  className?: string
}> = ({ onNavigate, className }) => {
  return (
    <div className={cn("flex flex-col h-full", className)}>
      <div className="p-6">
        <div className="flex items-center space-x-2">
          <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
            <GraduationCap className="h-5 w-5 text-primary-foreground" />
          </div>
          <div>
            <h2 className="text-lg font-semibold">EduData BD</h2>
            <p className="text-xs text-muted-foreground">Education Analytics</p>
          </div>
        </div>
      </div>

      <Separator />

      <ScrollArea className="flex-1 px-3 py-4">
        <nav className="space-y-1" role="navigation" aria-label="Main navigation">
          {navigationItems.map((item) => (
            <NavigationItem key={item.id} item={item} onNavigate={onNavigate} />
          ))}
        </nav>
      </ScrollArea>
    </div>
  )
}

const Header: React.FC<{
  title?: string
  subtitle?: string
  user?: DashboardLayoutProps["user"]
  notifications?: number
  onSearch?: (query: string) => void
  onMobileMenuToggle?: () => void
}> = ({ title, subtitle, user, notifications = 0, onSearch, onMobileMenuToggle }) => {
  const [searchQuery, setSearchQuery] = useState("")
  // const { toast } = useToast()

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (onSearch) {
      onSearch(searchQuery);
      console.log(`Searching for: ${searchQuery}`);
      // toast({
      //   title: "Searching...",
      //   description: `Searching for "${searchQuery}"`,
      // })
    } else {
      console.log(`Search not implemented for: ${searchQuery}`);
      // toast({
      //   title: "Search not implemented",
      //   description: `Search functionality will be implemented soon.`,
      //   variant: "destructive",
      // })
    }
  };

  const handleProfileClick = () => {
    console.log("Viewing profile information");
    // toast({
    //   title: "Profile",
    //   description: "Viewing your profile information.",
    // })
  };

  return (
    <header className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="flex h-16 items-center px-4 lg:px-6">
        {/* Mobile menu button */}
{{ ... }}
          variant="ghost"
          size="icon"
          className="md:hidden mr-2"
          onClick={onMobileMenuToggle}
          aria-label="Toggle navigation menu"
        >
          <Menu className="h-5 w-5" />
        </Button>

        {/* Title and subtitle */}
        <div className="flex-1">
          {title && (
            <div>
              <h1 className="text-lg font-semibold">{title}</h1>
              {subtitle && <p className="text-sm text-muted-foreground">{subtitle}</p>}
            </div>
          )}
        </div>

        {/* Search */}
        <div className="flex items-center space-x-4">
          <form onSubmit={handleSearchSubmit} className="hidden md:block">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                type="search"
                placeholder="Search..."
                className="pl-10 w-64"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                aria-label="Search dashboard"
              />
            </div>
          </form>

          {/* Notifications */}
          <Button
            variant="ghost"
            size="icon"
            className="relative"
            onClick={handleNotificationClick}
            aria-label={`Notifications (${notifications} unread)`}
          >
            <Bell className="h-5 w-5" />
            {notifications > 0 && (
              <Badge
                className="absolute -top-1 -right-1 h-5 w-5 rounded-full p-0 flex items-center justify-center text-xs"
                aria-hidden="true"
              >
                {notifications > 99 ? "99+" : notifications}
              </Badge>
            )}
          </Button>

          {/* User menu */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" className="relative h-8 w-8 rounded-full" aria-label="User menu">
                <Avatar className="h-8 w-8">
                  <AvatarImage src={user?.avatar || "/placeholder.svg"} alt={user?.name} />
                  <AvatarFallback>
                    {user?.name
                      ?.split(" ")
                      .map((n) => n[0])
                      .join("")
                      .toUpperCase() || "U"}
                  </AvatarFallback>
                </Avatar>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent className="w-56" align="end" forceMount>
              <DropdownMenuLabel className="font-normal">
                <div className="flex flex-col space-y-1">
                  <p className="text-sm font-medium leading-none">{user?.name}</p>
                  <p className="text-xs leading-none text-muted-foreground">{user?.email}</p>
                  <Badge variant="outline" className="w-fit text-xs">
                    {user?.role}
                  </Badge>
                </div>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem>
                <User className="mr-2 h-4 w-4" />
                <span>Profile</span>
              </DropdownMenuItem>
              <DropdownMenuItem>
                <Settings className="mr-2 h-4 w-4" />
                <span>Settings</span>
              </DropdownMenuItem>
              <DropdownMenuItem>
                <HelpCircle className="mr-2 h-4 w-4" />
                <span>Help</span>
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={handleLogout}>
                <LogOut className="mr-2 h-4 w-4" />
                <span>Log out</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </header>
  )
}

export const DashboardLayout: React.FC<DashboardLayoutProps> = ({
  children,
  title,
  subtitle,
  isLoading = false,
  error = null,
  user = {
    name: "John Doe",
    email: "john.doe@education.gov.bd",
    role: "Administrator",
  },
  notifications = 3,
  onSearch,
  onNavigate,
  className,
}) => {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)

  // Close mobile menu on route change
  useEffect(() => {
    setIsMobileMenuOpen(false)
  }, [title])

  const handleMobileMenuToggle = () => {
    setIsMobileMenuOpen(!isMobileMenuOpen)
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <ErrorBoundary>
          <div className="text-red-500">
            <h2 className="text-xl font-bold">An error occurred</h2>
            <p>{error.message}</p>
          </div>
        </ErrorBoundary>
      </div>
    )
  }

  return (
    <div className={cn("min-h-screen bg-background", className)}>
      {/* Desktop Sidebar */}
      <div className="hidden md:fixed md:inset-y-0 md:z-50 md:flex md:w-72 md:flex-col">
        <div className="flex grow flex-col gap-y-5 overflow-y-auto border-r bg-background px-6">
          <Sidebar onNavigate={onNavigate} />
        </div>
      </div>

      {/* Mobile Sidebar */}
      <Sheet open={isMobileMenuOpen} onOpenChange={setIsMobileMenuOpen}>
        <SheetContent side="left" className="w-72 p-0">
          <Sidebar onNavigate={onNavigate} />
        </SheetContent>
      </Sheet>

      {/* Main Content */}
      <div className="md:pl-72">
        <Header
          title={title}
          subtitle={subtitle}
          user={user}
          notifications={notifications}
          onSearch={onSearch}
          onMobileMenuToggle={handleMobileMenuToggle}
        />

        <main className="py-6">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            {isLoading ? (
              <div className="flex items-center justify-center min-h-[400px]">
                <LoadingSpinner size="lg" />
              </div>
            ) : (
              <ErrorBoundary>{children}</ErrorBoundary>
            )}
          </div>
        </main>
      </div>
    </div>
  )
}

export default DashboardLayout
