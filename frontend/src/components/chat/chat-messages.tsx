'use client';

import { useEffect, useState } from 'react';
import {
  Conversation,
  ConversationContent,
  ConversationScrollButton,
} from '@/components/ui/shadcn-io/ai/conversation';
import {
  Message,
  MessageAvatar,
  MessageContent,
} from '@/components/ui/shadcn-io/ai/message';
import { useChatContext } from '@/contexts/chat-context';
import { ToolCallCard } from './tool-call-card';
import { StoppedMessage } from './stopped-message';
import { validationService } from '@/services/validations/validations.service';
import ReactMarkdown from 'react-markdown';
import { toast } from 'sonner';
import { useQueryClient } from '@tanstack/react-query';
import { chatKeys } from '@/services/chats/chats.hooks';
// getAvatarUrl removed - using uploadId directly with MessageAvatar
import { ThreeDots } from 'react-loader-spinner';
import type { Message as ChatMessage } from '@/services/chats/chats.types';
import { Button } from '@/components/ui/button';
import { Copy, Check } from 'lucide-react';

// Helper pour détecter si un message est un message "stopped"
function isStoppedMessage(message: ChatMessage): boolean {
  const content = message.content || '';
  // Détecter par contenu (regex) ou par métadata
  return (
    /action refusée|génération arrêtée|stopped/i.test(content) ||
    message.metadata?.stopped === true
  );
}

