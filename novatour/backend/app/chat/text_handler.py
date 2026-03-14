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

        from app.lod.prompt_builder import CHAT_SYSTEM_PROMPT

        response = client.converse(
            modelId=settings.nova_lite_model_id,
            messages=[{"role": "user", "content": [{"text": request.message}]}],
            system=[{"text": CHAT_SYSTEM_PROMPT}],
            inferenceConfig={"maxTokens": 1024, "temperature": 0.7},
        )

        reply = response["output"]["message"]["content"][0]["text"]
        return ChatResponse(reply=reply, session_id=request.session_id)

    except Exception as e:
        logger.warning(f"Chat API error: {type(e).__name__}: {e}")

        error_name = type(e).__name__
        if "Throttling" in error_name or "throttl" in str(e).lower():
            detail = (
                "[Throttled] The AI model has reached its daily token limit. "
                "Please wait a while before trying again, or check your AWS Bedrock quotas."
            )
        elif "Credential" in error_name or "Access" in error_name:
            detail = (
                "[Auth Error] AWS credentials are missing or invalid. "
                "Please check your .env file for AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY."
            )
        else:
            detail = (
                f"[{error_name}] I'm temporarily unable to connect to travel services. "
                "Please try again in a moment."
            )

        return ChatResponse(reply=detail, session_id=request.session_id)
