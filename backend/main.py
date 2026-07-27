"""
FastAPI application entry.
"""

import asyncio
import json
import os
import sys

from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Ensure the backend package can be imported when the app starts from repo root.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.config import settings
from backend.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize local demo data on startup."""
    print(f"[{settings.APP_NAME}] starting...")
    init_db()

    from backend.seed_data import seed_all

    seed_all()
    print(f"[{settings.APP_NAME}] ready")
    yield
    print(f"[{settings.APP_NAME}] shutdown")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from backend.api.cars import router as car_router
from backend.api.chat import router as chat_router
from backend.api.customers import router as customer_router
from backend.api.finance import router_appointments, router_finance, router_inventory
from backend.api.knowledge import router as knowledge_router

app.include_router(chat_router)
app.include_router(customer_router)
app.include_router(car_router)
app.include_router(router_finance)
app.include_router(router_inventory)
app.include_router(router_appointments)
app.include_router(knowledge_router)


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "llm_provider": settings.LLM_PROVIDER,
        "llm_model": settings.OPENAI_MODEL,
    }


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """Stream one Agent reply over WebSocket."""
    await websocket.accept()

    from backend.api.chat import process_chat_message
    from backend.database import SessionLocal
    from backend.schemas.schemas import ChatRequest

    try:
        while True:
            raw_message = await websocket.receive_text()
            payload = json.loads(raw_message)
            req = ChatRequest(
                session_id=payload.get("session_id", ""),
                customer_id=payload.get("customer_id", ""),
                message=payload.get("message", ""),
            )

            await websocket.send_json({"type": "start"})

            db = SessionLocal()
            try:
                response = await run_in_threadpool(process_chat_message, req, db)
            finally:
                db.close()

            for chunk in _chunk_text(response.reply):
                await websocket.send_json({"type": "delta", "content": chunk})
                await asyncio.sleep(0.035)

            await websocket.send_json({
                "type": "done",
                "data": response.model_dump(),
            })
    except WebSocketDisconnect:
        return
    except Exception as exc:
        print(f"[WebSocket Chat Error] {exc}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": "AI 回复生成失败，请稍后再试。",
            })
        except RuntimeError:
            pass


def _chunk_text(text: str, size: int = 8):
    """Split text into small chunks for readable streaming."""
    text = text or ""
    for index in range(0, len(text), size):
        yield text[index:index + size]


frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
