'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import {
  PromptInput,
  PromptInputAction,
  PromptInputActions,
  PromptInputTextarea,
} from '@/components/ui/prompt-input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { ConfirmDialog } from '@/components/ui/confirm-dialog';
import { useChatContext } from '@/contexts/chat-context';
import { useModels } from '@/services/models/models.hooks';
import type { ModelWithService } from '@/services/models/models.types';
import { getAvatarUrl } from '@/lib/api';
import { Bot, Send, Sparkles, Shield, Square } from 'lucide-react';
import { toast } from 'sonner';

/**
 * Helper pour obtenir l'URL du logo du provider
 */
function getProviderLogoUrl(model: ModelWithService): string | undefined {
  if (!model.logo_url) return undefined;

  // Si c'est déjà une URL complète, la retourner telle quelle
  if (model.logo_url.startsWith('http://') || model.logo_url.startsWith('https://')) {
    return model.logo_url;
  }

  // Nettoyer le chemin (retirer le ./ du début si présent)
  let cleanPath = model.logo_url;
  if (cleanPath.startsWith('./')) {
    cleanPath = cleanPath.substring(1); // Retire le point, garde le /
  }
  if (!cleanPath.startsWith('/')) {
    cleanPath = '/' + cleanPath; // Ajoute le / si absent
  }

  // Construire l'URL complète avec l'API backend
  const API_BASE = process.env.NEXT_PUBLIC_API_URL?.replace('/api/v1', '') || 'http://localhost:8000';
  return `${API_BASE}${cleanPath}`;
}

