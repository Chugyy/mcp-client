"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { AppLayout } from "@/components/layouts/app-layout";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { Switch } from "@/components/ui/switch";
import { Palette, Settings, Key, Server } from "lucide-react";
import { ProviderCard } from "@/components/settings/provider-card";
import { ProviderConfigModal } from "@/components/settings/provider-config-modal";
import { PermissionLevelSelector } from "@/components/settings/permission-level-selector";
import { useServices, useUserProviders, useCreateUserProvider, useUpdateUserProvider, useDeleteUserProvider } from "@/services/providers/providers.hooks";
import { useCreateApiKey, useDeleteApiKey } from "@/services/api-keys/api-keys.hooks";
import { useCurrentUser, useUpdateUser, useUpdatePermissionLevel } from "@/services/users/users.hooks";
import { useMCPServers, useUpdateMCPServer, useUpdateMCPTool } from "@/services/mcp/mcp.hooks";
import type { Service, UserProvider } from "@/services/providers/providers.types";
import type { PermissionLevel } from "@/services/users/users.types";
import type { MCPServerWithTools } from "@/services/mcp/mcp.types";
import { toast } from "sonner";
import {
  VerticalTabs,
  VerticalTabsList,
  VerticalTabsTrigger,
  VerticalTabsContent,
} from "@/components/ui/vertical-tabs";

