from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import chat, db_check, projects

app = FastAPI(title="ChatbotAI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])
app.include_router(db_check.router, prefix="/api/v1", tags=["db"])
app.include_router(projects.router, prefix="/api/v1/projects", tags=["projects"])




@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
