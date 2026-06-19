from database.models import Note
from schemas.notes import NoteCreate, NoteUpdate

from .base import CRUDBase


note = CRUDBase[Note, NoteCreate, NoteUpdate](Note)
