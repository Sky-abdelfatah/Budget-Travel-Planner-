import os

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator

app = FastAPI(title="Trip Draft Backend - Week 5 Demo")

SYSTEM = (
    "You are Trip Draft, a budget travel assistant for Egypt. "
    "This demo has no dataset: do not state prices or name specific places. "
    "Reply briefly and ask for destination, duration, budget in EGP, and interests."
)


class ChatRequest(BaseModel):
    message: str = Field(..., max_length=2000)

    @field_validator("message")
    @classmethod
    def not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("message must not be empty")
        return value


class ChatResponse(BaseModel):
    reply: str
    model: str
    source: str = "live_model_api"


@app.get("/health")
def health():
    return {
        "status": "ok",
        "api_key_configured": bool(os.getenv("GEMINI_API_KEY")),
        "model_configured": bool(os.getenv("LLM_MODEL")),
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    api_key = os.getenv("GEMINI_API_KEY")
    model = os.getenv("LLM_MODEL")

    if not api_key or not model:
        raise HTTPException(
            status_code=503,
            detail="Model not configured. Set GEMINI_API_KEY and LLM_MODEL.",
        )

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent"
    )

    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM}]},
        "contents": [
            {"role": "user", "parts": [{"text": request.message}]}
        ],
        "generationConfig": {"maxOutputTokens": 1000},
    }

    headers = {
        "x-goog-api-key": api_key,
        "content-type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url,
                json=payload,
                headers=headers,
            )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="The model took too long to respond. Please try again.",
        )
    except httpx.RequestError:
        raise HTTPException(
            status_code=502,
            detail="Could not reach the model service.",
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"Model service returned an error (status {response.status_code}).",
        )

    try:
        parts = response.json()["candidates"][0]["content"]["parts"]
        reply_text = "".join(part.get("text", "") for part in parts)
    except (KeyError, IndexError, TypeError):
        raise HTTPException(
            status_code=502,
            detail="Unexpected response from the model.",
        )

    if not reply_text:
        raise HTTPException(
            status_code=502,
            detail="The model returned an empty response.",
        )

    return ChatResponse(reply=reply_text, model=model)
