from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class AIAnalysisResult(BaseModel):
    analysis: str = ""
    keywords: List[str] = Field(default_factory=list)
    
class ContentGenerationRequest(BaseModel):
    topic: str
    style: str = "news"
    length: int = 500

class ContentGenerationResult(BaseModel):
    content: str = ""

class AutoSummaryRequest(BaseModel):
    text: str
    max_length: int = 200

class AutoSummaryResult(BaseModel):
    summary: str = ""

class TagRecommendationRequest(BaseModel):
    text: str

class TagRecommendationResult(BaseModel):
    tags: List[str] = Field(default_factory=list)

class QualityEvaluationRequest(BaseModel):
    text: str

class QualityEvaluationResult(BaseModel):
    score: float = 0.0
    feedback: str = ""

class AIReviewResult(BaseModel):
    result: str = ""
    comment: str = ""

class TopicPlanningAnalysisResult(BaseModel):
    suggestions: List[str] = Field(default_factory=list)
