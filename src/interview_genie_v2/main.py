import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from interview_genie_v2.api.routes import interview_router, router

load_dotenv()

logging.basicConfig(level=logging.INFO,format="%(asctime)s %(levelname)s %(name)s: %(message)s",)
app = FastAPI(title="Interview Genie")

origins = [o.strip()
    for o in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type"],)

app.include_router(router)
app.include_router(interview_router)

@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}