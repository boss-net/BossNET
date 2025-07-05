"use client"

import React from "react"
import { cn } from "@/lib/utils"
import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Checkbox } from "@/components/ui/checkbox"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { Switch } from "@/components/ui/switch"
import { Button } from "@/components/ui/button"
import { Calendar } from "@/components/ui/calendar"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { AlertCircle, CalendarIcon, Eye, EyeOff } from "lucide-react"
import { format } from "date-fns"

export interface FormFieldProps {
  id: string
  name: string
  label: string
  type?:
    | "text"
    | "email"
    | "password"
    | "number"
    | "tel"
    | "url"
    | "search"
    | "textarea"
    | "select"
    | "checkbox"
    | "radio"
    | "switch"
    | "date"
    | "file"
  placeholder?: string
  value?: any
  defaultValue?: any
  options?: Array<{ value: string; label: string; disabled?: boolean }>
  required?: boolean
  disabled?: boolean
  readOnly?: boolean
  error?: string
  helperText?: string
  description?: string
  validation?: {
    required?: boolean | string
    minLength?: number | { value: number; message: string }
    maxLength?: number | { value: number; message: string }
    min?: number | { value: number; message: string }
    max?: number | { value: number; message: string }
    pattern?: RegExp | { value: RegExp; message: string }
    validate?: (value: any) => boolean | string
  }
  onChange?: (value: any) => void
  onBlur?: () => void
  onFocus?: () => void
  className?: string
  inputClassName?: string
  labelClassName?: string
  "aria-describedby"?: string
  "aria-invalid"?: boolean
}

