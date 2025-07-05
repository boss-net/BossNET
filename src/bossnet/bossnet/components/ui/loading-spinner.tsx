"use client";

import React from "react";
import { cn } from "@/lib/utils";
import { Loader2 } from "lucide-react";

interface LoadingSpinnerProps {
  size?: "sm" | "md" | "lg" | "xl";
  className?: string;
  text?: string;
  variant?: "default" | "overlay";
}

const sizeClasses = {
  sm: "h-4 w-4",
  md: "h-6 w-6",
  lg: "h-8 w-8",
  xl: "h-12 w-12",
};

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  size = "md",
  className,
  text,
  variant = "default",
}) => {
  if (variant === "overlay") {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm">
        <div className="flex flex-col items-center space-y-4">
          <Loader2
            className={cn(
              "animate-spin text-primary",
              sizeClasses[size],
              className
            )}
          />
          {text && (
            <p className="text-sm text-muted-foreground" aria-live="polite">
              {text}
            </p>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-center space-x-2">
      <Loader2
        className={cn("animate-spin text-primary", sizeClasses[size], className)}
        aria-hidden="true"
      />
      {text && (
        <span className="text-sm text-muted-foreground" aria-live="polite">
          {text}
        </span>
      )}
    </div>
  );
};

export const LoadingCard: React.FC<{
  className?: string;
  children?: React.ReactNode;
}> = ({ className, children }) => {
  return (
    <div className={cn("flex items-center justify-center p-8", className)}>
      <div className="flex flex-col items-center space-y-4">
        <LoadingSpinner size="lg" />
        {children}
      </div>
    </div>
  );
};

export const LoadingTable: React.FC<{
  rows?: number;
  columns?: number;
  className?: string;
}> = ({ rows = 5, columns = 4, className }) => {
  return (
    <div className={cn("space-y-3", className)}>
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <div key={rowIndex} className="flex space-x-4">
          {Array.from({ length: columns }).map((_, colIndex) => (
            <div
              key={colIndex}
              className="h-4 bg-muted rounded animate-pulse flex-1"
            />
          ))}
        </div>
      ))}
    </div>
  );
};

export function SimpleLoadingSpinner() {
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
      }}
    >
      <div
        className="spinner"
        style={{
          width: 32,
          height: 32,
          border: "4px solid #ccc",
          borderTop: "4px solid #333",
          borderRadius: "50%",
          animation: "spin 1s linear infinite",
        }}
      />
      <style>{`
        @keyframes spin {
          0% { transform: rotate(0deg);}
          100% { transform: rotate(360deg);}
        }
      `}</style>
    </div>
  );
}

export default LoadingSpinner;
