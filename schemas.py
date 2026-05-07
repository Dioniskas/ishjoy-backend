from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Any
from datetime import datetime
from models import UserRole, JobType, JobStatus, ApplicationStatus


# ─── AUTH ───────────────────────────────────────────────
class SendOTPRequest(BaseModel):
    phone: str = Field(..., example="+998901234567")

class VerifyOTPRequest(BaseModel):
    phone: str
    code: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"

class UserOut(BaseModel):
    id: int
    phone: str
    email: Optional[str]
    full_name: Optional[str]
    role: UserRole
    avatar_url: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    full_name: Optional[str]
    email: Optional[EmailStr]
    avatar_url: Optional[str]


# ─── COMPANY ────────────────────────────────────────────
class CompanyCreate(BaseModel):
    name: str
    description: Optional[str]
    website: Optional[str]
    city: Optional[str]
    industry: Optional[str]
    size: Optional[str]

class CompanyOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    logo_url: Optional[str]
    website: Optional[str]
    city: Optional[str]
    industry: Optional[str]
    size: Optional[str]
    is_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ─── JOBS ───────────────────────────────────────────────
class JobCreate(BaseModel):
    title: str
    description: str
    requirements: Optional[str]
    responsibilities: Optional[str]
    salary_min: Optional[float]
    salary_max: Optional[float]
    currency: str = "UZS"
    job_type: JobType = JobType.office
    city: Optional[str] = "Ташкент"
    experience_years: int = 0
    skills: List[str] = []
    category: Optional[str]
    is_hot: bool = False

class JobUpdate(BaseModel):
    title: Optional[str]
    description: Optional[str]
    salary_min: Optional[float]
    salary_max: Optional[float]
    job_type: Optional[JobType]
    status: Optional[JobStatus]
    is_hot: Optional[bool]

class JobOut(BaseModel):
    id: int
    title: str
    description: str
    requirements: Optional[str]
    salary_min: Optional[float]
    salary_max: Optional[float]
    currency: str
    job_type: JobType
    city: Optional[str]
    experience_years: int
    skills: List[str]
    category: Optional[str]
    status: JobStatus
    is_hot: bool
    views_count: int
    company: CompanyOut
    created_at: datetime

    class Config:
        from_attributes = True

class JobListOut(BaseModel):
    items: List[JobOut]
    total: int
    page: int
    per_page: int


# ─── RESUME ─────────────────────────────────────────────
class ExperienceItem(BaseModel):
    company: str
    position: str
    start_date: str
    end_date: Optional[str] = "по настоящее время"
    description: Optional[str]

class EducationItem(BaseModel):
    institution: str
    degree: str
    year: str

class LanguageItem(BaseModel):
    language: str
    level: str  # A1-C2 или Родной

class ResumeCreate(BaseModel):
    title: str
    summary: Optional[str]
    desired_salary: Optional[float]
    currency: str = "UZS"
    city: Optional[str]
    job_type: Optional[JobType]
    experience: List[ExperienceItem] = []
    education: List[EducationItem] = []
    skills: List[str] = []
    languages: List[LanguageItem] = []
    contacts: dict = {}
    is_public: bool = True

class ResumeOut(BaseModel):
    id: int
    title: str
    summary: Optional[str]
    desired_salary: Optional[float]
    currency: str
    city: Optional[str]
    job_type: Optional[JobType]
    experience: List[Any]
    education: List[Any]
    skills: List[str]
    languages: List[Any]
    contacts: dict
    is_public: bool
    ai_generated: bool
    user: UserOut
    created_at: datetime

    class Config:
        from_attributes = True


# ─── APPLICATIONS ────────────────────────────────────────
class ApplicationCreate(BaseModel):
    job_id: int
    resume_id: Optional[int]
    cover_letter: Optional[str]

class ApplicationOut(BaseModel):
    id: int
    status: ApplicationStatus
    cover_letter: Optional[str]
    job: JobOut
    created_at: datetime

    class Config:
        from_attributes = True


# ─── AI ─────────────────────────────────────────────────
class GenerateResumeRequest(BaseModel):
    user_description: str = Field(..., description="Свободный текст о себе, опыте, навыках")

class AISearchRequest(BaseModel):
    query: str
    city: Optional[str]
    job_type: Optional[JobType]

class AICoverLetterRequest(BaseModel):
    job_id: int
    resume_id: int

class AIInterviewRequest(BaseModel):
    job_title: str
    level: str = "middle"  # junior/middle/senior

class AIMessageIn(BaseModel):
    role: str  # user / assistant
    content: str

class AIChatRequest(BaseModel):
    messages: List[AIMessageIn]
    mode: str = "chat"  # chat / resume


TokenResponse.model_rebuild()
