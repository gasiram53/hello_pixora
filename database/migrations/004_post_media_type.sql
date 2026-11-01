USE pixora;

ALTER TABLE posts
  ADD COLUMN media_type ENUM('image', 'video') NOT NULL DEFAULT 'image'
  AFTER image_path;

ALTER TABLE messages
  ADD COLUMN media_path VARCHAR(255) NULL
  AFTER body;
