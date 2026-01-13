'use client';

import { AppLayout } from '@/components/layouts/app-layout';
import { ValidationCard } from '@/components/validation/validation-card';
import { ArchivesSidebar } from '@/components/validation/archives-sidebar';
import { ValidationArchiveSheet } from '@/components/validation/validation-archive-sheet';
import { FeedbackDialog } from '@/components/validation/feedback-dialog';
import { ConfirmDialog } from '@/components/ui/confirm-dialog';
import { Button } from '@/components/ui/button';
import { Archive } from 'lucide-react';
import { useState } from 'react';
import {
  useValidations,
  useApproveValidation,
  useRejectValidation,
  useFeedbackValidation
} from '@/services/validations/validations.hooks';
import type { Validation } from '@/services/validations/validations.types';

export default function ValidationPage() {
  // Utiliser les hooks React Query
  const { data: items = [], isLoading } = useValidations('pending');
  const { data: archivedItems = [] } = useValidations('approved,rejected');

  // Hooks mutations
  const approveValidation = useApproveValidation();
  const rejectValidation = useRejectValidation();
  const feedbackValidation = useFeedbackValidation();

  const [isArchivesOpen, setIsArchivesOpen] = useState(false);
  const [archiveSheetOpen, setArchiveSheetOpen] = useState(false);
  const [selectedValidationId, setSelectedValidationId] = useState<string | null>(null);

  // Modales states
  const [validateDialog, setValidateDialog] = useState<{ open: boolean; item: Validation | null }>({ open: false, item: null });
  const [cancelDialog, setCancelDialog] = useState<{ open: boolean; item: Validation | null }>({ open: false, item: null });
  const [feedbackDialog, setFeedbackDialog] = useState<{ open: boolean; item: Validation | null }>({ open: false, item: null });

  const handleValidate = (id: string) => {
    const item = items.find(i => i.id === id);
    if (item) {
      setValidateDialog({ open: true, item });
    }
  };

  const handleCancel = (id: string) => {
    const item = items.find(i => i.id === id);
    if (item) {
      setCancelDialog({ open: true, item });
    }
  };

  const handleFeedback = (id: string) => {
    const item = items.find(i => i.id === id);
    if (item) {
      setFeedbackDialog({ open: true, item });
    }
  };

  const handleArchiveClick = (id: string) => {
    setSelectedValidationId(id);
    setIsArchivesOpen(false);
    setArchiveSheetOpen(true);
  };

  const confirmValidate = async () => {
    if (!validateDialog.item) return;

    approveValidation.mutate({
      id: validateDialog.item.id,
      request: { always_allow: false }
    }, {
      onSuccess: () => {
        setValidateDialog({ open: false, item: null });
      }
    });
  };

  const confirmCancel = async () => {
    if (!cancelDialog.item) return;

    rejectValidation.mutate({
      id: cancelDialog.item.id,
      request: { reason: 'User cancelled' }
    }, {
      onSuccess: () => {
        setCancelDialog({ open: false, item: null });
      }
    });
  };

  const confirmFeedback = async (feedbackText: string) => {
    if (!feedbackDialog.item) return;

    feedbackValidation.mutate({
      id: feedbackDialog.item.id,
      request: { feedback: feedbackText }
    }, {
      onSuccess: () => {
        setFeedbackDialog({ open: false, item: null });
      }
    });
  };

  return (
    <AppLayout>
      <div className="container mx-auto px-4 py-8 max-w-7xl">
        <div className="mb-8">
          <h1 className="text-3xl font-bold tracking-tight">Validation</h1>
          <p className="text-muted-foreground mt-1">
            Gérez les éléments en attente de validation
          </p>
        </div>

        {isLoading ? (
          <div className="text-center py-12">
            <p className="text-muted-foreground">Chargement...</p>
          </div>
        ) : items.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-muted-foreground">Aucun élément en attente de validation</p>
          </div>
        ) : (
          <div className="space-y-4">
            {items.map((item) => (
              <ValidationCard
                key={item.id}
                {...item}
                onValidate={handleValidate}
                onCancel={handleCancel}
                onFeedback={handleFeedback}
              />
            ))}
          </div>
        )}
      </div>

      <Button
        size="icon-lg"
        className="fixed bottom-6 right-6 rounded-full shadow-lg"
        onClick={() => setIsArchivesOpen(true)}
        title="Voir les archives"
      >
        <Archive className="size-5" />
      </Button>

      <ArchivesSidebar
        open={isArchivesOpen}
        onOpenChange={setIsArchivesOpen}
        items={archivedItems}
        onItemClick={handleArchiveClick}
      />

      <ValidationArchiveSheet
        validationId={selectedValidationId}
        open={archiveSheetOpen}
        onOpenChange={(open) => {
          setArchiveSheetOpen(open);
          if (!open) {
            setTimeout(() => setSelectedValidationId(null), 300);
          }
        }}
      />

      <ConfirmDialog
        open={validateDialog.open}
        onOpenChange={(open) => setValidateDialog({ open, item: null })}
        title="Confirmer la validation"
        description={`Êtes-vous sûr de vouloir valider : "${validateDialog.item?.title}" ?`}
        confirmLabel="Valider"
        cancelLabel="Annuler"
        onConfirm={confirmValidate}
        variant="default"
      />

      <ConfirmDialog
        open={cancelDialog.open}
        onOpenChange={(open) => setCancelDialog({ open, item: null })}
        title="Confirmer l'annulation"
        description={`Êtes-vous sûr de vouloir annuler : "${cancelDialog.item?.title}" ?`}
        confirmLabel="Annuler l'élément"
        cancelLabel="Retour"
        onConfirm={confirmCancel}
        variant="destructive"
      />

      <FeedbackDialog
        open={feedbackDialog.open}
        onOpenChange={(open) => setFeedbackDialog({ open, item: null })}
        itemTitle={feedbackDialog.item?.title || ''}
        onSubmit={confirmFeedback}
      />
    </AppLayout>
  );
}
