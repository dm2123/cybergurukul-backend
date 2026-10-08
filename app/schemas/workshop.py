"""Workshop request/response schemas."""
from pydantic import BaseModel, Field


class WorkshopIn(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    slug: str = Field(min_length=3, max_length=255)
    description: str | None = None
    category: str = "Cybersecurity"
    date: str
    time: str
    duration: str = ""
    mode: str = "Online"
    price: int = 0
    instructor: str = ""
    syllabus: str | None = None
    max_seats: int = 100
    status: str = "upcoming"


class WorkshopOut(WorkshopIn):
    id: int
    registered_count: int = 0

    model_config = {"from_attributes": True}
