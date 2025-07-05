"use client"

import React, { useState, useCallback, memo } from "react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Sheet, SheetContent } from "@/components/ui/sheet"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { LoadingSpinner } from "@/components/ui/loading-spinner"
import { ErrorBoundary } from "@/lib/error-boundary"
import { ErrorFallback } from "@/components/ui/error-fallback"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  Menu,
  Bell,
  Search,
  Settings,
  User,
  LogOut,
  ChevronRight,
  GraduationCap,
} from "lucide-react"
import type { NavigationItem } from "@/config/navigation"
import { navigationItems } from "@/config/navigation"

// Types
export interface User {
  name: string
  email: string
  avatar?: string
  role: string
}

export interface DashboardLayoutProps {
  children: React.ReactNode
  title?: string
  subtitle?: string
  isLoading?: boolean
  error?: Error | null
  user?: User
  notifications?: number
  onSearch?: (query: string) => void
  onNavigate?: (itemId: string) => void
  className?: string
}

// Navigation Item Component
const NavigationItemComponent: React.FC<{
  item: NavigationItem
  level?: number
  onNavigate?: (itemId: string) => void
}> = ({ item, level = 0, onNavigate }) => {
  const [isExpanded, setIsExpanded] = useState(false)
  const hasChildren = item.children && item.children.length > 0

  const handleClick = useCallback(() => {
    if (hasChildren) {
      setIsExpanded(prev => !prev)
    } else if (onNavigate) {
      onNavigate(item.id)
    }
  }, [hasChildren, item.id, onNavigate])

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      handleClick()
    }
  }, [handleClick])

  return (
    <li className="space-y-1">
      <button
        type="button"
        className={cn(
          'flex w-full items-center rounded-md px-3 py-2 text-sm font-medium transition-colors',
          'hover:bg-accent hover:text-accent-foreground',
          'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
          item.isActive ? 'bg-accent text-accent-foreground' : 'text-muted-foreground',
          level > 0 && 'pl-8',
          item.className
        )}
        onClick={handleClick}
        onKeyDown={handleKeyDown}
        aria-expanded={hasChildren ? isExpanded : undefined}
        aria-haspopup={hasChildren ? 'true' : undefined}
        aria-current={item.isActive ? 'page' : undefined}
        role={hasChildren ? 'button' : 'menuitem'}
        tabIndex={0}
      >
        <item.icon className="mr-3 h-5 w-5 flex-shrink-0" aria-hidden="true" />
        <span className="flex-1 text-left">{item.label}</span>
        {item.badge && (
          <Badge variant="secondary" className="ml-2">
            {item.badge}
          </Badge>
        )}
        {hasChildren && (
          <ChevronRight
            className={cn(
              'ml-2 h-4 w-4 transition-transform',
              isExpanded && 'rotate-90'
            )}
            aria-hidden="true"
          />
        )}
      </button>
      {hasChildren && isExpanded && (
        <ul className="ml-4 border-l-2 border-border pl-2">
          {item.children?.map((child) => (
            <NavigationItemComponent
              key={child.id}
              item={child}
              level={level + 1}
              onNavigate={onNavigate}
            />
          ))}
        </ul>
      )}
    </li>
  )
}

// Memoize the NavigationItem component
const NavigationItem = memo(NavigationItemComponent)

// Sidebar Component
const SidebarComponent: React.FC<{
  onNavigate?: (itemId: string) => void
  className?: string
}> = ({ onNavigate, className }) => {
  return (
    <div className={cn('flex h-full flex-col', className)}>
      <div className="p-6">
        <div className="flex items-center space-x-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
            <GraduationCap className="h-5 w-5 text-primary-foreground" aria-hidden="true" />
          </div>
          <div>
            <h2 className="text-lg font-semibold">EduData BD</h2>
            <p className="text-xs text-muted-foreground">Education Analytics</p>
          </div>
        </div>
      </div>
      <Separator />
      <ScrollArea className="flex-1">
        <nav aria-label="Main navigation">
          <ul className="space-y-1 p-4">
            {navigationItems.map((item) => (
              <NavigationItem
                key={item.id}
                item={item}
                onNavigate={onNavigate}
              />
            ))}
          </ul>
        </nav>
      </ScrollArea>
    </div>
  )
}

// Memoize the Sidebar component
const Sidebar = memo(SidebarComponent)

