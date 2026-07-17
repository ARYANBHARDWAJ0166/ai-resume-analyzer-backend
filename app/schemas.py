from pydantic import BaseModel, Field, EmailStr
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum


# ─── Enums ───────────────────────────────────────────────
class JobSource(str, Enum):
    ALL = "all"
    ADZUNA = "adzuna"
    REMOTE = "remote"

class ExportFormat(str, Enum):
    JSON = "json"
    PDF = "pdf"

class SectionType(str, Enum):
    EXPERIENCE = "experience"
    EDUCATION = "education"
    SKILLS = "skills"
    SUMMARY = "summary"
    PROJECTS = "projects"

class StyleType(str, Enum):
    PROFESSIONAL = "professional"
    CREATIVE = "creative"
    CONCISE = "concise"

class DifficultyLevel(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


# ─── User Schemas ─────────────────────────────────────────
class UserCreateRequest(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)
    full_name: Optional[str] = Field(None, max_length=255)

class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)

class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    full_name: Optional[str] = None
    is_active: bool
    is_recruiter: bool
    created_at: datetime

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ─── Resume Schemas ───────────────────────────────────────
class ResumeResponse(BaseModel):
    id: int
    filename: str
    created_at: datetime
    has_analysis: bool
    skills: List[str] = []

    class Config:
        from_attributes = True

class ResumeDetailResponse(BaseModel):
    id: int
    filename: str
    parsed_data: Optional[Dict[str, Any]] = None
    analysis: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Analysis Schemas ─────────────────────────────────────
class AnalysisRequest(BaseModel):
    resume_id: int = Field(..., gt=0)
    job_description: Optional[str] = Field(None, max_length=10000)

class AnalysisResponse(BaseModel):
    success: bool
    analysis: Dict[str, Any]


# ─── Job Match Schemas ────────────────────────────────────
class JobMatchRequest(BaseModel):
    resume_id: int = Field(..., gt=0)
    job_description: str = Field(..., min_length=10, max_length=10000)
    job_title: Optional[str] = Field("Target Role", max_length=255)
    company: Optional[str] = Field("Target Company", max_length=255)

class JobMatchResponse(BaseModel):
    success: bool
    match: Dict[str, Any]


# ─── Rewrite Schemas ──────────────────────────────────────
class RewriteRequest(BaseModel):
    section_text: str = Field(..., min_length=10, max_length=5000)
    section_type: Optional[SectionType] = SectionType.EXPERIENCE
    style: Optional[StyleType] = StyleType.PROFESSIONAL


# ─── Cover Letter Schemas ─────────────────────────────────
class CoverLetterRequest(BaseModel):
    resume_id: int = Field(..., gt=0)
    job_title: str = Field(..., min_length=2, max_length=255)
    company: str = Field(..., min_length=2, max_length=255)
    job_description: str = Field(..., min_length=10, max_length=10000)


# ─── Skill Gap Schemas ────────────────────────────────────
class SkillGapRequest(BaseModel):
    resume_id: int = Field(..., gt=0)
    job_skills: List[str] = Field(..., min_length=1, max_length=50)


# ─── Roadmap Schemas ──────────────────────────────────────
class RoadmapRequest(BaseModel):
    resume_id: int = Field(..., gt=0)
    target_role: str = Field(..., min_length=2, max_length=255)


# ─── Interview Schemas ────────────────────────────────────
class InterviewQuestionsRequest(BaseModel):
    resume_id: int = Field(..., gt=0)
    job_title: str = Field(..., min_length=2, max_length=255)
    job_description: str = Field(..., min_length=10, max_length=10000)


# ─── GitHub Schemas ───────────────────────────────────────
class GitHubAnalysisRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    user_id: Optional[int] = Field(None, gt=0)


# ─── Chat Schemas ─────────────────────────────────────────
class ChatRequest(BaseModel):
    resume_id: int = Field(..., gt=0)
    message: str = Field(..., min_length=1, max_length=2000)

class ChatResponse(BaseModel):
    success: bool
    response: str
    chat_id: int


# ─── Analytics Schemas ────────────────────────────────────
class AnalyticsTrackRequest(BaseModel):
    user_id: Optional[int] = Field(None, gt=0)
    event_type: str = Field(..., min_length=1, max_length=100)
    event_data: Optional[Dict[str, Any]] = None


# ─── Version Schemas ──────────────────────────────────────
class SaveVersionRequest(BaseModel):
    resume_id: int = Field(..., gt=0)
    content: str = Field(..., min_length=1)
    changes: Optional[Dict[str, Any]] = None


# ─── Bulk Analysis Schemas ────────────────────────────────
class BulkAnalysisRequest(BaseModel):
    resume_ids: List[int] = Field(..., min_length=1, max_length=10)
    job_description: Optional[str] = Field(None, max_length=10000)


# ─── Compare Schemas ──────────────────────────────────────
class CompareResumesRequest(BaseModel):
    resume_id_1: int = Field(..., gt=0)
    resume_id_2: int = Field(..., gt=0)


# ─── Job Search Schemas ───────────────────────────────────
class JobSearchRequest(BaseModel):
    resume_id: int = Field(..., gt=0)
    job_title: Optional[str] = Field(None, max_length=255)
    location: Optional[str] = Field(None, max_length=255)
    limit: Optional[int] = Field(10, ge=1, le=50)
    source: Optional[JobSource] = JobSource.ALL

class JobListing(BaseModel):
    title: str
    company: str
    location: str
    description: str
    url: str
    source: str
    posted_at: str
    apply_url: str
    match_score: Optional[int] = None
    match_percentage: Optional[str] = None

class JobSearchResponse(BaseModel):
    success: bool
    jobs: List[JobListing]
    total_found: int
    search_query: str


# ─── Save Job Schemas ─────────────────────────────────────
class SaveJobRequest(BaseModel):
    resume_id: int = Field(..., gt=0)
    job_title: str = Field(..., min_length=1, max_length=255)
    company: str = Field(..., min_length=1, max_length=255)
    job_url: str = Field(..., min_length=1, max_length=500)
    match_score: Optional[int] = Field(None, ge=0, le=100)
    location: Optional[str] = Field(None, max_length=255)

class SavedJobResponse(BaseModel):
    id: int
    job_title: str
    company: str
    job_url: Optional[str] = None
    location: Optional[str] = None
    match_score: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True