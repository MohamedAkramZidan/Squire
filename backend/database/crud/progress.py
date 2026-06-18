from database.models import Progress
from schemas.progress import ProgressCreate, ProgressUpdate

from .base import CRUDBase


progress = CRUDBase[Progress, ProgressCreate, ProgressUpdate](Progress)
