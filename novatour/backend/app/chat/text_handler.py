"""Text chat API endpoint for NovaTour.

Provides a REST fallback for non-voice interactions.
"""

import logging

import boto3
from fastapi import APIRouter
from pydantic import BaseModel

from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"


class ChatResponse(BaseModel):
    reply: str
    session_id: str


@router.post("/chat")
async def chat(request: ChatRequest) -> ChatResponse:
    """Simple text chat endpoint using Nova 2 Lite."""
    try:
        client = boto3.client(
            "bedrock-runtime",
            region_name=settings.aws_default_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )

        response = client.converse(
            modelId=settings.nova_lite_model_id,
            messages=[{"role": "user", "content": [{"text": request.message}]}],
            system=[
                {
                    "text": "You are NovaTour, a helpful AI travel assistant. "
                    "Keep responses concise and helpful."
                }
            ],
            inferenceConfig={"maxTokens": 1024, "temperature": 0.7},
        )

        reply = response["output"]["message"]["content"][0]["text"]
        return ChatResponse(reply=reply, session_id=request.session_id)

    except Exception as e:
        logger.warning(f"Chat API error: {e}")
        return ChatResponse(
            reply="I'm having trouble connecting right now. Please try the voice interface or try again later.",
            session_id=request.session_id,
        )
