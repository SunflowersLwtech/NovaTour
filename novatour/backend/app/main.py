import asyncio
import logging
import time

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.voice.ws_handler import _active_sessions, router as voice_router
from app.chat.text_handler import router as chat_router

logger = logging.getLogger(__name__)

app = FastAPI(title="NovaTour API")


@app.on_event("shutdown")
async def shutdown_event():
    """Gracefully close all active voice sessions on server shutdown."""
    if not _active_sessions:
        return
    logger.info(f"Shutting down {len(_active_sessions)} active session(s)...")
    for session_id, agent in list(_active_sessions.items()):
        try:
            await asyncio.wait_for(agent.stop(), timeout=5.0)
            logger.info(f"Closed session: {session_id}")
        except asyncio.TimeoutError:
            logger.warning(f"Timeout closing session: {session_id}")
        except Exception as e:
            logger.error(f"Error closing session {session_id}: {e}")
    _active_sessions.clear()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(voice_router, prefix="/ws")
app.include_router(chat_router, prefix="/api")


@app.middleware("http")
async def timing_middleware(request: Request, call_next):
    start = time.time()
    response: Response = await call_next(request)
    elapsed = time.time() - start
    logger.info(f"{request.method} {request.url.path} {response.status_code} ({elapsed:.3f}s)")
    response.headers["X-Process-Time"] = f"{elapsed:.3f}"
    return response


@app.get("/health")
async def health():
    from app.tools import ALL_TOOLS

    return {
        "status": "ok",
        "app": settings.app_name,
        "mock_mode": settings.mock_mode,
        "tools": len(ALL_TOOLS),
    }
