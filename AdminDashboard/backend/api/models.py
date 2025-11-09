from typing import List, Optional

from pydantic import BaseModel, Field, constr, validator


class PaginationQuery(BaseModel):
    limit: int = Field(default=20, ge=1, le=100)
    cursor: Optional[str]


class AskRequest(BaseModel):
    callId: constr(strip_whitespace=True, min_length=3)
    question: constr(strip_whitespace=True, min_length=3, max_length=500)


class MessageModel(BaseModel):
    callId: str
    role: str
    text: str
    ts: str
    turn: int


class CallModel(BaseModel):
    callId: str
    agentId: str
    header: str
    summary: Optional[str]
    sentiment: Optional[str]
    startedAt: str
    endedAt: Optional[str]
    durationSec: Optional[int]
    riskFlags: Optional[List[dict]]
    tags: Optional[List[str]]
    score: Optional[float]
