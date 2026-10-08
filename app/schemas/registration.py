"""Registration request/response schemas."""
from datetime import datetime

from pydantic import BaseModel


class RegistrationOut(BaseModel):
    id: int
    reg_id: str
    user_id: int
    workshop_id: int
    status: str
    registered_at: datetime

    model_config = {"from_attributes": True}


class RegistrationDetailOut(RegistrationOut):
    user_name: str = ""
    user_email: str = ""
    workshop_title: str = ""
