from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import services.nlu as nlu
from api import routes
from config.settings import settings
from database import init_db

app = FastAPI(title="Squire")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup():
    if settings.create_tables_on_startup:
        init_db()
    nlu.load(settings.model_path)

app.include_router(routes.router)