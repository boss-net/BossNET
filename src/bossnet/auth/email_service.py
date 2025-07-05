import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from config import settings


class EmailTemplate(Enum):
    """Available email templates"""

    VERIFICATION = "verification_email.html"
    PASSWORD_RESET = "password_reset_email.html"
    WELCOME = "welcome_email.html"
    PASSWORD_CHANGED = "password_changed.html"
    ACCOUNT_LOCKED = "account_locked.html"


class EmailService:
    """Service for sending emails with templates"""

    def __init__(self):
        # Set up Jinja2 environment
        template_path = Path(__file__).parent / "templates"
        self.env = Environment(loader=FileSystemLoader(template_path), autoescape=select_autoescape(["html", "xml"]))

        # Email settings
        self.smtp_server = settings.SMTP_SERVER
        self.smtp_port = settings.SMTP_PORT
        self.smtp_username = settings.SMTP_USERNAME
        self.smtp_password = settings.SMTP_PASSWORD
        self.smtp_use_tls = settings.SMTP_USE_TLS
        self.smtp_from = settings.EMAILS_FROM_EMAIL
        self.smtp_from_name = settings.EMAILS_FROM_NAME

    def send_email(
        self,
        to_email: str,
        subject: str,
        template: EmailTemplate,
        template_vars: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Send an email using the specified template

        Args:
            to_email: Recipient email address
            subject: Email subject
            template: Email template to use
            template_vars: Variables to pass to the template

        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        if template_vars is None:
            template_vars = {}

        try:
            # Load and render the template
            template = self.env.get_template(template.value)
            html_content = template.render(**template_vars)

            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{self.smtp_from_name} <{self.smtp_from}>"
            msg["To"] = to_email

            # Attach HTML content
            part = MIMEText(html_content, "html")
            msg.attach(part)

            # Send the email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.smtp_use_tls:
                    server.starttls()
                if self.smtp_username and self.smtp_password:
                    server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)

            return True

        except Exception as e:
            print(f"Error sending email: {e}")
            return False

    def send_verification_email(self, to_email: str, username: str, token: str) -> bool:
        """Send email verification email"""
        verification_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"

        return self.send_email(
            to_email=to_email,
            subject="Verify your email address",
            template=EmailTemplate.VERIFICATION,
            template_vars={
                "name": username,
                "verification_url": verification_url,
                "app_name": settings.PROJECT_NAME,
                "support_email": settings.EMAILS_FROM_EMAIL,
            },
        )

    def send_password_reset_email(self, to_email: str, username: str, token: str) -> bool:
        """Send password reset email"""
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"

        return self.send_email(
            to_email=to_email,
            subject="Reset your password",
            template=EmailTemplate.PASSWORD_RESET,
            template_vars={
                "name": username,
                "reset_url": reset_url,
                "expiration_hours": 24,  # Should match token expiration
                "app_name": settings.PROJECT_NAME,
                "support_email": settings.EMAILS_FROM_EMAIL,
            },
        )

    def send_welcome_email(self, to_email: str, username: str) -> bool:
        """Send welcome email after successful registration"""
        return self.send_email(
            to_email=to_email,
            subject=f"Welcome to {settings.PROJECT_NAME}!",
            template=EmailTemplate.WELCOME,
            template_vars={
                "name": username,
                "app_name": settings.PROJECT_NAME,
                "support_email": settings.EMAILS_FROM_EMAIL,
                "login_url": f"{settings.FRONTEND_URL}/login",
            },
        )

    def send_password_changed_email(self, to_email: str, username: str) -> bool:
        """Send confirmation email after password change"""
        return self.send_email(
            to_email=to_email,
            subject="Your password has been changed",
            template=EmailTemplate.PASSWORD_CHANGED,
            template_vars={
                "name": username,
                "app_name": settings.PROJECT_NAME,
                "support_email": settings.EMAILS_FROM_EMAIL,
                "login_url": f"{settings.FRONTEND_URL}/login",
            },
        )

    def send_account_locked_email(self, to_email: str, username: str, unlock_time: str) -> bool:
        """Send account locked notification email"""
        return self.send_email(
            to_email=to_email,
            subject="Account Locked - Too Many Failed Login Attempts",
            template=EmailTemplate.ACCOUNT_LOCKED,
            template_vars={
                "name": username,
                "unlock_time": unlock_time,
                "app_name": settings.PROJECT_NAME,
                "support_email": settings.EMAILS_FROM_EMAIL,
            },
        )
