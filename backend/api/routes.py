from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import services.nlu as nlu

from database import get_db
from schemas.request import CommandRequest
from schemas.response import PredictResponse

from postprocess import process
from services.decide import decide
from services.executor import execute_intent

router = APIRouter()


@router.post(
    "/predict",
    response_model=PredictResponse
)
def predict(req: CommandRequest, db: Session = Depends(get_db)):

    if not req.text.strip():
        raise HTTPException(
            status_code=400,
            detail="text is empty"
        )

    raw = nlu.predict(req.text)

    result = process(raw)
    result["text"] = req.text

    decision = decide(result)
    execution = None

    if decision.get("decision") == "EXECUTE":
        execution = execute_intent(db, result, req.user_id)

    return {
        "result": result,
        "decision": decision,
        "execution": execution,
    }


@router.post("/debug/raw")
def debug_raw(req: CommandRequest):

    if not req.text.strip():
        raise HTTPException(
            status_code=400,
            detail="text is empty"
        )

    return nlu.predict(req.text)


@router.get("/debug/model")
def debug_model():
    return nlu.debug_info()


@router.get("/health")
def health():
    return {"status": "ok"}
