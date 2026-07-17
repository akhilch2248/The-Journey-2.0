from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class DevLoginRequest(BaseModel):
    id_token: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    provider: str
    email: Optional[str] = None
    display_name: Optional[str] = None
    created_at: datetime
