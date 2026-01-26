from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, field_validator

# Pydantic model for Contact
class Contact(BaseModel):
    first: str
    last: str
    email: List[str] = []
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
    @field_validator("email", mode='before')
    @classmethod
    def validate_email(cls, value):
        if isinstance(value, list):
            validated_emails = []
            for email in value:
                cleaned = email.strip()
                if cleaned and ("@" not in cleaned or "." not in cleaned):
                    raise ValueError(f"Invalid email address: {cleaned}")
                if cleaned:
                    validated_emails.append(cleaned)
            return validated_emails
        return value
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
    
