import { Button } from "./button"
import { AlertTriangle } from "lucide-react"

interface ErrorFallbackProps {
  error: Error
  resetErrorBoundary?: () => void
}

export const ErrorFallback: React.FC<ErrorFallbackProps> = ({
  error,
  resetErrorBoundary,
}) => {
  const handleReset = () => {
    if (resetErrorBoundary) {
      resetErrorBoundary()
    } else {
      window.location.reload()
    }
  }

  return (
    <div
      className="flex h-full flex-col items-center justify-center p-8 text-center"
      role="alert"
    >
      <div className="rounded-full bg-destructive/10 p-4">
        <AlertTriangle className="h-8 w-8 text-destructive" />
      </div>
      <h2 className="mt-4 text-lg font-medium">
        Something went wrong
      </h2>
      <p className="mt-2 text-sm text-muted-foreground">
        {error.message || 'An unexpected error occurred'}
      </p>
      <Button
        className="mt-4"
        onClick={handleReset}
        aria-label="Try again"
      >
        Try again
      </Button>
    </div>
  )
}
