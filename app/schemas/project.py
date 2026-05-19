from datetime import datetime
from pydantic import BaseModel


class ProjectCreate(BaseModel):
    title: str
    description: str | None = None


class ProjectRead(BaseModel):
    id: int
    title: str
    description: str | None
    owner_id: int
    created_at: datetime

    model_config = {"from_attributes": True}
