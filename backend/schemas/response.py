from pydantic import BaseModel
from typing import Dict, Any


class PredictResponse(BaseModel):
    result: Dict[str, Any]
    decision: Dict[str, Any]
    execution: Dict[str, Any] | None = None
    response: str | None = None