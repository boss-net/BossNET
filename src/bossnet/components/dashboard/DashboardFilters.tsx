"use client"

import React from "react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Checkbox } from "@/components/ui/checkbox"
import { Calendar } from "@/components/ui/calendar"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Filter, X, CalendarIcon, Search, RotateCcw, Download, Settings } from "lucide-react"
import { format } from "date-fns"

interface FilterOption {
  value: string
  label: string
  count?: number
}

interface FilterConfig {
  id: string
  label: string
  type: "select" | "multiselect" | "search" | "date" | "daterange" | "checkbox"
  options?: FilterOption[]
  placeholder?: string
  value?: any
  required?: boolean
}

interface DashboardFiltersProps {
  filters: FilterConfig[]
  values: Record<string, any>
  onFilterChange: (filterId: string, value: any) => void
  onApplyFilters: () => void
  onResetFilters: () => void
  onExportData?: () => void
  isLoading?: boolean
  className?: string
  showApplyButton?: boolean
  showResetButton?: boolean
  showExportButton?: boolean
  compact?: boolean
}

export const DashboardFilters: React.FC<DashboardFiltersProps> = ({
  filters = [],
  values = {},
  onFilterChange,
  onApplyFilters,
  onResetFilters,
  onExportData,
  isLoading = false,
  className,
  showApplyButton = true,
  showResetButton = true,
  showExportButton = true,
  compact = false,
}) => {
  const [isExpanded, setIsExpanded] = React.useState(!compact)
  const [searchQuery, setSearchQuery] = React.useState("")

  const activeFiltersCount = Object.values(values).filter((value) => {
    if (Array.isArray(value)) return value.length > 0
    if (typeof value === "string") return value.trim() !== ""
    if (typeof value === "boolean") return value
    return value != null
  }).length

  const handleFilterChange = (filterId: string, value: any) => {
    onFilterChange(filterId, value)
  }

  const handleRemoveFilter = (filterId: string) => {
    const filter = filters.find((f) => f.id === filterId)
    if (filter) {
      const defaultValue = filter.type === "multiselect" ? [] : filter.type === "checkbox" ? false : ""
      onFilterChange(filterId, defaultValue)
    }
  }

  const renderFilter = (filter: FilterConfig) => {
    const value = values[filter.id]

    switch (filter.type) {
      case "search":
        return (
          <div className="space-y-2">
            <Label htmlFor={filter.id}>{filter.label}</Label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                id={filter.id}
                type="search"
                placeholder={filter.placeholder}
                value={value || ""}
                onChange={(e) => handleFilterChange(filter.id, e.target.value)}
                className="pl-10"
                disabled={isLoading}
              />
            </div>
          </div>
        )

      case "select":
        return (
          <div className="space-y-2">
            <Label htmlFor={filter.id}>{filter.label}</Label>
            <Select
              value={value || ""}
              onValueChange={(newValue) => handleFilterChange(filter.id, newValue)}
              disabled={isLoading}
            >
              <SelectTrigger>
                <SelectValue placeholder={filter.placeholder} />
              </SelectTrigger>
              <SelectContent>
                {filter.options?.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    <div className="flex items-center justify-between w-full">
                      <span>{option.label}</span>
                      {option.count && (
                        <Badge variant="secondary" className="ml-2">
                          {option.count}
                        </Badge>
                      )}
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        )

      case "multiselect":
        const selectedValues = value || []
        return (
          <div className="space-y-2">
            <Label>{filter.label}</Label>
            <Popover>
              <PopoverTrigger asChild>
                <Button
                  variant="outline"
                  className="w-full justify-start text-left font-normal bg-transparent"
                  disabled={isLoading}
                >
                  {selectedValues.length > 0 ? (
                    <div className="flex flex-wrap gap-1">
                      {selectedValues.slice(0, 2).map((val: string) => {
                        const option = filter.options?.find((opt) => opt.value === val)
                        return (
                          <Badge key={val} variant="secondary" className="text-xs">
                            {option?.label || val}
                          </Badge>
                        )
                      })}
                      {selectedValues.length > 2 && (
                        <Badge variant="secondary" className="text-xs">
                          +{selectedValues.length - 2} more
                        </Badge>
                      )}
                    </div>
                  ) : (
                    <span className="text-muted-foreground">{filter.placeholder}</span>
                  )}
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-80 p-0" align="start">
                <div className="p-4">
                  <Input
                    placeholder="Search options..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="mb-3"
                  />
                  <ScrollArea className="h-48">
                    <div className="space-y-2">
                      {filter.options
                        ?.filter((option) => option.label.toLowerCase().includes(searchQuery.toLowerCase()))
                        .map((option) => (
                          <div key={option.value} className="flex items-center space-x-2">
                            <Checkbox
                              id={`${filter.id}-${option.value}`}
                              checked={selectedValues.includes(option.value)}
                              onCheckedChange={(checked) => {
                                const newValues = checked
                                  ? [...selectedValues, option.value]
                                  : selectedValues.filter((v: string) => v !== option.value)
                                handleFilterChange(filter.id, newValues)
                              }}
                            />
                            <Label
                              htmlFor={`${filter.id}-${option.value}`}
                              className="text-sm font-normal flex-1 cursor-pointer"
                            >
                              <div className="flex items-center justify-between">
                                <span>{option.label}</span>
                                {option.count && (
                                  <Badge variant="outline" className="text-xs">
                                    {option.count}
                                  </Badge>
                                )}
                              </div>
                            </Label>
                          </div>
                        ))}
                    </div>
                  </ScrollArea>
                </div>
              </PopoverContent>
            </Popover>
          </div>
        )

      case "date":
        return (
          <div className="space-y-2">
            <Label>{filter.label}</Label>
            <Popover>
              <PopoverTrigger asChild>
                <Button
                  variant="outline"
                  className="w-full justify-start text-left font-normal bg-transparent"
                  disabled={isLoading}
                >
                  <CalendarIcon className="mr-2 h-4 w-4" />
                  {value ? format(value, "PPP") : filter.placeholder || "Pick a date"}
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-auto p-0" align="start">
                <Calendar
                  mode="single"
                  selected={value}
                  onSelect={(date) => handleFilterChange(filter.id, date)}
                  disabled={isLoading}
                  initialFocus
                />
              </PopoverContent>
            </Popover>
          </div>
        )

      case "daterange":
        return (
          <div className="space-y-2">
            <Label>{filter.label}</Label>
            <Popover>
              <PopoverTrigger asChild>
                <Button
                  variant="outline"
                  className="w-full justify-start text-left font-normal bg-transparent"
                  disabled={isLoading}
                >
                  <CalendarIcon className="mr-2 h-4 w-4" />
                  {value?.from ? (
                    value.to ? (
                      <>
                        {format(value.from, "LLL dd, y")} - {format(value.to, "LLL dd, y")}
                      </>
                    ) : (
                      format(value.from, "LLL dd, y")
                    )
                  ) : (
                    filter.placeholder || "Pick a date range"
                  )}
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-auto p-0" align="start">
                <Calendar
                  initialFocus
                  mode="range"
                  defaultMonth={value?.from}
                  selected={value}
                  onSelect={(range) => handleFilterChange(filter.id, range)}
                  numberOfMonths={2}
                  disabled={isLoading}
                />
              </PopoverContent>
            </Popover>
          </div>
        )

      case "checkbox":
        return (
          <div className="flex items-center space-x-2">
            <Checkbox
              id={filter.id}
              checked={value || false}
              onCheckedChange={(checked) => handleFilterChange(filter.id, checked)}
              disabled={isLoading}
            />
            <Label
              htmlFor={filter.id}
              className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
            >
              {filter.label}
            </Label>
          </div>
        )

      default:
        return null
    }
  }

  return (
    <div className={cn("space-y-4", className)}>
      {/* Filter Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Filter className="h-5 w-5" />
          <h3 className="text-lg font-semibold">Filters</h3>
          {activeFiltersCount > 0 && <Badge variant="secondary">{activeFiltersCount} active</Badge>}
        </div>

        {compact && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsExpanded(!isExpanded)}
            aria-label={isExpanded ? "Collapse filters" : "Expand filters"}
          >
            <Settings className="h-4 w-4" />
          </Button>
        )}
      </div>

      {/* Active Filters */}
      {activeFiltersCount > 0 && (
        <div className="flex flex-wrap gap-2">
          {filters.map((filter) => {
            const value = values[filter.id]
            if (!value || (Array.isArray(value) && value.length === 0)) return null

            return (
              <Badge key={filter.id} variant="outline" className="flex items-center gap-1">
                <span className="text-xs">
                  {filter.label}:{" "}
                  {Array.isArray(value)
                    ? `${value.length} selected`
                    : typeof value === "boolean"
                      ? "Yes"
                      : value.toString()}
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-auto p-0 ml-1"
                  onClick={() => handleRemoveFilter(filter.id)}
                  aria-label={`Remove ${filter.label} filter`}
                >
                  <X className="h-3 w-3" />
                </Button>
              </Badge>
            )
          })}
        </div>
      )}

      {/* Filter Controls */}
      {isExpanded && (
        <>
          <Separator />

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {filters.map((filter) => (
              <div key={filter.id}>{renderFilter(filter)}</div>
            ))}
          </div>

          {/* Action Buttons */}
          <div className="flex flex-wrap gap-2 pt-4">
            {showApplyButton && (
              <Button onClick={onApplyFilters} disabled={isLoading} className="flex items-center">
                <Filter className="mr-2 h-4 w-4" />
                Apply Filters
              </Button>
            )}

            {showResetButton && activeFiltersCount > 0 && (
              <Button
                variant="outline"
                onClick={onResetFilters}
                disabled={isLoading}
                className="flex items-center bg-transparent"
              >
                <RotateCcw className="mr-2 h-4 w-4" />
                Reset
              </Button>
            )}

            {showExportButton && onExportData && (
              <Button
                variant="outline"
                onClick={onExportData}
                disabled={isLoading}
                className="flex items-center bg-transparent"
              >
                <Download className="mr-2 h-4 w-4" />
                Export
              </Button>
            )}
          </div>
        </>
      )}
    </div>
  )
}

export default DashboardFilters
