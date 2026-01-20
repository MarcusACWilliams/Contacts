from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

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
    