export default function SettingsPage() {
  const router = useRouter();
  const [theme, setTheme] = useState("system");
  const [language, setLanguage] = useState("fr");

  // Providers LLM state
  const [selectedService, setSelectedService] = useState<Service | null>(null);
  const [isConfigModalOpen, setIsConfigModalOpen] = useState(false);
  const [togglingProviderId, setTogglingProviderId] = useState<string | null>(null);
  const [deletingProviderId, setDeletingProviderId] = useState<string | null>(null);

  // React Query hooks
  const { data: currentUser, isLoading: userLoading } = useCurrentUser();
  const updateUser = useUpdateUser();
  const updatePermissionLevel = useUpdatePermissionLevel();
  // Récupère uniquement les services LLM (OpenAI + Anthropic)
  const { data: services = [], isLoading: servicesLoading } = useServices(['openai', 'anthropic']);
  const { data: userProviders = [], isLoading: userProvidersLoading } = useUserProviders();
  const createApiKey = useCreateApiKey();
  const createUserProvider = useCreateUserProvider();
  const updateUserProvider = useUpdateUserProvider();
  const deleteUserProvider = useDeleteUserProvider();
  const deleteApiKey = useDeleteApiKey();
  const { data: mcpServers = [], isLoading: mcpServersLoading } = useMCPServers({ with_tools: true }) as { data: MCPServerWithTools[]; isLoading: boolean };
  const updateMCPServer = useUpdateMCPServer();
  const updateMCPTool = useUpdateMCPTool();

  const handleServerToggle = async (serverId: string, enabled: boolean) => {
    await updateMCPServer.mutateAsync({
      id: serverId,
      data: { enabled },
    });
  };

  const handleToolToggle = async (serverId: string, toolId: string, enabled: boolean) => {
    await updateMCPTool.mutateAsync({
      serverId,
      toolId,
      data: { enabled },
    });
  };

  // Handlers pour les providers LLM
  const handleConfigureProvider = (service: Service) => {
    setSelectedService(service);
    setIsConfigModalOpen(true);
  };

  const handleConfirmConfig = async (apiKey: string) => {
    if (!selectedService) return;

    try {
      // 1. Créer la clé API chiffrée
      const apiKeyResponse = await createApiKey.mutateAsync({
        plain_value: apiKey,
        service_id: selectedService.id,
      });

      // 2. Créer le user_provider pour activer le service
      await createUserProvider.mutateAsync({
        service_id: selectedService.id,
        api_key_id: apiKeyResponse.id,
        enabled: true,
      });

      // 3. Optionnel: Sync les modèles en arrière-plan
      // On pourrait ajouter un appel à POST /models/sync?provider=openai ici

      toast.success(`${selectedService.name} configuré avec succès`);
    } catch (error) {
      // Les erreurs sont gérées par les hooks
      throw error;
    }
  };

  const handleToggleProvider = async (providerId: string, enabled: boolean) => {
    setTogglingProviderId(providerId);
    try {
      await updateUserProvider.mutateAsync({
        id: providerId,
        data: { enabled },
      });
    } finally {
      setTogglingProviderId(null);
    }
  };

  const handleDeleteProvider = async (providerId: string, apiKeyId: string) => {
    if (!confirm("Êtes-vous sûr de vouloir supprimer cette configuration ?")) {
      return;
    }

    setDeletingProviderId(providerId);
    try {
      // 1. Supprimer le user_provider
      await deleteUserProvider.mutateAsync(providerId);

      // 2. Supprimer la clé API associée
      if (apiKeyId) {
        await deleteApiKey.mutateAsync(apiKeyId);
      }
    } finally {
      setDeletingProviderId(null);
    }
  };

  // Helper pour trouver le userProvider correspondant à un service
  const getUserProviderForService = (serviceId: string): UserProvider | undefined => {
    return userProviders.find((up) => up.service_id === serviceId);
  };

  // Handlers pour les préférences utilisateur
  const handleThemeChange = async (newTheme: string) => {
    setTheme(newTheme);
    if (currentUser) {
      await updateUser.mutateAsync({
        preferences: {
          ...currentUser.preferences,
          theme: newTheme as 'light' | 'dark' | 'system',
        },
      });
    }
  };

  const handleLanguageChange = async (newLanguage: string) => {
    setLanguage(newLanguage);
    if (currentUser) {
      await updateUser.mutateAsync({
        preferences: {
          ...currentUser.preferences,
          language: newLanguage as 'fr' | 'en',
        },
      });
    }
  };

  const handlePermissionLevelChange = async (newLevel: PermissionLevel) => {
    await updatePermissionLevel.mutateAsync({
      permission_level: newLevel,
    });
  };

  return (
    <AppLayout>
      <div className="container mx-auto px-4 py-8 max-w-5xl">
        <div className="mb-8">
          <h1 className="text-3xl font-bold tracking-tight">Paramètres</h1>
          <p className="text-muted-foreground mt-1">
            Configurez vos préférences et vos providers
          </p>
        </div>

        <VerticalTabs defaultValue="preferences" className="gap-6 min-h-[600px]">
            <VerticalTabsList className="w-[200px]">
              {/* Section Apparence masquée */}
              {/* <VerticalTabsTrigger value="appearance">
                <Palette
                  aria-hidden="true"
                  className="-ms-0.5 me-1.5 opacity-60"
                  size={16}
                />
                Apparence
              </VerticalTabsTrigger> */}
              <VerticalTabsTrigger value="preferences">
                <Settings
                  aria-hidden="true"
                  className="-ms-0.5 me-1.5 opacity-60"
                  size={16}
                />
                Préférences
              </VerticalTabsTrigger>
              <VerticalTabsTrigger value="providers">
                <Key
                  aria-hidden="true"
                  className="-ms-0.5 me-1.5 opacity-60"
                  size={16}
                />
                Providers LLM
              </VerticalTabsTrigger>
              <VerticalTabsTrigger value="mcp">
                <Server
                  aria-hidden="true"
                  className="-ms-0.5 me-1.5 opacity-60"
                  size={16}
                />
                Serveurs MCP
              </VerticalTabsTrigger>
            </VerticalTabsList>

            {/* Section Apparence masquée */}
            {/* <VerticalTabsContent value="appearance" className="border-0 p-6 min-h-[600px]">
              <div className="space-y-6">
                <div>
                  <h2 className="text-2xl font-semibold mb-2">Apparence</h2>
                  <p className="text-sm text-muted-foreground">Personnalisez l'interface</p>
                </div>
                <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="theme">Thème</Label>
                  <Select
                    value={currentUser?.preferences?.theme || theme}
                    onValueChange={handleThemeChange}
                    disabled={userLoading}
                  >
                    <SelectTrigger id="theme">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="light">Clair</SelectItem>
                      <SelectItem value="dark">Sombre</SelectItem>
                      <SelectItem value="system">Système</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="language">Langue</Label>
                  <Select
                    value={currentUser?.preferences?.language || language}
                    onValueChange={handleLanguageChange}
                    disabled={userLoading}
                  >
                    <SelectTrigger id="language">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="fr">Français</SelectItem>
                      <SelectItem value="en">English</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>
            </VerticalTabsContent> */}
            <VerticalTabsContent value="preferences" className="border-0 p-6 min-h-[600px]">
              <div className="space-y-6">
                <div>
                  <h2 className="text-2xl font-semibold mb-2">Préférences utilisateur</h2>
                  <p className="text-sm text-muted-foreground">Configurez le comportement des outils externes</p>
                </div>
                {userLoading ? (
                  <p className="text-sm text-muted-foreground">Chargement...</p>
                ) : currentUser ? (
                  <div className="space-y-4">
                    <div>
                      <Label className="text-base">Niveau de permission pour les outils</Label>
                      <p className="text-sm text-muted-foreground mb-4">
                        Contrôlez comment les outils externes peuvent être exécutés
                      </p>
                      <PermissionLevelSelector
                        value={currentUser.permission_level}
                        onValueChange={handlePermissionLevelChange}
                        disabled={updatePermissionLevel.isPending}
                      />
                    </div>
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">Erreur de chargement des préférences</p>
                )}
              </div>
            </VerticalTabsContent>

            <VerticalTabsContent value="providers" className="border-0 p-6 min-h-[600px]">
              <div className="space-y-6">
                <div>
                  <h2 className="text-2xl font-semibold mb-2">Providers LLM</h2>
                  <p className="text-sm text-muted-foreground">Configurez vos clés API pour OpenAI, Anthropic, et autres providers</p>
                </div>
                {servicesLoading || userProvidersLoading ? (
                  <p className="text-sm text-muted-foreground">Chargement...</p>
                ) : services.length === 0 ? (
                  <p className="text-sm text-muted-foreground">Aucun service LLM disponible</p>
                ) : (
                  <div className="space-y-3">
                    {services.map((service) => {
                      const userProvider = getUserProviderForService(service.id);
                      return (
                        <ProviderCard
                          key={service.id}
                          service={service}
                          userProvider={userProvider}
                          onConfigure={handleConfigureProvider}
                          onToggle={handleToggleProvider}
                          onDelete={handleDeleteProvider}
                          isToggling={togglingProviderId === userProvider?.id}
                          isDeleting={deletingProviderId === userProvider?.id}
                        />
                      );
                    })}
                  </div>
                )}
              </div>
            </VerticalTabsContent>

            <VerticalTabsContent value="mcp" className="border-0 p-6 min-h-[600px]">
              <div className="space-y-6">
                <div>
                  <h2 className="text-2xl font-semibold mb-2">Serveurs MCP</h2>
                  <p className="text-sm text-muted-foreground">Activez ou désactivez les serveurs MCP et leurs outils</p>
                </div>
                {mcpServersLoading ? (
                  <p className="text-sm text-muted-foreground">Chargement...</p>
                ) : mcpServers.length === 0 ? (
                  <p className="text-sm text-muted-foreground">Aucun serveur MCP configuré</p>
                ) : (
                  <div className="space-y-6">
                    {mcpServers.map((server) => (
                      <div key={server.id} className="space-y-4">
                        <div className="flex items-center justify-between">
                          <div>
                            <h3 className="font-medium">{server.name}</h3>
                            <p className="text-sm text-muted-foreground">
                              {server.description}
                            </p>
                          </div>
                          <Switch
                            checked={server.enabled}
                            onCheckedChange={(checked) =>
                              handleServerToggle(server.id, checked)
                            }
                            disabled={updateMCPServer.isPending}
                          />
                        </div>
                        {server.tools && server.tools.length > 0 && (
                          <div className="pl-4 space-y-3 border-l-2">
                            {server.tools.map((tool) => (
                              <div
                                key={tool.id}
                                className="flex items-center justify-between"
                              >
                                <div>
                                  <p className="text-sm font-medium">{tool.name}</p>
                                  <p className="text-xs text-muted-foreground">
                                    {tool.description}
                                  </p>
                                </div>
                                <Switch
                                  checked={tool.enabled}
                                  onCheckedChange={(checked) =>
                                    handleToolToggle(server.id, tool.id, checked)
                                  }
                                  disabled={!server.enabled}
                                />
                              </div>
                            ))}
                          </div>
                        )}
                        {server !== mcpServers[mcpServers.length - 1] && (
                          <Separator />
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </VerticalTabsContent>
          </VerticalTabs>
      </div>

      {/* Modal de configuration des providers */}
      <ProviderConfigModal
        open={isConfigModalOpen}
        onOpenChange={setIsConfigModalOpen}
        service={selectedService}
        onConfirm={handleConfirmConfig}
      />
    </AppLayout>
  );
}
