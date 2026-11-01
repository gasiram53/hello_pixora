# PIXORA

PIXORA is a Flask/MySQL social-sharing MVP. It includes email-verified accounts,
profiles, a followed-users feed, photo posts, likes, comments, follows, search,
stories, reels, direct messages with WebRTC voice/video calls, notifications,
and account settings.

## Requirements

- Python 3.10+
- MySQL 8+
- SMTP credentials for registration verification and password-reset emails

## Local setup

1. Create and activate a virtual environment:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. Install dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

3. Copy the environment template, then edit `.env`:

   ```powershell
   Copy-Item .env.example .env
   ```

   Replace `SECRET_KEY` with a long random value, configure your
   MySQL credentials, then configure the SMTP values used to send OTP emails.
   Never use the example secret in a deployed application.

4. Create the database and tables:

   ```powershell
   Get-Content -Raw database.sql | mysql -u root -p
   ```

   Existing databases can apply the optional profile website field with:

   ```powershell
   Get-Content -Raw database/migrations/001_add_user_website.sql | mysql -u root -p pixora
   ```

   Reel likes, saves, and comments are added to existing databases with:

   ```powershell
   Get-Content -Raw database/migrations/002_add_reel_engagement.sql | mysql -u root -p pixora
   ```

   Existing databases add story captions, overlays, media types, and view
   tracking with:

   ```powershell
   Get-Content -Raw database/migrations/003_enhance_stories.sql | mysql -u root -p pixora
   ```

   Existing databases add video posts and image attachments in messages with:

   ```powershell
   Get-Content -Raw database/migrations/004_post_media_type.sql | mysql -u root -p pixora
   ```

   Persistent post saves are added with:

   ```powershell
   Get-Content -Raw database/migrations/005_saved_posts.sql | mysql -u root -p pixora
   ```

   Existing databases add message notifications and OTP request limits with:

   ```powershell
   Get-Content -Raw database/migrations/006_notifications_otp_limits.sql | mysql -u root -p pixora
   ```

   Normalized hashtag tables for newly published posts are added with:

   ```powershell
   Get-Content -Raw database/migrations/007_normalize_hashtags.sql | mysql -u root -p pixora
   ```

   Story access honors public/private account visibility with:

   ```powershell
   Get-Content -Raw database/migrations/008_story_privacy.sql | mysql -u root -p pixora
   ```

   Message unread badges and read status are added to existing databases with:

   ```powershell
   Get-Content -Raw database/migrations/009_message_read_status.sql | mysql -u root -p pixora
   ```

   Profile reporting for existing databases is added with:

   ```powershell
   Get-Content -Raw database/migrations/010_user_reports.sql | mysql -u root -p pixora
   ```

5. Start the development server:

   ```powershell
   python app.py
   ```

   Open `http://127.0.0.1:5000`.

Posts and reel uploads are stored under `static/uploads/`; story media is stored
under the ignored `private_uploads/stories/` directory and served through an
authenticated, privacy-checked route. Post and reel media is limited to 20 MB,
stories to 16 MB, and profile images to 5 MB. File extensions and signatures
are both validated. Production deployments should use private/object storage
and serve private media through a controlled media layer.

## Tests

```powershell
python -m unittest discover -s tests -v
```

Tests disable CSRF for the test client and mock external database operations.
The application itself requires the MySQL schema above and SMTP configuration
for email delivery.

## Notes

- Forms use CSRF protection and passwords are stored as Werkzeug password hashes.
- Account settings let signed-in users change their username after confirming
  their current password, and change their password after verifying the current
  password. Usernames are 3–30 letters, numbers, or underscores.
- A persistent browser preference toggles the shared light/dark theme.
- OTP codes expire after ten minutes and are stored as hashes.
- OTP issuance has a per-account 60-second cooldown and a five-requests-per-hour cap.
- Direct messages are authenticated and CSRF-protected, store text and private
  image attachments, and serve attachments only to conversation participants.
  Flask-SocketIO delivers new messages to authenticated recipients; socket
  connections join only the room associated with their Flask session. The
  Socket.IO WebSocket client is served by the app, so messaging and call
  signaling do not depend on an external client CDN. Calls use WebRTC for
  peer-to-peer media and authenticated Socket.IO signaling.
  Browsers need microphone/camera permission and a secure context (HTTPS, or
  localhost during development). The default public STUN servers may not
  connect through restrictive NATs or firewalls; configure a TURN service for
  reliable production connectivity. Text messages retain a three-second
  authenticated polling fallback when a WebSocket connection is unavailable;
  calls require a working WebSocket connection for signaling.
- Search supports verified people, post captions/hashtags, and reel captions
  using the existing database tables. Search history is stored in the browser;
  no database migration is needed.
- Stories support images and videos, short captions and overlays, follow-only
  viewing for private accounts and public viewing for public accounts, view
  tracking, owner-only deletion, and direct-message replies. Story media is
  served through an authenticated, privacy-checked route. Active stories expire
  automatically after 24 hours; expired records and media are cleaned up when
  the feed or Stories page is requested.
- This is an academic MVP. Before public launch, add moderation, operational
  monitoring, backups,
  and production-grade upload storage. For Render, connect a MySQL-compatible
  managed database, configure the environment variables listed in `.env.example`,
  and deploy using the included `render.yaml`; uploads on ephemeral service
  disks are not durable and should be moved to object storage.
