"""
Email Service for ModPorter AI

SendGrid integration for transactional emails.
"""

import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class EmailMessage:
    """Email message data."""

    to: str
    subject: str
    template: str
    context: Dict[str, Any]
    from_email: str = "noreply@modporter.ai"
    cc: Optional[List[str]] = None
    bcc: Optional[List[str]] = None


class SendGridEmailService:
    """SendGrid email service."""

    def __init__(
        self,
        api_key: str,
        from_email: str = "noreply@modporter.ai",
        from_name: str = "ModPorter AI",
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
                logger.warning(
                    "sendgrid package not installed. Emails will be logged only."
                )
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
        # Log email (always)
        logger.info(f"Sending email to {message.to}: {message.subject}")
        logger.debug(f"Template: {message.template}, Context: {message.context}")

        # If SendGrid not available, just log
        client = self._get_client()
        if client is None:
            logger.warning(
                f"SendGrid not available. Email logged only: {message.subject}"
            )
            return True

        try:
            # Build email content from template
            content = self._render_template(message.template, message.context)

            # Create email message
            from sendgrid.helpers.mail import Mail, To, From, Subject

            mail = Mail(
                from_email=From(self.from_email, self.from_name),
                to_emails=To(message.to),
                subject=Subject(message.subject),
                plain_text_content=content,
            )

            # Send email
            response = client.send(mail)

            logger.info(f"Email sent successfully. Status code: {response.status_code}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

    def _render_template(self, template: str, context: Dict[str, Any]) -> str:
        """
        Render email template with context.

        Args:
            template: Template name
            context: Template context

        Returns:
            Rendered email content
        """
        templates = {
            "email_verification": self._email_verification_template,
            "password_reset": self._password_reset_template,
            "welcome": self._welcome_template,
            "conversion_complete": self._conversion_complete_template,
        }

        render_func = templates.get(template)
        if render_func is None:
            logger.warning(f"Unknown template: {template}")
            return f"Unknown template: {template}"

        return render_func(**context)

    # ============================================
    # Email Templates
    # ============================================

    def _email_verification_template(
        self,
        verification_url: str,
        expiry_hours: int = 24,
    ) -> str:
        """Email verification template."""
        return f"""
Welcome to ModPorter AI!

Please verify your email address by clicking the link below:

{verification_url}

This link will expire in {expiry_hours} hours.

If you didn't create this account, please ignore this email.

Thanks,
The ModPorter AI Team

---
ModPorter AI - Java to Bedrock Mod Converter
https://modporter.ai
"""

    def _password_reset_template(
        self,
        reset_url: str,
        expiry_hours: int = 1,
    ) -> str:
        """Password reset template."""
        return f"""
Password Reset Request

You requested a password reset for your ModPorter AI account.

Click the link below to reset your password:

{reset_url}

This link will expire in {expiry_hours} hour(s).

If you didn't request this, please ignore this email and your password will remain unchanged.

Thanks,
The ModPorter AI Team

---
ModPorter AI - Java to Bedrock Mod Converter
https://modporter.ai
"""

    def _welcome_template(
        self,
        user_name: str,
    ) -> str:
        """Welcome email template."""
        return f"""
Welcome to ModPorter AI, {user_name}!

We're excited to have you on board. ModPorter AI makes it easy to convert your Java mods to Bedrock add-ons.

Getting Started:
1. Upload your Java mod file (.jar or .zip)
2. Wait for the AI to convert it
3. Download your Bedrock add-on (.mcaddon)
4. Install and enjoy!

Need help? Check out our documentation:
https://docs.modporter.ai

Have questions? Join our Discord:
https://discord.gg/modporter-ai

Happy modding!
The ModPorter AI Team

---
ModPorter AI - Java to Bedrock Mod Converter
https://modporter.ai
"""

    def _conversion_complete_template(
        self,
        conversion_id: str,
        download_url: str,
        success: bool,
        issues: Optional[List[str]] = None,
    ) -> str:
        """Conversion complete notification template."""
        if success:
            status = "completed successfully"
            body = f"""
Your mod conversion is complete!

Conversion ID: {conversion_id}
Status: {status}

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
            status = "failed"
            issues_text = "\n".join([f"- {issue}" for issue in (issues or [])])
            body = f"""
Your mod conversion encountered some issues.

Conversion ID: {conversion_id}
Status: {status}

Issues found:
{issues_text}

Please review the issues and try again with a different mod file, or contact support for assistance.

Support: support@modporter.ai
"""

        return f"""
Mod Conversion Complete

{body}

View conversion details:
https://modporter.ai/conversions/{conversion_id}

Thanks,
The ModPorter AI Team

---
ModPorter AI - Java to Bedrock Mod Converter
https://modporter.ai
"""


# Singleton instance
_email_service = None


def get_email_service(
    api_key: Optional[str] = None,
    from_email: str = "noreply@modporter.ai",
) -> SendGridEmailService:
    """Get or create email service singleton."""
    global _email_service
    if _email_service is None:
        import os

        api_key = api_key or os.getenv("SENDGRID_API_KEY")

        if not api_key:
            logger.warning(
                "SendGrid API key not configured. Emails will be logged only."
            )
            api_key = "dummy-key-for-development"

        _email_service = SendGridEmailService(api_key=api_key, from_email=from_email)

    return _email_service
