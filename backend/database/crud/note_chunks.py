from database.models import NoteChunk
from schemas.note_chunks import NoteChunkCreate, NoteChunkUpdate

from .base import CRUDBase


note_chunk = CRUDBase[NoteChunk, NoteChunkCreate, NoteChunkUpdate](NoteChunk)
