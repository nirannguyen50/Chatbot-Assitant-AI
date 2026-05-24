"""
Gửi email qua SMTP (hỗ trợ Gmail App Password).
Dùng aiosmtplib để không block event loop của FastAPI.
"""
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib

from app.config import settings

logger = logging.getLogger(__name__)


async def send_reset_email(to_email: str, raw_token: str) -> None:
    """
    Gửi email chứa link đặt lại mật khẩu.
    Không raise exception ra ngoài — lỗi chỉ được log.
    """
    reset_link = f"{settings.BASE_URL}/reset-password?token={raw_token}"

    html_body = f"""
<!DOCTYPE html>
<html lang="vi">
<head><meta charset="UTF-8"></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
             background:#f1f5f9;padding:40px 0;margin:0">
  <div style="max-width:480px;margin:0 auto;background:#fff;
              border-radius:12px;padding:40px;
              box-shadow:0 4px 24px rgba(0,0,0,0.08)">
    <h2 style="color:#4F46E5;margin:0 0 8px">Đặt lại mật khẩu</h2>
    <p style="color:#64748b;font-size:14px;margin:0 0 24px">
      Chúng tôi nhận được yêu cầu đặt lại mật khẩu cho tài khoản của bạn.
    </p>
    <a href="{reset_link}"
       style="display:inline-block;background:#4F46E5;color:#fff;
              text-decoration:none;padding:12px 28px;border-radius:8px;
              font-size:15px;font-weight:600">
      Đặt lại mật khẩu
    </a>
    <p style="color:#94a3b8;font-size:13px;margin:24px 0 0">
      Link có hiệu lực trong <strong>1 giờ</strong>.<br>
      Nếu bạn không yêu cầu, hãy bỏ qua email này.
    </p>
    <hr style="border:none;border-top:1px solid #e2e8f0;margin:24px 0">
    <p style="color:#cbd5e1;font-size:12px;margin:0">
      {settings.APP_NAME} · Không trả lời email này
    </p>
  </div>
</body>
</html>
"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Đặt lại mật khẩu của bạn"
    msg["From"]    = settings.SMTP_FROM or settings.SMTP_USER
    msg["To"]      = to_email
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        await aiosmtplib.send(
            msg,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER,
            password=settings.SMTP_PASSWORD,
            start_tls=True,
        )
        logger.info("Reset email sent to %s", to_email)
    except Exception as exc:
        logger.error("Failed to send reset email to %s: %s", to_email, exc)
