from fastapi import APIRouter
from pydantic import BaseModel
from backend.llm.openai_client import OpenAIClient

router = APIRouter()

openai_client = OpenAIClient()

class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    reply = openai_client.ask(request.message)
    return ChatResponse(reply=reply)
