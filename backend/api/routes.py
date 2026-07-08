from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import services.nlu as nlu

from database import get_db
from schemas.request import CommandRequest
from schemas.response import PredictResponse

from postprocess import process
from services.decide import decide
from services.executor import execute_intent
from response import generate_response

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
    raw["text"] = req.text

    result = process(raw)

    decision = decide(result, user_id=req.user_id)
    execution = None

    if decision.get("decision") == "EXECUTE":
        execute_data = decision.get("data", result)
        execution = execute_intent(db, execute_data, req.user_id)
        if execution and execution.get("status") == "CLARIFY":
            from services.state_manager import save_session
            session = {
                "status": "waiting_for_entity",
                "pending_command": {
                    "action": execute_data.get("action"),
                    "object": execute_data.get("object"),
                    "fields": execute_data.get("fields", {}),
                },
            }
            if "matches" in execution:
                session["waiting_for"] = "TARGET_SELECTION"
                session["matches"] = execution["matches"]
            elif "missing" in execution:
                session["waiting_for"] = execution["missing"][0]
            
            save_session(req.user_id, session)

    response_text = generate_response(
        decision=decision,
        execution=execution,
        original_text=req.text,
    )

    return {
        "result": result,
        "decision": decision,
        "execution": execution,
        "response": response_text,
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

from database.models import Task, Meeting, Note, Progress

@router.get("/api/tasks")
def get_tasks(user_id: int, db: Session = Depends(get_db)):
    tasks = db.query(Task).filter(Task.user_id == user_id).all()
    from services.execution.helpers import serialize
    return [serialize(t) for t in tasks]

@router.get("/api/meetings")
def get_meetings(user_id: int, db: Session = Depends(get_db)):
    meetings = db.query(Meeting).filter(Meeting.user_id == user_id).all()
    from services.execution.helpers import serialize
    return [serialize(m) for m in meetings]

@router.get("/api/notes")
def get_notes(user_id: int, db: Session = Depends(get_db)):
    notes = db.query(Note).filter(Note.user_id == user_id).all()
    from services.execution.helpers import serialize
    return [serialize(n) for n in notes]

@router.get("/api/progress")
def get_progress(user_id: int, db: Session = Depends(get_db)):
    progress = db.query(Progress).filter(Progress.user_id == user_id).all()
    from services.execution.helpers import serialize
    return [serialize(p) for p in progress]
