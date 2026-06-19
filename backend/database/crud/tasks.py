from database.models import Task
from schemas.tasks import TaskCreate, TaskUpdate

from .base import CRUDBase


task = CRUDBase[Task, TaskCreate, TaskUpdate](Task)
