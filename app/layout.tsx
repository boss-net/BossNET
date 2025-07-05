import type { Metadata } from "next";
import "./globals.css";
import ClientLayout from "../src/app/components/ClientLayout";

export const metadata: Metadata = {
  title: "BossNET",
  description: "BossNET - Educational Management System",
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <ClientLayout>
          {children}
        </ClientLayout>
      </body>
    </html>
  )
}
