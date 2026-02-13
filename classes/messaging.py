"""
Messaging service for sending emails and SMS to contacts.
Supports multiple providers (SendGrid, SMTP, AWS SES for email; Twilio, AWS SNS for SMS)
Includes mobile-native support for SMS and voice calls using standard URI schemes.
"""

import os
import smtplib
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional, Dict, Any
import asyncio
from functools import wraps
from urllib.parse import quote
from classes.emails import emailaddress


def async_wrap(func):
    """Wrapper to run synchronous functions in async context"""
    @wraps(func)
    async def run(*args, **kwargs):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))
    return run


class PhoneNumber:
    """
    Represents a phone number with parsing, validation, and formatting capabilities.
    Provides methods to validate, normalize, and generate mobile URIs for calls/SMS.
    """
    
    # Phone number regex patterns for various formats
    # Matches E.164 format and common patterns
    PHONE_PATTERN = re.compile(
        r'^\+?1?\s*\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})$'
    )
    E164_PATTERN = re.compile(r'^\+[1-9]\d{1,14}$')
    
    def __init__(self, phone: str):
        """Initialize phone number with validation."""
        if not phone:
            raise ValueError("Phone number cannot be empty")
        
        # Normalize the phone number
        phone = phone.strip()
        self._raw = phone
        self._normalized = self._normalize(phone)
        self._e164 = self._to_e164(phone)
    
    def _normalize(self, phone: str) -> str:
        """Normalize phone number to common format."""
        # Remove all non-digit characters except + at start
        normalized = phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "").replace(".", "")
        
        # If no country code, add US +1
        if not normalized.startswith("+"):
            if normalized.startswith("1") and len(normalized) == 11:
                normalized = "+" + normalized
            elif len(normalized) == 10:
                normalized = "+1" + normalized
            else:
                normalized = "+" + normalized
        
        return normalized
    
    def _to_e164(self, phone: str) -> str:
        """Convert to E.164 format (+1234567890)."""
        # Remove all non-digit characters
        digits_only = re.sub(r'\D', '', phone)
        
        # Handle US numbers without country code
        if len(digits_only) == 10 and not phone.startswith("+"):
            digits_only = "1" + digits_only
        
        # Ensure + prefix
        if not digits_only.startswith("+"):
            if not digits_only.startswith("1") or len(digits_only) != 11:
                # Try to guess country code (default to 1 for North America)
                if len(digits_only) == 10:
                    digits_only = "1" + digits_only
            e164 = "+" + digits_only
        else:
            e164 = digits_only
        
        return e164
    
    @property
    def raw(self) -> str:
        """Get the raw phone number as provided."""
        return self._raw
    
    @property
    def normalized(self) -> str:
        """Get the normalized phone number."""
        return self._normalized
    
    @property
    def e164(self) -> str:
        """Get the E.164 formatted phone number (+1234567890)."""
        return self._e164
    
    def is_valid(self) -> bool:
        """Validate the phone number format."""
        return bool(self.PHONE_PATTERN.match(self._raw))
    
    def get_call_uri(self) -> str:
        """
        Generate URI for making voice calls on mobile devices.
        Returns: tel:+1234567890
        """
        return f"tel:{self._e164}"
    
    def get_sms_uri(self, message: str = "") -> str:
        """
        Generate URI for sending SMS on mobile devices.
        Returns: sms:+1234567890?body=message
        """
        uri = f"sms:{self._e164}"
        if message:
            encoded_message = quote(message)
            uri += f"?body={encoded_message}"
        return uri
    
    def __str__(self) -> str:
        """Return the normalized phone number."""
        return self._normalized
    
    def __repr__(self) -> str:
        """Return repr of phone number."""
        return f"PhoneNumber('{self._raw}')"
    
    def __eq__(self, other) -> bool:
        """Compare phone numbers."""
        if isinstance(other, PhoneNumber):
            return self._e164 == other._e164
        elif isinstance(other, str):
            try:
                other_phone = PhoneNumber(other)
                return self._e164 == other_phone._e164
            except ValueError:
                return False
        return False


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
    
    def validate_phone_number(self, phone: str) -> bool:
        """Validate phone number using PhoneNumber class"""
        try:
            PhoneNumber(phone)
            return True
        except ValueError:
            return False
    
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
    
    def get_mobile_sms_uri(self, phone_number: str, message: str = "") -> Dict[str, Any]:
        """
        Generate mobile-compatible SMS URI for native functionality.
        Allows users to send SMS directly from their mobile device.
        
        Args:
            phone_number: Phone number to send SMS to
            message: Optional message body
            
        Returns:
            Dictionary with URI, segments info, and device compatibility
        """
        if not self.validate_phone_number(phone_number):
            return {
                "success": False,
                "error": "Invalid phone number",
                "uri": None
            }
        
        phone = PhoneNumber(phone_number)
        segments_info = self.calculate_sms_segments(message)
        
        return {
            "success": True,
            "uri": phone.get_sms_uri(message),
            "phone_number": phone.e164,
            "segments": segments_info,
            "device_compatibility": {
                "ios": True,
                "android": True,
                "web": False  # URI scheme only works on native
            },
            "type": "native_sms"
        }
    
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
        
        # Validate phone number
        if not self.validate_phone_number(phone_number):
            return {
                "success": False,
                "status": "failed",
                "error": "Invalid phone number"
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


class VoiceCallMessenger:
    """Service for initiating voice calls to contacts via mobile devices"""
    
    def __init__(self):
        self.provider = os.getenv("VOICE_PROVIDER", "twilio")
        self.twilio_account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
        self.twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")
        self.twilio_from_phone = os.getenv("TWILIO_FROM_PHONE", "")
    
    def validate_phone_number(self, phone: str) -> bool:
        """Validate phone number using PhoneNumber class"""
        try:
            PhoneNumber(phone)
            return True
        except ValueError:
            return False
    
    def get_mobile_call_uri(self, phone_number: str) -> Dict[str, Any]:
        """
        Generate mobile-compatible URI for making voice calls.
        Allows users to call directly from their mobile device using native dialer.
        
        Args:
            phone_number: Phone number to call
            
        Returns:
            Dictionary with URI, phone number, and device compatibility
        """
        if not self.validate_phone_number(phone_number):
            return {
                "success": False,
                "error": "Invalid phone number",
                "uri": None
            }
        
        phone = PhoneNumber(phone_number)
        
        return {
            "success": True,
            "uri": phone.get_call_uri(),
            "phone_number": phone.e164,
            "device_compatibility": {
                "ios": True,
                "android": True,
                "web": False  # URI scheme only works on native mobile
            },
            "type": "native_voice_call"
        }
    
    async def initiate_call(
        self,
        phone_number: str,
        contact_id: Optional[str] = None,
        contact_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Initiate a voice call to a phone number.
        On mobile devices, returns a URI to trigger the native dialer.
        On server-side with Twilio, would initiate the call programmatically.
        
        Args:
            phone_number: Phone number to call
            contact_id: Optional contact ID for tracking
            contact_name: Optional contact name for reference
            
        Returns:
            Dictionary with call initiation details and/or URI for mobile
        """
        if not self.validate_phone_number(phone_number):
            return {
                "success": False,
                "status": "failed",
                "error": "Invalid phone number"
            }
        
        phone = PhoneNumber(phone_number)
        
        # For mobile devices, return the URI
        result = {
            "success": True,
            "phone_number": phone.e164,
            "contact_name": contact_name,
            "mobile_uri": phone.get_call_uri(),
            "device_compatibility": {
                "ios": True,
                "android": True,
                "web": False
            },
            "type": "native_voice_call",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # If server-side Twilio integration is needed:
        if self.provider == "twilio":
            if not self.twilio_account_sid or not self.twilio_auth_token:
                result["server_call_available"] = False
                result["server_call_error"] = "Twilio credentials not configured"
            else:
                result["server_call_available"] = False
                result["server_call_error"] = "Twilio voice call integration not yet implemented"
        
        return result
    
    def get_call_request_link(self, phone_number: str, callback_number: Optional[str] = None) -> str:
        """
        Generate a clickable link for mobile devices that initiates a call.
        Can be embedded in HTML or sent via SMS.
        
        Args:
            phone_number: Phone number to call
            callback_number: Optional number for callbacks
            
        Returns:
            Clickable tel: URI
        """
        try:
            phone = PhoneNumber(phone_number)
            return phone.get_call_uri()
        except ValueError:
            return ""
