from datetime import datetime

from pydantic import BaseModel, ConfigDict

from database.models import ProgressStatus


class ProgressBase(BaseModel):
    title: str
    status: ProgressStatus = ProgressStatus.not_started
    field: str | None = None
    value: int | None = None
    user_id: int


class ProgressCreate(ProgressBase):
    pass


class ProgressUpdate(BaseModel):
    title: str | None = None
    status: ProgressStatus | None = None
    field: str | None = None
    value: int | None = None
    user_id: int | None = None


class Progress(ProgressBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    embedding: list[float] | None = None
    created_at: datetime
    updated_at: datetime
