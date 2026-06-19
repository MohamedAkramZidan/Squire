from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NoteBase(BaseModel):
    title: str
    description: str
    user_id: int


class NoteCreate(NoteBase):
    pass


class NoteUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    user_id: int | None = None


class Note(NoteBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
