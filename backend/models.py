"""Pydantic models for the voice agent."""
from pydantic import BaseModel
from typing import Optional
from enum import Enum
from datetime import datetime


class LeadStatus(str, Enum):
    NEW = "new"
    IN_PROGRESS = "in_progress"
    HOT = "hot"
    WARM = "warm"
    COLD = "cold"
    CONVERTED = "converted"


class Language(str, Enum):
    ENGLISH = "english"
    HINDI = "hindi"
    HINGLISH = "hinglish"
    TAMIL = "tamil"
    TELUGU = "telugu"
    MARATHI = "marathi"
    GUJARATI = "gujarati"
    BENGALI = "bengali"


class Lead(BaseModel):
    id: Optional[int] = None
    name: str
    phone: str
    language: Language = Language.ENGLISH
    status: LeadStatus = LeadStatus.NEW
    score: int = 0  # 0-100
    source: str = "manual"
    created_at: Optional[str] = None


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: Optional[str] = None
    language_detected: Optional[str] = None


class ConversationRequest(BaseModel):
    lead_id: int
    message: str


class ConversationResponse(BaseModel):
    reply: str
    language_detected: str
    is_call_ended: bool = False
    lead_status: Optional[LeadStatus] = None
    score: Optional[int] = None


class CallSummary(BaseModel):
    lead_id: int
    lead_name: str
    duration_seconds: int
    messages_count: int
    language_used: str
    objections_raised: list[str]
    topics_covered: list[str]
    interest_score: LeadStatus
    score_numeric: int
    recommended_action: str
    summary_text: str
    created_at: Optional[str] = None


class LeadBatchUpload(BaseModel):
    leads: list[Lead]


class DashboardStats(BaseModel):
    total_leads: int
    contacted: int
    hot: int
    warm: int
    cold: int
    converted: int
    avg_score: float
    conversion_rate: float
