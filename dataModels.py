from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr
from beanie import Document

# Pydantic models for embedded data
class Email(BaseModel):
    address: EmailStr
    label: str = "personal"

class Phone(BaseModel):
    number: str
    label: str = "mobile"

class Address(BaseModel):
    street: str
    city: str
    state: str
    zip_code: str
    country: str = "USA"
    label: str = "home"

# Beanie Document for the MongoDB collection
class Contact(Document):
    # Indexed marks the fields for faster querying
    first_name: str
    last_name: str
    
    emails: List[Email] = []
    phones: List[Phone] = []
    addresses: List[Address] = []
    
    social_media: Optional[dict] = None
    notes: Optional[str] = None
    birthday: Optional[datetime] = None
    
    created_at: datetime = datetime.utcnow()
    
