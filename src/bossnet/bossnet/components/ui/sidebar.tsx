'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';

const SidebarContext = React.createContext<{
  isOpen: boolean;
  setIsOpen: (open: boolean) => void;
} | null>(null);

export function SidebarProvider({ children }: { children: React.ReactNode }) {
  const [isOpen, setIsOpen] = React.useState(false);

  return (
    <SidebarContext.Provider value={{ isOpen, setIsOpen }}>
      {children}
    </SidebarContext.Provider>
  );
}

export function useSidebar() {
  const context = React.useContext(SidebarContext);
  if (!context) {
    throw new Error('useSidebar must be used within a SidebarProvider');
  }
  return context;
}

export function SidebarTrigger({ className, ...props }: React.HTMLAttributes<HTMLButtonElement>) {
  const { setIsOpen } = useSidebar();

  return (
    <button
      type="button"
      className={cn(
        'inline-flex items-center justify-center rounded-md p-2 text-gray-700 hover:bg-gray-100',
        className
      )}
      onClick={() => setIsOpen(true)}
      {...props}
    >
      <span className="sr-only">Open sidebar</span>
      <svg
        className="h-6 w-6"
        fill="none"
        viewBox="0 0 24 24"
        strokeWidth="1.5"
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5"
        />
      </svg>
    </button>
  );
}