export const FormField: React.FC<FormFieldProps> = ({
  id,
  name,
  label,
  type = "text",
  placeholder,
  value,
  defaultValue,
  options = [],
  required = false,
  disabled = false,
  readOnly = false,
  error,
  helperText,
  description,
  validation,
  onChange,
  onBlur,
  onFocus,
  className,
  inputClassName,
  labelClassName,
  "aria-describedby": ariaDescribedBy,
  "aria-invalid": ariaInvalid,
  ...props
}) => {
  const [showPassword, setShowPassword] = React.useState(false)
  const [internalValue, setInternalValue] = React.useState(value || defaultValue || "")

  const handleChange = (newValue: any) => {
    setInternalValue(newValue)
    onChange?.(newValue)
  }

  const fieldId = id || name
  const errorId = `${fieldId}-error`
  const helperId = `${fieldId}-helper`
  const descriptionId = `${fieldId}-description`

  const getAriaDescribedBy = () => {
    const ids = []
    if (error) ids.push(errorId)
    if (helperText) ids.push(helperId)
    if (description) ids.push(descriptionId)
    if (ariaDescribedBy) ids.push(ariaDescribedBy)
    return ids.length > 0 ? ids.join(" ") : undefined
  }

  const commonProps = {
    id: fieldId,
    name,
    disabled,
    readOnly,
    onBlur,
    onFocus,
    "aria-describedby": getAriaDescribedBy(),
    "aria-invalid": ariaInvalid || !!error,
    "aria-required": required,
  }

  const renderInput = () => {
    switch (type) {
      case "textarea":
        return (
          <Textarea
            {...commonProps}
            placeholder={placeholder}
            value={internalValue}
            onChange={(e) => handleChange(e.target.value)}
            className={cn(error && "border-red-500 focus:border-red-500 focus:ring-red-500", inputClassName)}
            rows={4}
            {...props}
          />
        )

      case "select":
        return (
          <Select value={internalValue} onValueChange={handleChange} disabled={disabled} required={required}>
            <SelectTrigger
              className={cn(error && "border-red-500 focus:border-red-500 focus:ring-red-500", inputClassName)}
              aria-describedby={getAriaDescribedBy()}
              aria-invalid={ariaInvalid || !!error}
            >
              <SelectValue placeholder={placeholder} />
            </SelectTrigger>
            <SelectContent>
              {options.map((option) => (
                <SelectItem key={option.value} value={option.value} disabled={option.disabled}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )

      case "checkbox":
        return (
          <div className="flex items-center space-x-2">
            <Checkbox
              {...commonProps}
              checked={internalValue}
              onCheckedChange={handleChange}
              className={cn(error && "border-red-500 focus:border-red-500 focus:ring-red-500", inputClassName)}
            />
            <Label
              htmlFor={fieldId}
              className={cn(
                "text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70",
                labelClassName,
              )}
            >
              {label}
              {required && (
                <span className="text-red-500 ml-1" aria-label="required">
                  *
                </span>
              )}
            </Label>
          </div>
        )

      case "radio":
        return (
          <RadioGroup
            value={internalValue}
            onValueChange={handleChange}
            disabled={disabled}
            className={inputClassName}
            aria-describedby={getAriaDescribedBy()}
            aria-invalid={ariaInvalid || !!error}
            aria-required={required}
          >
            {options.map((option) => (
              <div key={option.value} className="flex items-center space-x-2">
                <RadioGroupItem value={option.value} id={`${fieldId}-${option.value}`} disabled={option.disabled} />
                <Label
                  htmlFor={`${fieldId}-${option.value}`}
                  className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                >
                  {option.label}
                </Label>
              </div>
            ))}
          </RadioGroup>
        )

      case "switch":
        return (
          <div className="flex items-center space-x-2">
            <Switch
              {...commonProps}
              checked={internalValue}
              onCheckedChange={handleChange}
              className={inputClassName}
            />
            <Label
              htmlFor={fieldId}
              className={cn(
                "text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70",
                labelClassName,
              )}
            >
              {label}
              {required && (
                <span className="text-red-500 ml-1" aria-label="required">
                  *
                </span>
              )}
            </Label>
          </div>
        )

      case "date":
        return (
          <Popover>
            <PopoverTrigger asChild>
              <Button
                variant="outline"
                className={cn(
                  "w-full justify-start text-left font-normal",
                  !internalValue && "text-muted-foreground",
                  error && "border-red-500 focus:border-red-500 focus:ring-red-500",
                  inputClassName,
                )}
                disabled={disabled}
                aria-describedby={getAriaDescribedBy()}
                aria-invalid={ariaInvalid || !!error}
                aria-required={required}
              >
                <CalendarIcon className="mr-2 h-4 w-4" />
                {internalValue ? format(internalValue, "PPP") : placeholder || "Pick a date"}
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-auto p-0" align="start">
              <Calendar
                mode="single"
                selected={internalValue}
                onSelect={handleChange}
                disabled={disabled}
                initialFocus
              />
            </PopoverContent>
          </Popover>
        )

      case "password":
        return (
          <div className="relative">
            <Input
              {...commonProps}
              type={showPassword ? "text" : "password"}
              placeholder={placeholder}
              value={internalValue}
              onChange={(e) => handleChange(e.target.value)}
              className={cn("pr-10", error && "border-red-500 focus:border-red-500 focus:ring-red-500", inputClassName)}
              {...props}
            />
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
              onClick={() => setShowPassword(!showPassword)}
              aria-label={showPassword ? "Hide password" : "Show password"}
              tabIndex={-1}
            >
              {showPassword ? (
                <EyeOff className="h-4 w-4 text-muted-foreground" />
              ) : (
                <Eye className="h-4 w-4 text-muted-foreground" />
              )}
            </Button>
          </div>
        )

      case "file":
        return (
          <Input
            {...commonProps}
            type="file"
            onChange={(e) => handleChange(e.target.files)}
            className={cn(error && "border-red-500 focus:border-red-500 focus:ring-red-500", inputClassName)}
            {...props}
          />
        )

      default:
        return (
          <Input
            {...commonProps}
            type={type}
            placeholder={placeholder}
            value={internalValue}
            onChange={(e) => handleChange(e.target.value)}
            className={cn(error && "border-red-500 focus:border-red-500 focus:ring-red-500", inputClassName)}
            {...props}
          />
        )
    }
  }

  return (
    <div className={cn("space-y-2", className)}>
      {type !== "checkbox" && type !== "switch" && (
        <Label
          htmlFor={fieldId}
          className={cn(
            "text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70",
            labelClassName,
          )}
        >
          {label}
          {required && (
            <span className="text-red-500 ml-1" aria-label="required">
              *
            </span>
          )}
        </Label>
      )}

      {description && (
        <p id={descriptionId} className="text-sm text-muted-foreground">
          {description}
        </p>
      )}

      {renderInput()}

      {error && (
        <div id={errorId} className="flex items-center space-x-1 text-sm text-red-600" role="alert">
          <AlertCircle className="h-4 w-4" />
          <span>{error}</span>
        </div>
      )}

      {helperText && !error && (
        <p id={helperId} className="text-sm text-muted-foreground">
          {helperText}
        </p>
      )}
    </div>
  )
}

export default FormField
