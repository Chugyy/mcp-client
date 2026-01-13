'use client';

import { SidebarProvider } from '@/components/ui/sidebar';
import { Sidebar } from '@/components/layouts/sidebar';
import { ChatProvider } from '@/contexts/chat-context';

/**
 * Layout pour toutes les routes protégées
 * L'authentification est vérifiée par le middleware avant d'arriver ici
 */
export default function ProtectedLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ChatProvider>
      <SidebarProvider defaultOpen>
        <Sidebar />
        {children}
      </SidebarProvider>
    </ChatProvider>
  );
}
