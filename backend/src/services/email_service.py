"""
Email Service for Portkit

SendGrid integration for transactional emails.
"""

import logging
import os
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


FRONTEND_URL = os.getenv("FRONTEND_URL", "https://portkit.cloud")


@dataclass
class EmailMessage:
    """Email message data."""

    to: str
    subject: str
    template: str
    context: Dict[str, Any]
    from_email: str = "noreply@portkit.cloud"
    cc: Optional[List[str]] = None
    bcc: Optional[List[str]] = None


class SendGridEmailService:
    """SendGrid email service."""

    def __init__(
        self,
        api_key: str,
        from_email: str = "noreply@portkit.cloud",
        from_name: str = "Portkit",
    ):
        self.api_key = api_key
        self.from_email = from_email
        self.from_name = from_name
        self._client = None

    def _get_client(self):
        """Lazy-load SendGrid client."""
        if self._client is None:
            try:
                import sendgrid
                from sendgrid.helpers.mail import Mail

                self._client = sendgrid.SendGridAPIClient(api_key=self.api_key)
                logger.info("SendGrid client initialized")
            except ImportError:
                logger.warning("sendgrid package not installed. Emails will be logged only.")
                self._client = None

        return self._client

    async def send(self, message: EmailMessage) -> bool:
        """
        Send email message.

        Args:
            message: Email message to send

        Returns:
            True if sent successfully
        """
        logger.info(f"Sending email to {message.to}: {message.subject}")
        logger.debug(f"Template: {message.template}, Context: {message.context}")

        client = self._get_client()
        if client is None:
            logger.warning(f"SendGrid not available. Email logged only: {message.subject}")
            return True

        try:
            plain_text, html_content = self._render_template(message.template, message.context)

            from sendgrid.helpers.mail import Mail, To, From, Subject

            mail = Mail(
                from_email=From(self.from_email, self.from_name),
                to_emails=To(message.to),
                subject=Subject(message.subject),
                plain_text_content=plain_text,
                html_content=html_content,
            )

            response = client.send(mail)

            logger.info(f"Email sent successfully. Status code: {response.status_code}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

    def _render_template(self, template: str, context: Dict[str, Any]) -> tuple[str, str]:
        """
        Render email template with context.

        Args:
            template: Template name
            context: Template context

        Returns:
            Tuple of (plain_text, html_content)
        """
        templates = {
            "email_verification": (self._email_verification_plain, self._email_verification_html),
            "password_reset": (self._password_reset_plain, self._password_reset_html),
            "welcome": (self._welcome_plain, self._welcome_html),
            "conversion_complete": (
                self._conversion_complete_plain,
                self._conversion_complete_html,
            ),
        }

        render_funcs = templates.get(template)
        if render_funcs is None:
            logger.warning(f"Unknown template: {template}")
            return (f"Unknown template: {template}", f"<p>Unknown template: {template}</p>")

        plain_func, html_func = render_funcs
        try:
            return (plain_func(**context), html_func(**context))
        except Exception as e:
            logger.error(f"Error rendering template {template}: {e}")
            return (str(e), f"<p>Error rendering template: {e}</p>")

    # ============================================
    # Email Templates
    # ============================================

    def _unsubscribe_url(self, email: str) -> str:
        """Generate unsubscribe URL."""
        import urllib.parse

        encoded_email = urllib.parse.quote(email)
        return f"{FRONTEND_URL}/unsubscribe?email={encoded_email}"

    def _email_verification_plain(
        self,
        verification_url: str,
        expiry_hours: int = 24,
    ) -> str:
        """Email verification plain text template."""
        return f"""
Welcome to Portkit!

Please verify your email address by clicking the link below:

{verification_url}

This link will expire in {expiry_hours} hours.

If you didn't create this account, please ignore this email.

Thanks,
The Portkit Team

---
Portkit - Java to Bedrock Mod Converter
https://portkit.cloud
"""

    def _email_verification_html(
        self,
        verification_url: str,
        expiry_hours: int = 24,
    ) -> str:
        """Email verification HTML template."""
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Verify Your Email</title>
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="text-align: center; margin-bottom: 30px;">
        <h1 style="color: #2c3e50;">Portkit</h1>
        <p style="color: #7f8c8d;">Java to Bedrock Mod Converter</p>
    </div>
    
    <div style="background: #f9f9f9; border-radius: 8px; padding: 30px; margin-bottom: 20px;">
        <h2 style="color: #27ae60; margin-top: 0;">Verify Your Email Address</h2>
        <p>Thank you for signing up! Please verify your email address by clicking the button below:</p>
        <div style="text-align: center; margin: 30px 0;">
            <a href="{verification_url}" style="background: #27ae60; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; font-weight: bold;">Verify Email</a>
        </div>
        <p style="font-size: 14px; color: #7f8c8d;">This link will expire in {expiry_hours} hours.</p>
        <p style="font-size: 14px; color: #7f8c8d;">Or copy and paste this URL into your browser:</p>
        <p style="font-size: 12px; word-break: break-all; color: #3498db;">{verification_url}</p>
    </div>
    
    <p style="font-size: 14px; color: #7f8c8d;">If you didn't create this account, please ignore this email.</p>
    
    <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
    <p style="font-size: 12px; color: #95a5a6; text-align: center;">
        Portkit - Java to Bedrock Mod Converter<br>
        <a href="https://portkit.cloud" style="color: #3498db;">https://portkit.cloud</a>
    </p>
</body>
</html>
"""

    def _password_reset_plain(
        self,
        reset_url: str,
        expiry_hours: int = 1,
        email: str = "",
    ) -> str:
        """Password reset plain text template."""
        unsubscribe = self._unsubscribe_url(email)
        return f"""
Password Reset Request

You requested a password reset for your Portkit account.

Click the link below to reset your password:

{reset_url}

This link will expire in {expiry_hours} hour(s).

If you didn't request this, please ignore this email and your password will remain unchanged.

Unsubscribe: {unsubscribe}

Thanks,
The Portkit Team

---
Portkit - Java to Bedrock Mod Converter
https://portkit.cloud
"""

    def _password_reset_html(
        self,
        reset_url: str,
        expiry_hours: int = 1,
        email: str = "",
    ) -> str:
        """Password reset HTML template."""
        unsubscribe = self._unsubscribe_url(email)
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Password Reset</title>
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="text-align: center; margin-bottom: 30px;">
        <h1 style="color: #2c3e50;">Portkit</h1>
        <p style="color: #7f8c8d;">Java to Bedrock Mod Converter</p>
    </div>
    
    <div style="background: #f9f9f9; border-radius: 8px; padding: 30px; margin-bottom: 20px;">
        <h2 style="color: #e74c3c; margin-top: 0;">Password Reset Request</h2>
        <p>You requested a password reset for your Portkit account.</p>
        <p>Click the button below to reset your password:</p>
        <div style="text-align: center; margin: 30px 0;">
            <a href="{reset_url}" style="background: #e74c3c; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; font-weight: bold;">Reset Password</a>
        </div>
        <p style="font-size: 14px; color: #7f8c8d;">This link will expire in {expiry_hours} hour(s).</p>
        <p style="font-size: 14px; color: #7f8c8d;">Or copy and paste this URL into your browser:</p>
        <p style="font-size: 12px; word-break: break-all; color: #3498db;">{reset_url}</p>
    </div>
    
    <p style="font-size: 14px; color: #7f8c8d;">If you didn't request this, please ignore this email and your password will remain unchanged.</p>
    
    <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
    <p style="font-size: 12px; color: #95a5a6; text-align: center;">
        <a href="{unsubscribe}" style="color: #95a5a6;">Unsubscribe from notifications</a><br>
        Portkit - Java to Bedrock Mod Converter<br>
        <a href="https://portkit.cloud" style="color: #3498db;">https://portkit.cloud</a>
    </p>
</body>
</html>
"""

    def _welcome_plain(
        self,
        user_name: str,
        email: str = "",
    ) -> str:
        """Welcome plain text template."""
        unsubscribe = self._unsubscribe_url(email)
        return f"""
Welcome to Portkit, {user_name}!

We're excited to have you on board. Portkit makes it easy to convert your Java mods to Bedrock add-ons.

Getting Started:
1. Upload your Java mod file (.jar or .zip)
2. Wait for the AI to convert it
3. Download your Bedrock add-on (.mcaddon)
4. Install and enjoy!

Need help? Check out our documentation:
https://docs.portkit.cloud

Have questions? Join our Discord:
https://discord.gg/portkit

Happy modding!
The Portkit Team

Unsubscribe: {unsubscribe}

---
Portkit - Java to Bedrock Mod Converter
https://portkit.cloud
"""

    def _welcome_html(
        self,
        user_name: str,
        email: str = "",
    ) -> str:
        """Welcome HTML template."""
        unsubscribe = self._unsubscribe_url(email)
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Welcome to Portkit</title>
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="text-align: center; margin-bottom: 30px;">
        <h1 style="color: #2c3e50;">Portkit</h1>
        <p style="color: #7f8c8d;">Java to Bedrock Mod Converter</p>
    </div>
    
    <div style="background: #f9f9f9; border-radius: 8px; padding: 30px; margin-bottom: 20px;">
        <h2 style="color: #27ae60; margin-top: 0;">Welcome, {user_name}!</h2>
        <p>We're excited to have you on board. Portkit makes it easy to convert your Java mods to Bedrock add-ons.</p>
        
        <h3 style="color: #2c3e50;">Getting Started:</h3>
        <ol style="color: #555;">
            <li>Upload your Java mod file (.jar or .zip)</li>
            <li>Wait for the AI to convert it</li>
            <li>Download your Bedrock add-on (.mcaddon)</li>
            <li>Install and enjoy!</li>
        </ol>
        
        <div style="text-align: center; margin: 30px 0;">
            <a href="{FRONTEND_URL}" style="background: #27ae60; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; font-weight: bold;">Start Converting</a>
        </div>
    </div>
    
    <div style="background: #ecf0f1; border-radius: 8px; padding: 20px; margin-bottom: 20px;">
        <h3 style="color: #2c3e50; margin-top: 0;">Need Help?</h3>
        <p>Check out our <a href="https://docs.portkit.cloud" style="color: #3498db;">documentation</a> or join our <a href="https://discord.gg/portkit" style="color: #3498db;">Discord</a> community.</p>
    </div>
    
    <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
    <p style="font-size: 12px; color: #95a5a6; text-align: center;">
        <a href="{unsubscribe}" style="color: #95a5a6;">Unsubscribe from notifications</a><br>
        Portkit - Java to Bedrock Mod Converter<br>
        <a href="https://portkit.cloud" style="color: #3498db;">https://portkit.cloud</a>
    </p>
</body>
</html>
"""

    def _conversion_complete_plain(
        self,
        conversion_id: str,
        download_url: str,
        success: bool,
        issues: Optional[List[str]] = None,
        email: str = "",
    ) -> str:
        """Conversion complete plain text template."""
        unsubscribe = self._unsubscribe_url(email)
        if success:
            body = f"""
Your mod conversion is complete!

Conversion ID: {conversion_id}
Status: completed successfully

Download your converted add-on:
{download_url}

Installation Instructions:
1. Download the .mcaddon file
2. Open Minecraft Bedrock Edition
3. Go to Settings → Storage → Import
4. Select the downloaded file
5. Create a new world with the add-on enabled

Enjoy your converted mod!
"""
        else:
            issues_text = "\n".join([f"- {issue}" for issue in (issues or [])])
            body = f"""
Your mod conversion encountered some issues.

Conversion ID: {conversion_id}
Status: failed

Issues found:
{issues_text}

Please review the issues and try again with a different mod file, or contact support for assistance.

Support: support@portkit.cloud
"""

        return f"""
Mod Conversion Complete

{body}

View conversion details:
{FRONTEND_URL}/conversions/{conversion_id}

Unsubscribe: {unsubscribe}

Thanks,
The Portkit Team

---
Portkit - Java to Bedrock Mod Converter
https://portkit.cloud
"""

    def _conversion_complete_html(
        self,
        conversion_id: str,
        download_url: str,
        success: bool,
        issues: Optional[List[str]] = None,
        email: str = "",
    ) -> str:
        """Conversion complete HTML template."""
        unsubscribe = self._unsubscribe_url(email)
        if success:
            status_color = "#27ae60"
            status_text = "Completed Successfully"
            body_content = f"""
            <p>Your mod conversion is complete!</p>
            <p><strong>Conversion ID:</strong> {conversion_id}</p>
            <div style="text-align: center; margin: 30px 0;">
                <a href="{download_url}" style="background: #27ae60; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; font-weight: bold;">Download Add-on</a>
            </div>
            <h3 style="color: #2c3e50;">Installation Instructions:</h3>
            <ol style="color: #555;">
                <li>Download the .mcaddon file</li>
                <li>Open Minecraft Bedrock Edition</li>
                <li>Go to Settings → Storage → Import</li>
                <li>Select the downloaded file</li>
                <li>Create a new world with the add-on enabled</li>
            </ol>
            <p>Enjoy your converted mod!</p>
"""
        else:
            status_color = "#e74c3c"
            status_text = "Failed"
            issues_html = "<br>".join(
                [f'<li style="color: #e74c3c;">{issue}</li>' for issue in (issues or [])]
            )
            body_content = f"""
            <p>Your mod conversion encountered some issues.</p>
            <p><strong>Conversion ID:</strong> {conversion_id}</p>
            <p><strong>Status:</strong> <span style="color: #e74c3c;">{status_text}</span></p>
            <h3 style="color: #2c3e50;">Issues Found:</h3>
            <ul style="color: #e74c3c;">
                {issues_html}
            </ul>
            <p>Please review the issues and try again with a different mod file, or contact support for assistance.</p>
            <p>Support: <a href="mailto:support@portkit.cloud" style="color: #3498db;">support@portkit.cloud</a></p>
"""

        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Conversion Complete</title>
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="text-align: center; margin-bottom: 30px;">
        <h1 style="color: #2c3e50;">Portkit</h1>
        <p style="color: #7f8c8d;">Java to Bedrock Mod Converter</p>
    </div>
    
    <div style="background: #f9f9f9; border-radius: 8px; padding: 30px; margin-bottom: 20px;">
        <h2 style="color: {status_color}; margin-top: 0;">Conversion {status_text}</h2>
        {body_content}
        <p><a href="{FRONTEND_URL}/conversions/{conversion_id}" style="color: #3498db;">View conversion details</a></p>
    </div>
    
    <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
    <p style="font-size: 12px; color: #95a5a6; text-align: center;">
        <a href="{unsubscribe}" style="color: #95a5a6;">Unsubscribe from notifications</a><br>
        Portkit - Java to Bedrock Mod Converter<br>
        <a href="https://portkit.cloud" style="color: #3498db;">https://portkit.cloud</a>
    </p>
</body>
</html>
"""


# Singleton instance
_email_service = None


def get_email_service(
    api_key: Optional[str] = None,
    from_email: str = "noreply@portkit.cloud",
) -> SendGridEmailService:
    """Get or create email service singleton."""
    global _email_service
    if _email_service is None:
        import os

        api_key = api_key or os.getenv("SENDGRID_API_KEY")

        if not api_key:
            logger.warning("SendGrid API key not configured. Emails will be logged only.")
            api_key = "dummy-key-for-development"

        _email_service = SendGridEmailService(api_key=api_key, from_email=from_email)

    return _email_service


async def send_verification_email(
    email: str,
    verification_token: str,
    expiry_hours: int = 24,
) -> bool:
    """
    Send email verification email.

    Args:
        email: Recipient email address
        verification_token: The verification token
        expiry_hours: Token expiry in hours

    Returns:
        True if sent successfully
    """
    import os

    frontend_url = os.getenv("FRONTEND_URL", "https://portkit.cloud")
    verification_url = f"{frontend_url}/auth/verify-email/{verification_token}"

    service = get_email_service()
    message = EmailMessage(
        to=email,
        subject="Verify Your Portkit Email",
        template="email_verification",
        context={
            "verification_url": verification_url,
            "expiry_hours": expiry_hours,
        },
    )
    return await service.send(message)


async def send_password_reset_email(
    email: str,
    reset_token: str,
    expiry_hours: int = 1,
) -> bool:
    """
    Send password reset email.

    Args:
        email: Recipient email address
        reset_token: The reset token
        expiry_hours: Token expiry in hours

    Returns:
        True if sent successfully
    """
    import os

    frontend_url = os.getenv("FRONTEND_URL", "https://portkit.cloud")
    reset_url = f"{frontend_url}/auth/reset-password/{reset_token}"

    service = get_email_service()
    message = EmailMessage(
        to=email,
        subject="Reset Your Portkit Password",
        template="password_reset",
        context={
            "reset_url": reset_url,
            "expiry_hours": expiry_hours,
            "email": email,
        },
    )
    return await service.send(message)


async def send_welcome_email(
    email: str,
    user_name: str,
) -> bool:
    """
    Send welcome email.

    Args:
        email: Recipient email address
        user_name: User's name

    Returns:
        True if sent successfully
    """
    service = get_email_service()
    message = EmailMessage(
        to=email,
        subject="Welcome to Portkit!",
        template="welcome",
        context={
            "user_name": user_name,
            "email": email,
        },
    )
    return await service.send(message)


async def send_conversion_notification(
    email: str,
    conversion_id: str,
    download_url: str,
    success: bool,
    issues: Optional[List[str]] = None,
) -> bool:
    """
    Send conversion completion notification.

    Args:
        email: Recipient email address
        conversion_id: The conversion ID
        download_url: URL to download the converted add-on
        success: Whether conversion succeeded
        issues: List of issues if conversion failed

    Returns:
        True if sent successfully
    """
    service = get_email_service()
    message = EmailMessage(
        to=email,
        subject="Your Portkit Conversion is Complete",
        template="conversion_complete",
        context={
            "conversion_id": conversion_id,
            "download_url": download_url,
            "success": success,
            "issues": issues,
            "email": email,
        },
    )
    return await service.send(message)
