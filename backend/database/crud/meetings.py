from database.models import Meeting
from schemas.meetings import MeetingCreate, MeetingUpdate

from .base import CRUDBase


meeting = CRUDBase[Meeting, MeetingCreate, MeetingUpdate](Meeting)
