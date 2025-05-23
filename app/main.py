from fastapi import FastAPI
from app.routers import ingest
from app.database import Base, engine

app = FastAPI()

Base.metadata.create_all(bind=engine)

app.include_router(ingest.router)