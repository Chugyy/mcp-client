"use client";

import React, { createContext, useContext, useState, useCallback, ReactNode } from "react";
import { useRouter } from "next/navigation";
import { useAgents } from "@/services/agents/agents.hooks";
import {
  useChats,
  useMessages,
  useStreamMessage,
  useCreateChat,
  useDeleteChat
} from '@/services/chats/chats.hooks';
import { useLogout } from "@/services/auth/auth.hooks";
import type { Chat, Message, Source } from '@/services/chats/chats.types';
import type { Agent } from "@/services/agents/agents.types";

interface ChatContextType {
  // Auth
  logout: () => void;

  // Agents
  agents: Agent[];
  agentsLoading: boolean;

  // Chats
  chats: Chat[];
  chatsLoading: boolean;
  refetchChats: () => void;

  // Chat actif
  activeChatId: string | null;
  activeChat: Chat | null;
  setActiveChatId: (id: string | null) => void;

  // Messages
  messages: Message[];
  messagesLoading: boolean;
  streaming: boolean;
  isSending: boolean;
  streamingMessage: string;
  sources: Source[];
  pendingValidation: string | null;
  sendMessage: (content: string, model: string, agentId: string) => Promise<void>;
  stopStream: () => Promise<void>;

  // Actions
  createNewChat: () => Promise<void>;
  createChatWithParams: (params: { agentId?: string; modelId?: string; prompt?: string }) => Promise<void>;
  deleteChat: (chatId: string) => Promise<void>;

  // Initial params (from URL)
  initialParams: { agentId?: string; modelId?: string; prompt?: string } | null;
  setInitialParams: (params: { agentId?: string; modelId?: string; prompt?: string } | null) => void;
}

const ChatContext = createContext<ChatContextType | undefined>(undefined);

export function ChatProvider({ children }: { children: ReactNode }) {
  const [activeChatId, setActiveChatId] = useState<string | null>(null);
  const [initialParams, setInitialParams] = useState<{ agentId?: string; modelId?: string; prompt?: string } | null>(null);
  const [isSending, setIsSending] = useState(false);
  const [optimisticUserMessage, setOptimisticUserMessage] = useState<Message | null>(null);
  const router = useRouter();
  const logoutMutation = useLogout();

  const logout = () => {
    // Appel API backend pour déconnexion
    logoutMutation.mutate();
  };

  // Les hooks n'ont plus besoin du token (géré par cookies)
  const { data: agents = [], isLoading: agentsLoading } = useAgents();
  const { data: chats = [], isLoading: chatsLoading, refetch: refetchChats } = useChats();
  const { data: messages = [], isLoading: messagesLoading } = useMessages(activeChatId);
  const {
    streamMessage,
    stopStream: stopStreamFromHook,
    isStreaming,
    streamingMessage,
    sources,
    pendingValidation,
  } = useStreamMessage(activeChatId);
  const createChatMutation = useCreateChat();
  const deleteChatMutation = useDeleteChat();

  // Calculer le chat actif depuis la liste
  const activeChat = activeChatId ? chats.find(c => c.id === activeChatId) || null : null;

  // Fusionner messages réels avec message optimiste
  // Filtrer le message optimiste si un message réel avec le même contenu existe déjà
  const allMessages = optimisticUserMessage
    ? (() => {
        const realMessageExists = messages.some(
          m => m.role === 'user' && m.content === optimisticUserMessage.content
        );
        return realMessageExists ? messages : [...messages, optimisticUserMessage];
      })()
    : messages;

  const sendMessage = useCallback(async (
    content: string,
    model: string,
    agentId: string
  ) => {
    setIsSending(true); // Activer immédiatement pour feedback instantané

    // Créer message user optimiste pour feedback instantané
    const tempMessage: Message = {
      id: `temp_${Date.now()}`,
      chat_id: activeChatId!,
      role: 'user',
      content,
      created_at: new Date().toISOString(),
    };
    setOptimisticUserMessage(tempMessage);

    try {
      // Le chat existe toujours à ce stade (créé au clic sur "+")
      if (!activeChatId) {
        console.error('No active chat - this should not happen');
        return;
      }

      // Stream dans le chat actif avec l'agent ID
      await streamMessage(content, model, agentId);
    } catch (error) {
      // Re-throw pour que l'appelant puisse gérer (notamment le 409)
      throw error;
    } finally {
      setIsSending(false); // Désactiver dans tous les cas
      setOptimisticUserMessage(null); // Retirer le message optimiste
    }
  }, [activeChatId, streamMessage]);

  const createNewChat = useCallback(async () => {
    try {
      // Créer le chat sans agent - l'agent sera assigné au premier message
      const newChat = await createChatMutation.mutateAsync({
        title: "Nouvelle conversation"
        // No agent_id or team_id
      });

      setActiveChatId(newChat.id);
      router.push(`/chat/${newChat.id}`);
    } catch (error) {
      console.error('Error creating chat:', error);
    }
  }, [createChatMutation, router]);

  const createChatWithParams = useCallback(async (params: { agentId?: string; modelId?: string; prompt?: string }) => {
    try {
      // Créer le chat
      const newChat = await createChatMutation.mutateAsync({
        title: "Nouvelle conversation"
      });

      // Construire les query params
      const searchParams = new URLSearchParams();
      if (params.agentId) searchParams.set('agentId', params.agentId);
      if (params.modelId) searchParams.set('modelId', params.modelId);
      if (params.prompt) searchParams.set('prompt', params.prompt);

      setActiveChatId(newChat.id);
      router.push(`/chat/${newChat.id}?${searchParams.toString()}`);
    } catch (error) {
      console.error('Error creating chat with params:', error);
    }
  }, [createChatMutation, router]);

  const deleteChat = useCallback(async (chatId: string) => {
    try {
      await deleteChatMutation.mutateAsync(chatId);
      if (activeChatId === chatId) {
        setActiveChatId(null);
        router.push('/');
      }
      // Plus besoin de refetchChats() : le hook useMutation invalide automatiquement le cache
    } catch (error) {
      console.error('Error deleting chat:', error);
    }
  }, [activeChatId, deleteChatMutation, router]);

  // Wrapper pour stopStream qui nettoie aussi les états locaux
  const stopStream = useCallback(async () => {
    setIsSending(false); // Désactiver isSending immédiatement
    setOptimisticUserMessage(null); // Nettoyer le message optimiste
    await stopStreamFromHook(); // Appeler le vrai stopStream du hook
  }, [stopStreamFromHook]);

  return (
    <ChatContext.Provider
      value={{
        logout,
        agents,
        agentsLoading,
        chats,
        chatsLoading,
        refetchChats,
        activeChatId,
        activeChat,
        setActiveChatId,
        messages: allMessages,
        messagesLoading,
        streaming: isStreaming,
        isSending,
        streamingMessage,
        sources,
        pendingValidation,
        sendMessage,
        stopStream,
        createNewChat,
        createChatWithParams,
        deleteChat,
        initialParams,
        setInitialParams,
      }}
    >
      {children}
    </ChatContext.Provider>
  );
}

export function useChatContext() {
  const context = useContext(ChatContext);
  if (!context) {
    throw new Error("useChatContext must be used within ChatProvider");
  }
  return context;
}
