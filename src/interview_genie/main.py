from fastapi import FastAPI
from interview_genie.api.routes import router

app = FastAPI(title="Interview Genie")
app.include_router(router, prefix="/api")