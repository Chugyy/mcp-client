'use client';

import { StopCircle } from 'lucide-react';

export function StoppedMessage() {
  return (
    <div className="flex items-center justify-center py-4">
      <div className="flex items-center gap-2 px-4 py-2 rounded-full border border-muted bg-muted/30 text-muted-foreground text-base">
        <StopCircle className="size-4" />
        <span>Génération arrêtée par l'utilisateur</span>
      </div>
    </div>
  );
}