// Header Component
const HeaderComponent: React.FC<{
  title?: string
  subtitle?: string
  user?: User
  notifications?: number
  onSearch?: (query: string) => void
  onMobileMenuToggle?: () => void
}> = ({
  title = 'Dashboard',
  subtitle = 'Welcome back',
  user = {
    name: 'John Doe',
    email: 'john.doe@education.gov.bd',
    role: 'Administrator',
  },
  notifications = 0,
  onSearch,
  onMobileMenuToggle,
}) => {
  const [searchQuery, setSearchQuery] = useState('')

  const handleSearchSubmit = useCallback((e: React.FormEvent) => {
    e.preventDefault()
    if (onSearch && searchQuery.trim()) {
      onSearch(searchQuery.trim())
    }
  }, [onSearch, searchQuery])

  const handleNotificationClick = useCallback(() => {
    console.log('Notifications clicked')
  }, [])

  const handleLogout = useCallback(() => {
    console.log('Logout clicked')
  }, [])

  return (
    <header className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="flex h-16 items-center px-4">
        <Button
          variant="ghost"
          size="icon"
          className="mr-2 md:hidden"
          onClick={onMobileMenuToggle}
          aria-label="Toggle menu"
        >
          <Menu className="h-5 w-5" aria-hidden="true" />
        </Button>

        <div className="flex flex-1 items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold">{title}</h1>
            {subtitle && (
              <p className="text-sm text-muted-foreground">{subtitle}</p>
            )}
          </div>

          <div className="flex items-center space-x-4">
            <form onSubmit={handleSearchSubmit} className="hidden md:block">
              <div className="relative">
                <Search
                  className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground"
                  aria-hidden="true"
                />
                <Input
                  type="search"
                  placeholder="Search..."
                  className="w-full rounded-lg bg-background pl-8 md:w-[200px] lg:w-[336px]"
                  value={searchQuery}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                    setSearchQuery(e.target.value)
                  }
                  aria-label="Search"
                />
              </div>
            </form>

            <Button
              variant="ghost"
              size="icon"
              className="relative"
              onClick={handleNotificationClick}
              aria-label={`Notifications ${notifications > 0 ? `(${notifications} unread)` : ''}`}
            >
              <Bell className="h-5 w-5" aria-hidden="true" />
              {notifications > 0 && (
                <span className="absolute -right-1 -top-1 flex h-4 w-4 items-center justify-center rounded-full bg-primary text-xs text-primary-foreground">
                  {notifications > 9 ? '9+' : notifications}
                  <span className="sr-only">unread notifications</span>
                </span>
              )}
            </Button>

            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  className="relative h-8 w-8 rounded-full"
                  aria-label="User menu"
                >
                  <Avatar className="h-8 w-8">
                    <AvatarImage src={user.avatar} alt="" />
                    <AvatarFallback>
                      {user.name
                        .split(' ')
                        .map(n => n[0])
                        .join('')}
                    </AvatarFallback>
                  </Avatar>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent className="w-56" align="end" forceMount>
                <DropdownMenuLabel className="font-normal">
                  <div className="flex flex-col space-y-1">
                    <p className="text-sm font-medium leading-none">
                      {user.name}
                    </p>
                    <p className="text-xs leading-none text-muted-foreground">
                      {user.email}
                    </p>
                  </div>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem>
                  <User className="mr-2 h-4 w-4" aria-hidden="true" />
                  <span>Profile</span>
                </DropdownMenuItem>
                <DropdownMenuItem>
                  <Settings className="mr-2 h-4 w-4" aria-hidden="true" />
                  <span>Settings</span>
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onSelect={handleLogout}>
                  <LogOut className="mr-2 h-4 w-4" aria-hidden="true" />
                  <span>Log out</span>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </div>
    </header>
  )
}

// Memoize the Header component
const Header = memo(HeaderComponent)

// Main DashboardLayout Component
const DashboardLayout: React.FC<DashboardLayoutProps> = ({
  children,
  title,
  subtitle,
  isLoading = false,
  error = null,
  user = {
    name: 'John Doe',
    email: 'john.doe@education.gov.bd',
    role: 'Administrator',
  },
  notifications = 0,
  onSearch,
  onNavigate,
  className,
}) => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  const toggleMobileMenu = useCallback(() => {
    setMobileMenuOpen(prev => !prev)
  }, [])

  const handleSearch = useCallback((query: string) => {
    onSearch?.(query)
  }, [onSearch])

  return (
    <div className={cn('flex min-h-screen flex-col bg-background', className)}>
      <Header
        title={title}
        subtitle={subtitle}
        user={user}
        notifications={notifications}
        onSearch={handleSearch}
        onMobileMenuToggle={toggleMobileMenu}
      />

      <div className="flex flex-1 overflow-hidden">
        <aside className="hidden md:flex md:flex-shrink-0">
          <div className="flex w-64 flex-col border-r">
            <Sidebar onNavigate={onNavigate} />
          </div>
        </aside>

        <Sheet open={mobileMenuOpen} onOpenChange={setMobileMenuOpen}>
          <SheetContent side="left" className="w-72 p-0">
            <Sidebar onNavigate={onNavigate} />
          </SheetContent>
        </Sheet>

        <main
          className="flex-1 overflow-auto focus:outline-none"
          id="main-content"
          tabIndex={-1}
        >
          <ErrorBoundary FallbackComponent={ErrorFallback}>
            {isLoading ? (
              <div className="flex h-full items-center justify-center">
                <LoadingSpinner size="lg" aria-label="Loading..." />
              </div>
            ) : error ? (
              <ErrorFallback error={error} />
            ) : (
              <div className="h-full">{children}</div>
            )}
          </ErrorBoundary>
        </main>
      </div>
    </div>
  )
}

export type { User, DashboardLayoutProps }
export default memo(DashboardLayout)
