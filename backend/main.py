from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from services.decide import decide
import services.nlu as nlu
from postprocess import process
from config.settings import settings
from schemas.request import CommandRequest

app = FastAPI(title="Squire NLU")

@app.on_event("startup")
def startup():
    nlu.load(settings.model_path)

@app.post("/predict")
def predict(req: CommandRequest):
    if not req.text.strip():
        raise HTTPException(400, "text is empty")
    raw    = nlu.predict(req.text)
    result = process(raw)
    decision = decide(result)
    return {"result": result, "decision": decision}

@app.post("/debug/raw")
def debug_raw(req: CommandRequest):
    if not req.text.strip():
        raise HTTPException(400, "text is empty")
    return nlu.predict(req.text)

@app.get("/debug/model")
def debug_model():
    return nlu.debug_info()

@app.get("/health")
def health():
    return {"status": "ok"}