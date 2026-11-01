ALTER TABLE stories
  ADD COLUMN media_type VARCHAR(10) NOT NULL DEFAULT 'image' AFTER media_path,
  ADD COLUMN caption VARCHAR(500) NOT NULL DEFAULT '' AFTER media_type,
  ADD COLUMN overlay_text VARCHAR(120) NOT NULL DEFAULT '' AFTER caption;

UPDATE stories
SET media_type = CASE
  WHEN LOWER(media_path) REGEXP '\\.(mp4|webm|mov)$' THEN 'video'
  ELSE 'image'
END;

CREATE TABLE IF NOT EXISTS story_views (
  story_id BIGINT UNSIGNED NOT NULL,
  viewer_id BIGINT UNSIGNED NOT NULL,
  viewed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (story_id, viewer_id),
  INDEX idx_story_views_viewer (viewer_id, viewed_at),
  CONSTRAINT fk_story_view_story FOREIGN KEY (story_id) REFERENCES stories(id) ON DELETE CASCADE,
  CONSTRAINT fk_story_viewer_user FOREIGN KEY (viewer_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;