export function ChatMessages() {
  const {
    messages,
    messagesLoading,
    streaming,
    isSending,
    streamingMessage,
    sources,
    pendingValidation,
    activeChatId,
    activeChat,
    agents
  } = useChatContext();
  const queryClient = useQueryClient();

  // Récupérer l'agent du chat actif pour afficher son avatar
  const currentAgent = agents.find(a => a.id === activeChat?.agent_id);

  // État pour gérer les copies
  const [copiedMessageId, setCopiedMessageId] = useState<string | null>(null);

  // Handler pour copier le contenu
  const handleCopyMessage = async (messageId: string, content: string) => {
    try {
      await navigator.clipboard.writeText(content);
      setCopiedMessageId(messageId);
      toast.success('Message copié !');

      // Reset après 2 secondes
      setTimeout(() => {
        setCopiedMessageId(null);
      }, 2000);
    } catch (error) {
      toast.error('Erreur lors de la copie');
      console.error('Copy error:', error);
    }
  };

  // Handlers pour les actions de validation
  const handleApprove = async (validationId: string, alwaysAllow: boolean) => {
    try {
      await validationService.approve(validationId, { always_allow: alwaysAllow })
      toast.success(alwaysAllow ? 'Outil approuvé définitivement' : 'Outil approuvé une fois')
      // Invalider pour voir le message "executing" puis "completed"
      if (activeChatId) {
        queryClient.invalidateQueries({
          queryKey: chatKeys.messages(activeChatId),
        });
      }
    } catch (error: any) {
      // Gérer l'erreur 404 (validation déjà annulée)
      if (error.response?.status === 404 || error.message?.includes('already')) {
        toast.error('Cette validation n\'existe plus (génération arrêtée)')
        // Forcer un refetch pour mettre à jour l'affichage
        queryClient.invalidateQueries({ queryKey: chatKeys.messages(activeChatId!) })
      } else {
        toast.error('Erreur lors de l\'approbation')
        console.error('Approve error:', error)
      }
    }
  }

  const handleReject = async (validationId: string, reason?: string) => {
    try {
      await validationService.reject(validationId, { reason })
      toast.success('Outil rejeté')
      // Invalider pour voir le message "rejected"
      if (activeChatId) {
        queryClient.invalidateQueries({
          queryKey: chatKeys.messages(activeChatId),
        });
      }
    } catch (error: any) {
      // Gérer l'erreur 404 (validation déjà annulée)
      if (error.response?.status === 404 || error.message?.includes('already')) {
        toast.error('Cette validation n\'existe plus (génération arrêtée)')
        queryClient.invalidateQueries({ queryKey: chatKeys.messages(activeChatId!) })
      } else {
        toast.error('Erreur lors du rejet')
        console.error('Reject error:', error)
      }
    }
  }

  const handleFeedback = async (validationId: string, feedback: string) => {
    try {
      await validationService.feedback(validationId, { feedback })
      toast.success('Feedback envoyé')
      // Invalider pour voir le message "feedback_received"
      if (activeChatId) {
        queryClient.invalidateQueries({
          queryKey: chatKeys.messages(activeChatId),
        });
      }
    } catch (error: any) {
      // Gérer l'erreur 404 (validation déjà annulée)
      if (error.response?.status === 404 || error.message?.includes('already')) {
        toast.error('Cette validation n\'existe plus (génération arrêtée)')
        queryClient.invalidateQueries({ queryKey: chatKeys.messages(activeChatId!) })
      } else {
        toast.error('Erreur lors de l\'envoi du feedback')
        console.error('Feedback error:', error)
      }
    }
  }

  if (messagesLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-muted-foreground">Loading messages...</p>
      </div>
    );
  }

  if (messages.length === 0) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-muted-foreground">No messages yet. Start a conversation!</p>
      </div>
    );
  }

  // Plus besoin de grouper : les messages sont déjà dans le bon ordre en DB
  // Transformer simplement les messages en format displayMessages
  const displayMessages = messages.map((msg, index) => ({
    type: msg.role === 'tool_call' ? ('tool_call' as const) : ('regular' as const),
    data: msg.role === 'tool_call'
      ? {
          validationId: msg.metadata?.validation_id,
          message: msg
        }
      : msg,
    key: `${msg.role}-${msg.id}-${index}`
  }));

  return (
    <Conversation className="flex-1">
      <ConversationContent>
        {displayMessages.map((item) => (
          <div key={item.key}>
            {/* Messages utilisateur et assistant */}
            {item.type === 'regular' && (item.data.role === 'user' || item.data.role === 'assistant') && (
              <>
                {/* Si le message est un message "stopped", afficher le composant StoppedMessage */}
                {isStoppedMessage(item.data) ? (
                  <StoppedMessage />
                ) : (
                  <Message from={item.data.role}>
                {item.data.role !== 'user' && currentAgent && (
                  <MessageAvatar
                    name={currentAgent.name}
                    uploadId={currentAgent.avatar_url}
                    fallback="/bot.png"
                  />
                )}
                <MessageContent>
                  {item.data.role === 'assistant' ? (
                    <>
                      <ReactMarkdown
                        components={{
                          // Texte plus grand pour markdown
                          p: ({ children }) => <p className="mb-2 last:mb-0 text-base">{children}</p>,
                          ul: ({ children }) => <ul className="mb-2 ml-4 list-disc text-base">{children}</ul>,
                          ol: ({ children }) => <ol className="mb-2 ml-4 list-decimal text-base">{children}</ol>,
                          li: ({ children }) => <li className="mb-1 text-base">{children}</li>,
                          code: ({ className, children }) =>
                            !className ? (
                              <code className="rounded bg-muted px-1 py-0.5 font-mono text-sm">{children}</code>
                            ) : (
                              <code className="block rounded bg-muted p-2 font-mono text-sm overflow-x-auto">{children}</code>
                            ),
                          pre: ({ children }) => <pre className="mb-2">{children}</pre>,
                          h1: ({ children }) => <h1 className="mb-2 text-2xl font-bold">{children}</h1>,
                          h2: ({ children }) => <h2 className="mb-2 text-xl font-bold">{children}</h2>,
                          h3: ({ children }) => <h3 className="mb-2 text-lg font-bold">{children}</h3>,
                          blockquote: ({ children }) => (
                            <blockquote className="mb-2 border-l-4 border-muted pl-4 italic text-base">{children}</blockquote>
                          ),
                        }}
                      >
                        {item.data.content}
                      </ReactMarkdown>

                      {/* Affichage des sources si disponibles */}
                      {item.data.metadata?.sources && item.data.metadata.sources.length > 0 && (
                        <div className="mt-3 pt-3 border-t border-muted">
                          <details className="text-xs text-muted-foreground" open>
                            <summary className="cursor-pointer hover:text-foreground font-semibold">
                              📚 Sources ({item.data.metadata.sources.length})
                            </summary>
                            <ul className="mt-2 space-y-2 ml-4">
                              {item.data.metadata.sources.map((source: any, i: number) => (
                                <li key={i} className="text-xs border-l-2 border-primary/30 pl-2">
                                  <div className="font-semibold text-foreground">{source.resource_name || 'Source inconnue'}</div>
                                  {source.similarity !== undefined && (
                                    <div className="text-muted-foreground">
                                      Similarité: {(source.similarity * 100).toFixed(1)}%
                                    </div>
                                  )}
                                  {source.content && (
                                    <div className="mt-1 text-muted-foreground italic line-clamp-2">
                                      "{source.content}"
                                    </div>
                                  )}
                                </li>
                              ))}
                            </ul>
                          </details>
                        </div>
                      )}

                      {/* Bouton Copier - uniquement si le message contient du texte */}
                      {item.data.content && item.data.content.trim().length > 0 && (
                        <div className="mt-4 flex justify-start">
                          <Button
                            size="icon"
                            variant="ghost"
                            onClick={() => handleCopyMessage(item.data.id, item.data.content)}
                            className="h-7 w-7"
                          >
                            {copiedMessageId === item.data.id ? (
                              <Check className="size-4" />
                            ) : (
                              <Copy className="size-4" />
                            )}
                          </Button>
                        </div>
                      )}
                    </>
                  ) : (
                    item.data.content
                  )}
                </MessageContent>
              </Message>
                )}
              </>
            )}

            {/* Messages tool_call - Afficher UN SEUL ToolCallCard par validation_id */}
            {item.type === 'tool_call' && item.data.message.metadata && (
              <ToolCallCard
                toolName={item.data.message.metadata.tool_name || 'Unknown tool'}
                step={item.data.message.metadata.step || 'validation_requested'}
                arguments={item.data.message.metadata.arguments || {}}
                result={item.data.message.metadata.result}
                validationId={item.data.validationId}
                status={item.data.message.metadata.status}
                onApprove={handleApprove}
                onReject={handleReject}
                onFeedback={handleFeedback}
              />
            )}
          </div>
        ))}

        {/* Message en cours de streaming */}
        {streaming && (
          <>
            {streamingMessage && (
              <Message from="assistant">
                <MessageAvatar
                  name={currentAgent?.name || "AI"}
                  uploadId={currentAgent?.avatar_url}
                  fallback="/bot.png"
                />
                <MessageContent>
                  <ReactMarkdown
                    components={{
                      p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                      ul: ({ children }) => <ul className="mb-2 ml-4 list-disc">{children}</ul>,
                      ol: ({ children }) => <ol className="mb-2 ml-4 list-decimal">{children}</ol>,
                      li: ({ children }) => <li className="mb-1">{children}</li>,
                      code: ({ className, children }) =>
                        !className ? (
                          <code className="rounded bg-muted px-1 py-0.5 font-mono text-sm">{children}</code>
                        ) : (
                          <code className="block rounded bg-muted p-2 font-mono text-sm overflow-x-auto">{children}</code>
                        ),
                    }}
                  >
                    {streamingMessage}
                  </ReactMarkdown>

                  {/* Sources en cours */}
                  {sources.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-muted">
                      <details className="text-xs text-muted-foreground" open>
                        <summary className="cursor-pointer hover:text-foreground font-semibold">
                          Sources ({sources.length})
                        </summary>
                        <ul className="mt-2 space-y-2 ml-4">
                          {sources.map((source: any, i: number) => (
                            <li key={i} className="text-xs border-l-2 border-primary/30 pl-2">
                              <div className="font-semibold text-foreground">{source.resource_name || 'Source inconnue'}</div>
                              {source.similarity !== undefined && (
                                <div className="text-muted-foreground">
                                  Similarité: {(source.similarity * 100).toFixed(1)}%
                                </div>
                              )}
                              {source.content && (
                                <div className="text-muted-foreground mt-1 text-[11px] line-clamp-2">
                                  {source.content}
                                </div>
                              )}
                            </li>
                          ))}
                        </ul>
                      </details>
                    </div>
                  )}
                </MessageContent>
              </Message>
            )}

            {/* Spinner visible UNIQUEMENT si pas de chunk ET pas de validation en attente */}
            {!streamingMessage && !pendingValidation && (
              <div className="flex justify-start ml-12 mb-2">
                <ThreeDots
                  height="40"
                  width="40"
                  radius="9"
                  color="hsl(var(--primary))"
                  ariaLabel="three-dots-loading"
                  visible={true}
                />
              </div>
            )}
          </>
        )}

        {/* Spinner si isSending (feedback immédiat avant le streaming) */}
        {isSending && !streaming && (
          <div className="flex justify-start ml-12 mb-2">
            <ThreeDots
              height="40"
              width="40"
              radius="9"
              color="hsl(var(--primary))"
              ariaLabel="three-dots-loading"
              visible={true}
            />
          </div>
        )}
      </ConversationContent>
      <ConversationScrollButton />
    </Conversation>
  );
}
