from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, field_validator

# Pydantic model for EmailAddress
class EmailAddress(BaseModel):
    _id: Optional[bytes] = None
    _contact_id: Optional[bytes] = None
    address: str
    type: Optional[str] = None

# Pydantic model for Contact
class Contact(BaseModel):
    _id: bytes
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
                        if "@" not in cleaned or "." not in cleaned:
                            raise ValueError(f"Invalid email address: {cleaned}")
                        # Create EmailAddress object with placeholder IDs (will be set in createContact)
                        email_obj = EmailAddress(
                            _id=b'',  # Placeholder, will be set in endpoint
                            _contact_id=b'',  # Placeholder, will be set in endpoint
                            address=cleaned,
                            type='home'
                        )
                        validated_emails.append(email_obj)
                elif isinstance(item, dict):
                    # Already a dict/object, validate and convert
                    if 'address' in item:
                        validated_emails.append(EmailAddress(**item))
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
    
