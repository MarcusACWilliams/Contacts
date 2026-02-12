from typing import List, Optional, Literal
from datetime import datetime
from pydantic import BaseModel, field_validator
from classes.emails import emailaddress

# Pydantic model for Message
class Message(BaseModel):
    _id: Optional[str] = None
    _contact_id: str
    type: Literal['email', 'sms']
    direction: Literal['sent', 'received'] = 'sent'
    recipient: str  # email address or phone number
    subject: Optional[str] = None  # only for email
    body: str
    status: Literal['draft', 'sending', 'sent', 'failed', 'delivered'] = 'draft'
    timestamp: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    error_message: Optional[str] = None
    metadata: Optional[dict] = None

    @field_validator("body")
    @classmethod
    def validate_body(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Message body cannot be empty")
        return cleaned

    @field_validator("recipient")
    @classmethod
    def validate_recipient(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Recipient cannot be empty")
        return cleaned

# Pydantic model for EmailAddress
class EmailAddress(BaseModel):
    _id: Optional[bytes] = None
    _contact_id: Optional[bytes] = None
    address: str
    type: Optional[str] = None

# Pydantic model for Contact
class Contact(BaseModel):
    _id: Optional[bytes] = None
    first: str
    last: str
    emails: List[EmailAddress] = []
    phone: List[str] = []
    address: Optional[str] = None
    social_media: Optional[dict] = None
    notes: Optional[str] = None
    birthday: Optional[datetime] = None

    @field_validator("first", "last")
    @classmethod
    def validate_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Name cannot be empty")
        if not all(ch.isalpha() or ch in {" ", "-", "'"} for ch in cleaned):
            raise ValueError("Name must only contain letters, spaces, hyphens, or apostrophes")
        return cleaned
    @field_validator("emails", mode='before')
    @classmethod
    def validate_emails(cls, value):
        if isinstance(value, list) and value:
            # If it's already a list of EmailAddress objects, return as-is
            if isinstance(value[0], EmailAddress):
                return value
            # If it's a list of strings or dicts, convert to EmailAddress objects
            validated_emails = []
            for item in value:
                if isinstance(item, str):
                    cleaned = item.strip()
                    if cleaned:
                        try:
                            # Use emailaddress class for validation
                            email_obj_validator = emailaddress(cleaned)
                            # If validation passes, create EmailAddress object
                            email_obj = EmailAddress(
                                _id=b'',  # Placeholder, will be set in endpoint
                                _contact_id=b'',  # Placeholder, will be set in endpoint
                                address=email_obj_validator.address,
                                type='home'
                            )
                            validated_emails.append(email_obj)
                        except ValueError as e:
                            raise ValueError(f"Invalid email address: {cleaned} - {str(e)}")
                elif isinstance(item, dict):
                    # Already a dict/object, validate address with emailaddress class
                    if 'address' in item:
                        try:
                            email_obj_validator = emailaddress(item['address'])
                            validated_emails.append(EmailAddress(**item))
                        except ValueError as e:
                            raise ValueError(f"Invalid email address in dict: {item.get('address')} - {str(e)}")
            return validated_emails
        return value if value else []
    @field_validator("phone", mode='before')
    @classmethod
    def validate_phone(cls, value):
        if isinstance(value, list):
            validated_phones = []
            for phone in value:
                cleaned = phone.strip()
                if cleaned and not all(ch.isdigit() or ch in {"-", "(", ")", " "} for ch in cleaned):
                    raise ValueError("Phone number must only contain digits, spaces, hyphens, or parentheses")
                if cleaned:
                    validated_phones.append(cleaned)
            return validated_phones
        return value
    
