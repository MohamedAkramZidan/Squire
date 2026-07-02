from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict

from database.models import MeetingStatus


class MeetingBase(BaseModel):
    title: str
    meeting_date: date
    meeting_time: time | None = None
    status: MeetingStatus = MeetingStatus.scheduled
    person: str | None = None
    location: str | None = None
    user_id: int


class MeetingCreate(MeetingBase):
    pass


class MeetingUpdate(BaseModel):
    title: str | None = None
    meeting_date: date | None = None
    meeting_time: time | None = None
    status: MeetingStatus | None = None
    person: str | None = None
    location: str | None = None
    user_id: int | None = None


class Meeting(MeetingBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    embedding: list[float] | None = None
    created_at: datetime
    updated_at: datetime
