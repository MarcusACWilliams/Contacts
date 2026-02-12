"""
Messaging service for sending emails and SMS to contacts.
Supports multiple providers (SendGrid, SMTP, AWS SES for email; Twilio, AWS SNS for SMS)
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional, Dict, Any
import asyncio
from functools import wraps
from classes.emails import emailaddress


def async_wrap(func):
    """Wrapper to run synchronous functions in async context"""
    @wraps(func)
    async def run(*args, **kwargs):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))
    return run


class EmailMessenger:
    """Service for sending emails to contacts"""
    
    def __init__(self):
        self.provider = os.getenv("EMAIL_PROVIDER", "smtp")
        self.sender_email = os.getenv("SENDER_EMAIL", "noreply@contacts-app.com")
        self.sender_name = os.getenv("SENDER_NAME", "Contacts App")
        
        # SMTP configuration
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        
        # SendGrid configuration
        self.sendgrid_api_key = os.getenv("SENDGRID_API_KEY", "")
    
    def validate_email_address(self, email: str) -> bool:
        """Validate email address using emailaddress class"""
        try:
            emailaddress(email)
            return True
        except ValueError:
            return False
    
    @async_wrap
    def send_via_smtp(
        self,
        recipient_email: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send email via SMTP (Gmail, Outlook, etc.)"""
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.sender_name} <{self.sender_email}>"
            msg['To'] = recipient_email
            
            # Attach plain text
            text_part = MIMEText(body, 'plain')
            msg.attach(text_part)
            
            # Attach HTML if provided
            if html_body:
                html_part = MIMEText(html_body, 'html')
                msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            return {
                "success": True,
                "status": "sent",
                "provider": "smtp",
                "message_id": None
            }
        except Exception as e:
            return {
                "success": False,
                "status": "failed",
                "error": str(e),
                "provider": "smtp"
            }
    
    async def send_via_sendgrid(
        self,
        recipient_email: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send email via SendGrid API"""
        try:
            # Import SendGrid only if this provider is used
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail, Content
            
            # Create message
            if html_body:
                content = Content("text/html", html_body)
            else:
                content = Content("text/plain", body)
            
            message = Mail(
                from_email=self.sender_email,
                to_emails=recipient_email,
                subject=subject,
                plain_text_content=body if not html_body else None,
                html_content=html_body if html_body else None
            )
            
            # Send email
            sg = SendGridAPIClient(self.sendgrid_api_key)
            response = sg.send(message)
            
            return {
                "success": True,
                "status": "sent",
                "provider": "sendgrid",
                "message_id": response.headers.get('X-Message-Id'),
                "status_code": response.status_code
            }
        except Exception as e:
            return {
                "success": False,
                "status": "failed",
                "error": str(e),
                "provider": "sendgrid"
            }
    
    async def send_email(
        self,
        recipient_email: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        contact_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send email using configured provider
        
        Args:
            recipient_email: Email address to send to
            subject: Email subject line
            body: Plain text email body
            html_body: Optional HTML version of email body
            contact_id: Optional contact ID for tracking
            
        Returns:
            Dictionary with success status, message_id, error info
        """
        # Validate email
        if not self.validate_email_address(recipient_email):
            return {
                "success": False,
                "status": "failed",
                "error": "Invalid recipient email address"
            }
        
        # Check provider configuration
        if self.provider == "smtp":
            if not self.smtp_username or not self.smtp_password:
                return {
                    "success": False,
                    "status": "failed",
                    "error": "SMTP credentials not configured"
                }
            result = await self.send_via_smtp(recipient_email, subject, body, html_body)
        elif self.provider == "sendgrid":
            if not self.sendgrid_api_key:
                return {
                    "success": False,
                    "status": "failed",
                    "error": "SendGrid API key not configured"
                }
            result = await self.send_via_sendgrid(recipient_email, subject, body, html_body)
        else:
            return {
                "success": False,
                "status": "failed",
                "error": f"Unsupported email provider: {self.provider}"
            }
        
        # Add timestamp
        result["timestamp"] = datetime.utcnow().isoformat()
        if result["success"]:
            result["delivered_at"] = result["timestamp"]
        
        return result
    
    def render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """
        Render email template with context
        
        Args:
            template_name: Name of template (e.g., 'greeting', 'followup')
            context: Dictionary with template variables (e.g., contact_name, user_name)
            
        Returns:
            Rendered template string
        """
        templates = {
            "greeting": """Hi {contact_name},

I hope this message finds you well!

{custom_message}

Best regards,
{user_name}""",
            
            "followup": """Hi {contact_name},

I wanted to follow up on our previous conversation.

{custom_message}

Looking forward to hearing from you.

Best regards,
{user_name}""",
            
            "quick_note": """Hi {contact_name},

{custom_message}

Thanks,
{user_name}""",
        }
        
        template = templates.get(template_name, templates["quick_note"])
        return template.format(**context)
    
    def get_available_templates(self) -> list:
        """Get list of available email templates"""
        return [
            {"name": "greeting", "description": "Friendly greeting message"},
            {"name": "followup", "description": "Follow-up on previous conversation"},
            {"name": "quick_note", "description": "Short note or reminder"}
        ]


class SMSMessenger:
    """Service for sending SMS messages to contacts"""
    
    def __init__(self):
        self.provider = os.getenv("SMS_PROVIDER", "twilio")
        self.twilio_account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
        self.twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")
        self.twilio_from_phone = os.getenv("TWILIO_FROM_PHONE", "")
    
    def calculate_sms_segments(self, message: str) -> Dict[str, int]:
        """
        Calculate number of SMS segments for a message
        
        Standard SMS: 160 chars = 1 segment
        If > 160: 153 chars per segment (7 chars for concatenation header)
        """
        length = len(message)
        
        if length == 0:
            return {"characters": 0, "segments": 0}
        elif length <= 160:
            return {"characters": length, "segments": 1}
        else:
            # Multi-part SMS uses 153 characters per segment
            segments = (length + 152) // 153  # Round up
            return {"characters": length, "segments": segments}
    
    async def send_sms(
        self,
        phone_number: str,
        body: str,
        contact_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send SMS using configured provider
        
        Args:
            phone_number: Phone number to send to (E.164 format preferred)
            body: SMS message body
            contact_id: Optional contact ID for tracking
            
        Returns:
            Dictionary with success status, message_id, error info
        """
        if not body.strip():
            return {
                "success": False,
                "status": "failed",
                "error": "Message body cannot be empty"
            }
        
        # Calculate segments
        segments_info = self.calculate_sms_segments(body)
        
        # Send via Twilio (placeholder - requires twilio library)
        if self.provider == "twilio":
            if not self.twilio_account_sid or not self.twilio_auth_token:
                return {
                    "success": False,
                    "status": "failed",
                    "error": "Twilio credentials not configured",
                    "segments": segments_info
                }
            
            # Actual Twilio integration would go here
            return {
                "success": False,
                "status": "failed",
                "error": "SMS sending not yet implemented - Twilio library required",
                "segments": segments_info
            }
        
        return {
            "success": False,
            "status": "failed",
            "error": f"Unsupported SMS provider: {self.provider}",
            "segments": segments_info
        }
