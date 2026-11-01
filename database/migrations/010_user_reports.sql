USE pixora;

CREATE TABLE IF NOT EXISTS user_reports (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  reporter_id BIGINT UNSIGNED NOT NULL,
  reported_user_id BIGINT UNSIGNED NOT NULL,
  reason ENUM('spam', 'harassment', 'impersonation', 'inappropriate', 'other') NOT NULL,
  details VARCHAR(500) NOT NULL DEFAULT '',
  status ENUM('pending', 'reviewed', 'resolved', 'dismissed') NOT NULL DEFAULT 'pending',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_user_report_pair (reporter_id, reported_user_id),
  INDEX idx_user_reports_queue (status, created_at),
  CONSTRAINT fk_user_report_reporter FOREIGN KEY (reporter_id) REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT fk_user_report_target FOREIGN KEY (reported_user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;
