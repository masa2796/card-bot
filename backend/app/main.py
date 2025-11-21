from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .models import ChatRequest, ChatResponse
from .services import chat as run_chat

app = FastAPI(title="gamechat-ai", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat_endpoint(payload: ChatRequest):
    try:
        return await run_chat(payload.message, payload.history or [])
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - FastAPI will surface clean 500 JSON
        raise HTTPException(status_code=500, detail=f"Failed to generate answer: {exc}") from exc
