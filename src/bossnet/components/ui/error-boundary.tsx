"use client"

import React from "react"
import { AlertTriangle, RefreshCw, Home, Bug } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { cn } from "@/lib/utils"

interface ErrorBoundaryState {
  hasError: boolean
  error: Error | null
  errorInfo: React.ErrorInfo | null
}

interface ErrorBoundaryProps {
  children?: React.ReactNode
  fallback?: React.ComponentType<ErrorFallbackProps>
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void
  className?: string
}

interface ErrorFallbackProps {
  error: Error
  errorInfo?: React.ErrorInfo
  resetError?: () => void
  className?: string
}

export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    }
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return {
      hasError: true,
      error,
    }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    this.setState({
      error,
      errorInfo,
    })

    // Log error to monitoring service
    console.error("ErrorBoundary caught an error:", error, errorInfo)

    // Call onError callback if provided
    this.props.onError?.(error, errorInfo)
  }

  resetError = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    })
  }

  render() {
    if (this.state.hasError) {
      const FallbackComponent = this.props.fallback || DefaultErrorFallback

      return (
        <FallbackComponent
          error={this.state.error!}
          errorInfo={this.state.errorInfo || undefined}
          resetError={this.resetError}
          className={this.props.className}
        />
      )
    }

    return this.props.children
  }
}

export const DefaultErrorFallback: React.FC<ErrorFallbackProps> = ({ error, errorInfo, resetError, className }) => {
  const [showDetails, setShowDetails] = React.useState(false)
  const isDevelopment = process.env.NODE_ENV === "development"

  const handleReload = () => {
    window.location.reload()
  }

  const handleGoHome = () => {
    window.location.href = "/"
  }

  const handleReportError = () => {
    // In a real app, this would send error details to a reporting service
    const errorReport = {
      message: error.message,
      stack: error.stack,
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent,
      url: window.location.href,
    }

    console.log("Error report:", errorReport)

    // You could integrate with services like Sentry, Bugsnag, etc.
    alert("Error report has been logged. Thank you for helping us improve!")
  }

  return (
    <div className={cn("min-h-[400px] flex items-center justify-center p-4", className)}>
      <Card className="w-full max-w-2xl">
        <CardHeader className="text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-red-100">
            <AlertTriangle className="h-6 w-6 text-red-600" />
          </div>
          <CardTitle className="text-xl font-semibold text-red-900">Something went wrong</CardTitle>
          <CardDescription className="text-red-700">
            We're sorry, but an unexpected error occurred. Please try refreshing the page or contact support if the
            problem persists.
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-4">
          {isDevelopment && (
            <Alert variant="destructive">
              <Bug className="h-4 w-4" />
              <AlertDescription className="font-mono text-sm">
                <strong>Error:</strong> {error.message}
              </AlertDescription>
            </Alert>
          )}

          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Button onClick={resetError} variant="default" className="flex items-center">
              <RefreshCw className="mr-2 h-4 w-4" />
              Try Again
            </Button>

            <Button onClick={handleReload} variant="outline" className="flex items-center bg-transparent">
              <RefreshCw className="mr-2 h-4 w-4" />
              Reload Page
            </Button>

            <Button onClick={handleGoHome} variant="outline" className="flex items-center bg-transparent">
              <Home className="mr-2 h-4 w-4" />
              Go Home
            </Button>
          </div>

          <div className="text-center">
            <Button
              onClick={handleReportError}
              variant="ghost"
              size="sm"
              className="text-muted-foreground hover:text-foreground"
            >
              <Bug className="mr-2 h-4 w-4" />
              Report this error
            </Button>
          </div>

          {isDevelopment && (
            <div className="mt-6">
              <Button onClick={() => setShowDetails(!showDetails)} variant="ghost" size="sm" className="w-full">
                {showDetails ? "Hide" : "Show"} Error Details
              </Button>

              {showDetails && (
                <div className="mt-4 p-4 bg-gray-50 rounded-lg">
                  <h4 className="font-semibold mb-2">Error Details:</h4>
                  <pre className="text-xs overflow-auto whitespace-pre-wrap text-gray-700">{error.stack}</pre>

                  {errorInfo && (
                    <>
                      <h4 className="font-semibold mt-4 mb-2">Component Stack:</h4>
                      <pre className="text-xs overflow-auto whitespace-pre-wrap text-gray-700">
                        {errorInfo.componentStack}
                      </pre>
                    </>
                  )}
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

// Hook for functional components
export const useErrorHandler = () => {
  const [error, setError] = React.useState<Error | null>(null)

  const resetError = React.useCallback(() => {
    setError(null)
  }, [])

  const captureError = React.useCallback((error: Error) => {
    setError(error)
  }, [])

  React.useEffect(() => {
    if (error) {
      throw error
    }
  }, [error])

  return { captureError, resetError }
}

// Simple error fallback for specific components
export const SimpleErrorFallback: React.FC<{
  message?: string
  onRetry?: () => void
  className?: string
}> = ({ message = "Something went wrong", onRetry, className }) => {
  return (
    <div className={cn("flex flex-col items-center justify-center p-8 text-center", className)}>
      <AlertTriangle className="h-8 w-8 text-red-500 mb-4" />
      <h3 className="text-lg font-semibold text-red-900 mb-2">Error</h3>
      <p className="text-red-700 mb-4">{message}</p>
      {onRetry && (
        <Button onClick={onRetry} variant="outline" size="sm">
          <RefreshCw className="mr-2 h-4 w-4" />
          Try Again
        </Button>
      )}
    </div>
  )
}

export default ErrorBoundary
