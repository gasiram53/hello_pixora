from datetime import datetime, timedelta, timezone
import secrets

from werkzeug.security import check_password_hash, generate_password_hash

from models.user_model import get_otp, get_otp_request_stats, log_otp_request, save_otp


class OtpRateLimitError(RuntimeError):
    pass


def issue_otp(user_id):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    stats = get_otp_request_stats(user_id)
    if stats and (
        stats["request_count"] >= 5
        or (
            stats["latest_request_at"]
            and now - stats["latest_request_at"] < timedelta(seconds=60)
        )
    ):
        raise OtpRateLimitError("Please wait before requesting another verification code.")
    log_otp_request(user_id)
    code = f"{secrets.randbelow(1_000_000):06d}"
    expires_at = now + timedelta(minutes=10)
    save_otp(user_id, generate_password_hash(code), expires_at)
    return code


def verify_otp(user_id, submitted_code):
    record = get_otp(user_id)
    if not record or record["expires_at"] <= datetime.utcnow():
        return False
    return check_password_hash(record["code_hash"], submitted_code)
