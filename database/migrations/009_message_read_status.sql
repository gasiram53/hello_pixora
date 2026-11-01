USE pixora;

ALTER TABLE messages
  ADD COLUMN is_read BOOLEAN NOT NULL DEFAULT FALSE AFTER media_path,
  ADD INDEX idx_messages_unread (recipient_id, is_read, sender_id);

UPDATE messages SET is_read = TRUE;
