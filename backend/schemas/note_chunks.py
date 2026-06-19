from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NoteChunkBase(BaseModel):
    chunk_index: int
    chunk_text: str
    note_id: int
    embedding: list[float] | None = None


class NoteChunkCreate(NoteChunkBase):
    pass


class NoteChunkUpdate(BaseModel):
    chunk_index: int | None = None
    chunk_text: str | None = None
    note_id: int | None = None
    embedding: list[float] | None = None


class NoteChunk(NoteChunkBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
