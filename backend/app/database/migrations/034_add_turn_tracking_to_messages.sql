-- Migration: add_turn_tracking_to_messages
-- Description: Ajoute les colonnes turn_id et sequence_index pour permettre
--              le tracking des tours de conversation et l'ordre des segments

-- Ajout des colonnes pour le tracking des tours
ALTER TABLE messages
ADD COLUMN turn_id VARCHAR(36),
ADD COLUMN sequence_index INTEGER;

-- Création d'un index pour améliorer les performances de tri
CREATE INDEX idx_messages_turn_id ON messages(turn_id);

-- Commentaires pour documentation
COMMENT ON COLUMN messages.turn_id IS 'Identifiant unique du tour de conversation (même turn_id pour plusieurs messages liés)';
COMMENT ON COLUMN messages.sequence_index IS 'Index de séquence pour garantir l''ordre d''affichage des messages dans un même turn';
