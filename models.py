from typing import Literal, Optional, List
from pydantic import BaseModel, Field

class TranscriptMetadata(BaseModel):
    transcript_id: str
    expert_name: str
    role: str
    market: str
    file_path: str

class TranscriptSegment(BaseModel):
    transcript_id: str
    expert_name: str
    market: str
    speaker: str
    text: str
    timestamp: str  # Format "MM:SS" e.g., "00:18"
    start_seconds: int
    segment_index: int

class QuoteEvidence(BaseModel):
    transcript_id: str
    expert_name: str
    market: str
    quote: str
    timestamp: str
    segment_index: int
    speaker: Optional[str] = None

class ExpertGuideAnswer(BaseModel):
    expert_name: str
    market: str
    transcript_id: str
    answer: str
    evidence: List[QuoteEvidence] = Field(default_factory=list)

class GuideQuestionAnswers(BaseModel):
    question_id: str
    question: str
    overall_summary: Optional[str] = None
    answers_by_expert: List[ExpertGuideAnswer] = Field(default_factory=list)

class ThemeOrDisagreement(BaseModel):
    topic: str
    type: Literal["consensus", "disagreement"]
    summary: str
    evidence: List[QuoteEvidence] = Field(default_factory=list)

class ChatMessage(BaseModel):
    question: str
    answer: str
    evidence: List[QuoteEvidence] = Field(default_factory=list)
