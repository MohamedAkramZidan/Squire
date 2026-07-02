from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict

from database.models import TaskStatus


class TaskBase(BaseModel):
    title: str
    task_date: date | None = None
    task_time: time | None = None
    status: TaskStatus = TaskStatus.pending
    user_id: int


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: str | None = None
    task_date: date | None = None
    task_time: time | None = None
    status: TaskStatus | None = None
    user_id: int | None = None


class Task(TaskBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    embedding: list[float] | None = None
    created_at: datetime
    updated_at: datetime
