"use client"

import { Button } from "@/components/ui/button"
import { Switch } from "@/components/ui/switch"
import { Badge } from "@/components/ui/badge"
import { Trash2, RefreshCw } from "lucide-react"
import type { Service, UserProvider } from "@/services/providers/providers.types"

interface ProviderCardProps {
  service: Service
  userProvider?: UserProvider
  onConfigure: (service: Service) => void
  onToggle: (providerId: string, enabled: boolean) => void
  onDelete: (providerId: string, apiKeyId: string) => void
  onRotateKey?: (service: Service) => void
  isToggling?: boolean
  isDeleting?: boolean
}

export function ProviderCard({
  service,
  userProvider,
  onConfigure,
  onToggle,
  onDelete,
  onRotateKey,
  isToggling = false,
  isDeleting = false,
}: ProviderCardProps) {
  const isConfigured = !!userProvider
  const isEnabled = userProvider?.enabled ?? false

  return (
    <div className="flex items-center justify-between p-4 border rounded-lg">
      <div className="flex-1">
        <div className="flex items-center gap-2 mb-1">
          <h3 className="font-medium">{service.name}</h3>
          {isConfigured ? (
            <Badge variant="outline" className="text-xs">
              Configuré
            </Badge>
          ) : (
            <Badge variant="secondary" className="text-xs">
              Non configuré
            </Badge>
          )}
        </div>
        {service.description && (
          <p className="text-sm text-muted-foreground">{service.description}</p>
        )}
        {isConfigured && userProvider?.api_key_id && (
          <p className="text-xs text-muted-foreground mt-1">
            Clé API: ••••••••
          </p>
        )}
      </div>

      <div className="flex items-center gap-2">
        {isConfigured && userProvider ? (
          <>
            {onRotateKey && (
              <Button
                variant="ghost"
                size="icon"
                onClick={() => onRotateKey(service)}
                disabled={isDeleting}
                title="Changer la clé API"
              >
                <RefreshCw className="h-4 w-4" />
              </Button>
            )}
            <Button
              variant="ghost"
              size="icon"
              onClick={() => onDelete(userProvider.id, userProvider.api_key_id!)}
              disabled={isDeleting}
              title="Supprimer la configuration"
            >
              <Trash2 className="h-4 w-4" />
            </Button>
            <Switch
              checked={isEnabled}
              onCheckedChange={(checked) => onToggle(userProvider.id, checked)}
              disabled={isToggling || isDeleting}
            />
          </>
        ) : (
          <Button onClick={() => onConfigure(service)} variant="outline" size="sm">
            + Configurer
          </Button>
        )}
      </div>
    </div>
  )
}
