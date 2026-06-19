from pydantic import BaseModel


class CommandRequest(BaseModel):
    text: str
    user_id: int | None = None