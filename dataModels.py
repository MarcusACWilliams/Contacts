from pydantic import BaseModel
from typing import List # Use list in modern Python

class Contact(BaseModel):
    first: str
    last: str
    middle: str | None = None # or list[str] in Python 3.9+
    phone: str
    email: list[str]
    address: str | None = None  
    