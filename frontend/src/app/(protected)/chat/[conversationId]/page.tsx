"use client";

import { useEffect } from "react";
import dynamic from "next/dynamic";
import { useParams, useSearchParams } from "next/navigation";
import { SidebarInset, useSidebar } from '@/components/ui/sidebar';
import { useChatContext } from '@/contexts/chat-context';
import { ChatMessages } from '@/components/chat/chat-messages';

// Désactiver SSR pour éviter les erreurs d'hydration avec Radix UI
const Header = dynamic(() => import('@/components/layouts/header').then(mod => ({ default: mod.Header })), { ssr: false });
const ChatInput = dynamic(() => import('@/components/chat/chat-input').then(mod => ({ default: mod.ChatInput })), { ssr: false });

function ChatContent() {
  const { open } = useSidebar();

  return (
    <SidebarInset className="flex flex-col relative">
      <Header />
      <div className="flex flex-1 flex-col overflow-hidden pb-32">
        <ChatMessages />
      </div>
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

export default function ChatPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const conversationId = params?.conversationId as string;
  const { setActiveChatId, setInitialParams } = useChatContext();

  useEffect(() => {
    if (conversationId) {
      setActiveChatId(conversationId);

      // Lire les query params pour pré-remplissage
      const agentId = searchParams.get('agentId');
      const modelId = searchParams.get('modelId');
      const prompt = searchParams.get('prompt');

      if (agentId || modelId || prompt) {
        setInitialParams({
          agentId: agentId || undefined,
          modelId: modelId || undefined,
          prompt: prompt || undefined,
        });
      }
    }
  }, [conversationId, searchParams, setActiveChatId, setInitialParams]);

  return <ChatContent />;
}
