"use client";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert-dialog";
import { AlertTriangle, Trash2 } from "lucide-react";

export interface CascadeImpact {
  agents_to_delete?: Array<{ id: string; name: string }>;
  agents_to_update?: Array<{ id: string; name: string }>;
  chats_to_delete?: number;
  configurations_to_delete?: number;
  agent_id?: string;
  agent_name?: string;
}

interface CascadeConfirmDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  entityType: "agent" | "server" | "resource";
  entityName: string;
  impact: CascadeImpact | null;
  onConfirm: () => void;
  loading?: boolean;
}

export function CascadeConfirmDialog({
  open,
  onOpenChange,
  entityType,
  entityName,
  impact,
  onConfirm,
  loading = false,
}: CascadeConfirmDialogProps) {
  if (!impact) return null;

  const entityTypeLabel = {
    agent: "l'agent",
    server: "le serveur MCP",
    resource: "la ressource",
  }[entityType];

  // Pour les agents, l'impact est juste le nombre de chats
  const isAgentDeletion = entityType === "agent";
  const agentsToDelete = impact.agents_to_delete || [];
  const agentsToUpdate = impact.agents_to_update || [];
  const chatsToDelete = impact.chats_to_delete || 0;
  const configurationsToDelete = impact.configurations_to_delete || 0;

  const hasImpact = isAgentDeletion
    ? chatsToDelete > 0
    : agentsToDelete.length > 0 ||
      agentsToUpdate.length > 0 ||
      chatsToDelete > 0;

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent className="max-w-lg">
        <AlertDialogHeader>
          <AlertDialogTitle className="flex items-center gap-2">
            <Trash2 className="size-5 text-destructive" />
            Confirmer la suppression
          </AlertDialogTitle>
          <AlertDialogDescription className="text-base">
            Vous êtes sur le point de supprimer {entityTypeLabel}{" "}
            <strong>{entityName}</strong>.
          </AlertDialogDescription>
        </AlertDialogHeader>

        {hasImpact && (
          <div className="space-y-3">
            <div className="rounded-md border border-destructive/50 bg-destructive/10 p-3">
              <div className="flex items-start gap-2">
                <AlertTriangle className="size-4 text-destructive mt-0.5 flex-shrink-0" />
                <p className="text-sm text-destructive font-medium">
                  Cette suppression aura les impacts suivants :
                </p>
              </div>
            </div>

            <div className="space-y-2 text-sm">
              {/* Pour agents : afficher seulement les chats */}
              {isAgentDeletion && chatsToDelete > 0 && (
                <div className="flex items-center justify-between p-3 rounded-md bg-destructive/10 border border-destructive/20">
                  <span className="font-medium">
                    Conversation{chatsToDelete > 1 ? "s" : ""} supprimée
                    {chatsToDelete > 1 ? "s" : ""}
                  </span>
                  <Badge
                    variant="destructive"
                    className="font-bold"
                  >
                    {chatsToDelete}
                  </Badge>
                </div>
              )}

              {/* Pour servers/resources : afficher tout */}
              {!isAgentDeletion && (
                <>
                  {agentsToDelete.length > 0 && (
                    <div className="flex items-center justify-between p-3 rounded-md bg-destructive/10 border border-destructive/20">
                      <div className="flex flex-col gap-1">
                        <span className="font-medium">
                          Agent{agentsToDelete.length > 1 ? "s" : ""}{" "}
                          supprimé{agentsToDelete.length > 1 ? "s" : ""}
                        </span>
                        <span className="text-xs text-muted-foreground">
                          Car {agentsToDelete.length > 1 ? "ils" : "il"} n'
                          {agentsToDelete.length > 1 ? "ont" : "a"} plus aucune
                          configuration
                        </span>
                      </div>
                      <Badge variant="destructive" className="font-bold">
                        {agentsToDelete.length}
                      </Badge>
                    </div>
                  )}

                  {chatsToDelete > 0 && (
                    <div className="flex items-center justify-between p-3 rounded-md bg-destructive/10 border border-destructive/20">
                      <span className="font-medium">
                        Conversation{chatsToDelete > 1 ? "s" : ""} supprimée
                        {chatsToDelete > 1 ? "s" : ""}
                      </span>
                      <Badge variant="destructive" className="font-bold">
                        {chatsToDelete}
                      </Badge>
                    </div>
                  )}

                  {agentsToUpdate.length > 0 && (
                    <div className="flex items-center justify-between p-3 rounded-md bg-orange-500/10 border border-orange-500/20">
                      <div className="flex flex-col gap-1">
                        <span className="font-medium text-orange-700">
                          Agent{agentsToUpdate.length > 1 ? "s" : ""} mis à
                          jour
                        </span>
                        <span className="text-xs text-muted-foreground">
                          Configuration retirée
                        </span>
                      </div>
                      <Badge
                        variant="outline"
                        className="bg-orange-500/20 text-orange-700 border-orange-500/30 font-bold"
                      >
                        {agentsToUpdate.length}
                      </Badge>
                    </div>
                  )}

                  {configurationsToDelete > 0 && (
                    <div className="flex items-center justify-between p-3 rounded-md bg-muted border">
                      <span className="font-medium text-muted-foreground">
                        Configuration{configurationsToDelete > 1 ? "s" : ""}{" "}
                        supprimée{configurationsToDelete > 1 ? "s" : ""}
                      </span>
                      <Badge variant="outline" className="font-bold">
                        {configurationsToDelete}
                      </Badge>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        )}

        {!hasImpact && (
          <div className="rounded-md border bg-muted p-3">
            <p className="text-sm text-muted-foreground">
              Aucune dépendance détectée. La suppression sera sans impact sur
              d'autres entités.
            </p>
          </div>
        )}

        <AlertDialogFooter>
          <AlertDialogCancel disabled={loading}>Annuler</AlertDialogCancel>
          <AlertDialogAction
            onClick={onConfirm}
            disabled={loading}
            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
          >
            {loading ? (
              <span className="flex items-center gap-2">
                <span className="size-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Suppression...
              </span>
            ) : (
              "Supprimer définitivement"
            )}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
