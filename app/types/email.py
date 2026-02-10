# app/schemas/email.py

from typing import Dict, Optional, List
from pydantic import BaseModel

class EmailHeader(BaseModel):
    name: str
    value: str

class EmailBody(BaseModel):
    text: Optional[str] = None
    html: Optional[str] = None

class EmailPayload(BaseModel):
    subject: Optional[str] = None
    from_email: Optional[str] = None
    to_email: Optional[str] = None
    headers: List[EmailHeader] = []   # list of headers instead of dict
    body: EmailBody
