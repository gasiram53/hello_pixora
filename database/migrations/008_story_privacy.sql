USE pixora;

ALTER TABLE users
  ADD COLUMN is_private BOOLEAN NOT NULL DEFAULT FALSE
  AFTER is_verified;
