USE pixora;

ALTER TABLE notifications
  MODIFY kind ENUM('follow', 'like', 'comment', 'message') NOT NULL;

CREATE TABLE otp_request_log (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  user_id BIGINT UNSIGNED NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_otp_request_user_time (user_id, created_at),
  CONSTRAINT fk_otp_request_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;