export function ChatInput() {
  const [input, setInput] = useState('');
  const [selectedAgent, setSelectedAgent] = useState<string>('');
  const [selectedModel, setSelectedModel] = useState<string>('');
  const [conflictDialog, setConflictDialog] = useState<{
    open: boolean;
    pendingMessage: string;
    pendingModel: string;
    pendingAgent: string;
  }>({
    open: false,
    pendingMessage: '',
    pendingModel: '',
    pendingAgent: ''
  });

  const {
    agents,
    sendMessage,
    stopStream,
    streaming,
    activeChatId,
    activeChat,
    messages,
    initialParams,
    setInitialParams,
  } = useChatContext();

  // Récupérer les modèles depuis l'API (avec logo provider)
  const { data: models = [] } = useModels() as { data: ModelWithService[] };

  // Synchroniser les sélecteurs avec le chat actif
  useEffect(() => {
    // Déterminer le modèle par défaut (premier modèle disponible)
    const defaultModel = models.length > 0 ? models[0].model_name : '';

    if (activeChat) {
      if (activeChat.agent_id && activeChat.model) {
        // Chat initialisé → charger l'agent et le modèle du chat
        setSelectedAgent(activeChat.agent_id);
        setSelectedModel(activeChat.model);
      } else {
        // Chat vide → vérifier les params initiaux ou réinitialiser
        if (initialParams) {
          // Pré-remplir avec les params de l'URL
          if (initialParams.agentId) setSelectedAgent(initialParams.agentId);
          else setSelectedAgent(agents.length > 0 ? agents[0].id : '');

          if (initialParams.modelId) setSelectedModel(initialParams.modelId);
          else setSelectedModel(defaultModel);

          if (initialParams.prompt) setInput(initialParams.prompt);

          // Nettoyer les params après utilisation
          setInitialParams(null);
        } else {
          // Pas de params → valeurs par défaut
          const defaultAgent = agents.length > 0 ? agents[0].id : '';
          setSelectedAgent(defaultAgent);
          setSelectedModel(defaultModel);
        }
      }
    } else {
      // Pas de chat actif → réinitialiser
      const defaultAgent = agents.length > 0 ? agents[0].id : '';
      setSelectedAgent(defaultAgent);
      setSelectedModel(defaultModel);
    }
  }, [activeChat, agents, activeChatId, models, initialParams, setInitialParams]);

  const handleSubmit = async () => {
    if (!input.trim() || !selectedAgent || streaming) return;

    const messageToSend = input.trim(); // Sauvegarder le message
    setInput(''); // Vider immédiatement l'input

    try {
      await sendMessage(messageToSend, selectedModel, selectedAgent);
    } catch (error: any) {
      // Si 409 Conflict → ouvrir modale de confirmation
      const isConflict = error.response?.status === 409 || error.message?.includes('409')
      if (isConflict) {
        // En cas de conflit, restaurer le message dans l'input
        setInput(messageToSend);
        setConflictDialog({
          open: true,
          pendingMessage: messageToSend,
          pendingModel: selectedModel,
          pendingAgent: selectedAgent
        });
      } else {
        // Autres erreurs → afficher dans console
        console.error('Error sending message:', error);
      }
    }
  };

  const handleStop = async () => {
    await stopStream();
  };

  const handleCancelAndRetry = async () => {
    if (!conflictDialog.pendingMessage) return;

    try {
      // 1. Forcer l'arrêt du stream (réussit toujours, force is_generating = false)
      await stopStream();

      // 2. Attendre un peu pour la transition
      await new Promise(resolve => setTimeout(resolve, 500));

      // 3. Retry avec le message en attente
      await sendMessage(
        conflictDialog.pendingMessage,
        conflictDialog.pendingModel,
        conflictDialog.pendingAgent
      );

      // 4. Nettoyer
      setInput('');
      setConflictDialog({ open: false, pendingMessage: '', pendingModel: '', pendingAgent: '' });
    } catch (error: any) {
      console.error('Error during cancel and retry:', error);

      // Si encore un 409, afficher un message plus explicite
      const isStillConflict = error.response?.status === 409 || error.message?.includes('409');
      if (isStillConflict) {
        toast.error('La génération précédente n\'est pas encore terminée. Veuillez patienter quelques secondes.');
      } else {
        toast.error('Échec de l\'annulation et du retry');
      }

      setConflictDialog({ open: false, pendingMessage: '', pendingModel: '', pendingAgent: '' });
    }
  };

  const handleWaitConflict = () => {
    // Juste fermer la modale, garder le message dans l'input
    setConflictDialog({ open: false, pendingMessage: '', pendingModel: '', pendingAgent: '' });
  };

  // Trouver les données de l'agent et du modèle sélectionnés
  const selectedAgentData = agents.find(a => a.id === selectedAgent);
  const selectedModelData = models.find(m => m.model_name === selectedModel);

  // Bloquer le changement d'agent si le chat est déjà initialisé avec un agent
  const isAgentLocked = !!(activeChat?.agent_id && messages.length > 0);

  return (
    <PromptInput
      value={input}
      onValueChange={setInput}
      onSubmit={handleSubmit}
      className="w-full bg-background/95 backdrop-blur-sm shadow-lg"
    >
      <div className="flex flex-col gap-2">
        <PromptInputTextarea
          placeholder="Type your message..."
          className="min-h-[40px] w-full bg-transparent"
          disabled={streaming}
        />

        <div className="flex items-center justify-between">
          <PromptInputActions className="gap-2">
            <Select
              value={selectedAgent || ''}
              onValueChange={setSelectedAgent}
              disabled={isAgentLocked}
            >
              <SelectTrigger
                className="h-7 w-auto gap-1.5 rounded-full border-0 bg-transparent px-2.5 text-xs transition-colors hover:bg-blue-500/10 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <SelectValue placeholder="Select agent" />
              </SelectTrigger>
              <SelectContent className="bg-background rounded-2xl max-w-[280px] max-h-[300px] overflow-y-auto">
                {agents.map((a) => (
                  <SelectItem key={a.id} value={a.id}>
                    <div className="flex items-center gap-2 max-w-[240px]">
                      {a.avatar_url ? (
                        <img
                          src={getAvatarUrl(a.avatar_url)}
                          alt={a.name}
                          className="size-4 rounded-full object-cover flex-shrink-0"
                        />
                      ) : (
                        <Bot className="size-4 flex-shrink-0" />
                      )}
                      <span className="truncate">{a.name}</span>
                      {a.is_system && (
                        <Badge
                          variant="secondary"
                          className="text-[10px] px-1 py-0 h-4 flex-shrink-0 bg-blue-500/10 text-blue-700 border-blue-500/20"
                        >
                          <Shield className="size-2.5 mr-0.5" />
                          System
                        </Badge>
                      )}
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={selectedModel} onValueChange={setSelectedModel}>
              <SelectTrigger className="h-7 w-auto gap-1.5 rounded-full border-0 bg-transparent px-2.5 text-xs transition-colors hover:bg-blue-500/10">
                <SelectValue placeholder="Select model" />
              </SelectTrigger>
              <SelectContent className="bg-background rounded-2xl max-w-[280px] max-h-[300px] overflow-y-auto">
                {models.map((m) => {
                  const logoUrl = getProviderLogoUrl(m);
                  return (
                    <SelectItem key={m.id} value={m.model_name}>
                      <div className="flex items-center gap-2 max-w-[240px]">
                        {logoUrl ? (
                          <img
                            src={logoUrl}
                            alt={m.provider}
                            className="size-4 rounded object-cover flex-shrink-0"
                          />
                        ) : (
                          <Sparkles className="size-4 flex-shrink-0" />
                        )}
                        <span className="truncate">{m.display_name || m.model_name}</span>
                      </div>
                    </SelectItem>
                  );
                })}
              </SelectContent>
            </Select>
          </PromptInputActions>

          <PromptInputAction tooltip={streaming ? "Stop generation" : "Send message"}>
            <Button
              size="icon"
              onClick={streaming ? handleStop : handleSubmit}
              disabled={streaming ? false : (!input.trim() || !selectedAgent)}
              className={`size-7 rounded-md ${
                streaming
                  ? 'bg-red-500 hover:bg-red-600 text-white'
                  : 'bg-transparent hover:bg-transparent text-blue-500 hover:text-blue-600 disabled:text-gray-400'
              }`}
            >
              {streaming ? (
                <Square className="size-4 fill-current" />
              ) : (
                <Send className="size-4" />
              )}
            </Button>
          </PromptInputAction>
        </div>
      </div>

      {/* Modale de conflit de génération */}
      <ConfirmDialog
        open={conflictDialog.open}
        onOpenChange={(open) => {
          if (!open) handleWaitConflict();
        }}
        title="Génération en cours"
        description="Une génération est déjà en cours pour ce chat. Voulez-vous annuler la génération actuelle et relancer avec votre nouveau message ?"
        confirmLabel="Annuler et relancer"
        cancelLabel="Attendre"
        onConfirm={handleCancelAndRetry}
        variant="destructive"
      />
    </PromptInput>
  );
}
