"use client";

import dynamic from 'next/dynamic';
import { SidebarInset, useSidebar } from '@/components/ui/sidebar';
import { MessageSquare } from 'lucide-react';

// Désactiver SSR pour éviter les erreurs d'hydration avec Radix UI
const Header = dynamic(() => import('@/components/layouts/header').then(mod => ({ default: mod.Header })), { ssr: false });
const ChatInput = dynamic(() => import('@/components/chat/chat-input').then(mod => ({ default: mod.ChatInput })), { ssr: false });

function EmptyState() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center">
      <MessageSquare className="h-16 w-16 text-muted-foreground mb-4" />
      <h2 className="text-2xl font-semibold mb-2">Nouvelle conversation</h2>
      <p className="text-muted-foreground">Posez une question pour commencer</p>
    </div>
  );
}

export default function Home() {
  const { open } = useSidebar();

  return (
    <SidebarInset className="flex flex-col relative">
      <Header />
      <EmptyState />
      <div
        className="fixed bottom-6 z-50 w-full max-w-2xl px-4 transition-all duration-300"
        style={{
          left: open ? 'calc(50% + 8rem)' : '50%',
          transform: 'translateX(-50%)',
        }}
      >
        <ChatInput />
      </div>
    </SidebarInset>
  );
}
