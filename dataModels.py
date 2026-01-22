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
