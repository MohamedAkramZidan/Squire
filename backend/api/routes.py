from fastapi import APIRouter, HTTPException

import services.nlu as nlu

from schemas.request import CommandRequest
from schemas.response import PredictResponse

from postprocess import process
from services.decide import decide

router = APIRouter()


@router.post(
    "/predict",
    response_model=PredictResponse
)
def predict(req: CommandRequest):

    if not req.text.strip():
        raise HTTPException(
            status_code=400,
            detail="text is empty"
        )

    raw = nlu.predict(req.text)

    result = process(raw)

    decision = decide(result)

    return {
        "result": result,
        "decision": decision
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