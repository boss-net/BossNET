'use client';

import { SidebarTrigger, SidebarProvider } from "../../components/ui/sidebar";
import { AppSidebar } from "../../components/AppSidebar";
import dynamic from 'next/dynamic';

// Dynamically import the client component with no SSR
const RemoveDarkreader = dynamic<{}>(
  () => import('../../components/client/RemoveDarkreader').then((mod) => mod.RemoveDarkreader),
  { ssr: false }
);

export default function ClientLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <RemoveDarkreader />
      <SidebarProvider>
        <AppSidebar />
        <main>
          <SidebarTrigger />
          {children}
        </main>
      </SidebarProvider>
    </>
  );
}
