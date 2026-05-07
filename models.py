from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime,
    ForeignKey, Enum, Numeric, JSON
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from database import Base


class UserRole(str, enum.Enum):
    jobseeker = "jobseeker"   # Соискатель
    employer = "employer"     # Работодатель
    admin = "admin"           # Админ


class JobType(str, enum.Enum):
    office = "office"         # Офис
    remote = "remote"         # Удалённо
    hybrid = "hybrid"         # Гибрид


class JobStatus(str, enum.Enum):
    active = "active"
    closed = "closed"
    draft = "draft"


class ApplicationStatus(str, enum.Enum):
    pending = "pending"       # На рассмотрении
    viewed = "viewed"         # Просмотрено
    invited = "invited"       # Приглашён
    rejected = "rejected"     # Отказ
    hired = "hired"           # Принят


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String(20), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=True)
    full_name = Column(String(255), nullable=True)
    role = Column(Enum(UserRole), default=UserRole.jobseeker)
    is_active = Column(Boolean, default=True)
    avatar_url = Column(String(500), nullable=True)
    password_hash = Column(String(255), nullable=True)
    fcm_token = Column(String(500), nullable=True)
    device_platform = Column(String(20), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Связи
    resumes = relationship("Resume", back_populates="user", cascade="all, delete")
    company = relationship("Company", back_populates="owner", uselist=False)
    applications = relationship("Application", back_populates="user")


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    logo_url = Column(String(500), nullable=True)
    website = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    industry = Column(String(100), nullable=True)
    size = Column(String(50), nullable=True)  # "1-10", "11-50", "50-200", "200+"
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Связи
    owner = relationship("User", back_populates="company")
    jobs = relationship("Job", back_populates="company", cascade="all, delete")


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    requirements = Column(Text, nullable=True)
    responsibilities = Column(Text, nullable=True)
    salary_min = Column(Numeric(15, 2), nullable=True)
    salary_max = Column(Numeric(15, 2), nullable=True)
    currency = Column(String(10), default="UZS")
    job_type = Column(Enum(JobType), default=JobType.office)
    city = Column(String(100), nullable=True)
    experience_years = Column(Integer, default=0)
    skills = Column(JSON, default=list)         # ["Python", "FastAPI", ...]
    category = Column(String(100), nullable=True)
    status = Column(Enum(JobStatus), default=JobStatus.active)
    is_hot = Column(Boolean, default=False)
    views_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Связи
    company = relationship("Company", back_populates="jobs")
    applications = relationship("Application", back_populates="job")


class Resume(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)          # "Python разработчик"
    summary = Column(Text, nullable=True)                # О себе
    desired_salary = Column(Numeric(15, 2), nullable=True)
    currency = Column(String(10), default="UZS")
    city = Column(String(100), nullable=True)
    job_type = Column(Enum(JobType), nullable=True)
    experience = Column(JSON, default=list)              # [{company, position, start, end, desc}]
    education = Column(JSON, default=list)               # [{institution, degree, year}]
    skills = Column(JSON, default=list)                  # ["Python", "SQL", ...]
    languages = Column(JSON, default=list)               # [{"lang": "Русский", "level": "Родной"}]
    contacts = Column(JSON, default=dict)                # {email, telegram, linkedin}
    is_public = Column(Boolean, default=True)
    ai_generated = Column(Boolean, default=False)        # Создано через AI
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Связи
    user = relationship("User", back_populates="resumes")


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=True)
    cover_letter = Column(Text, nullable=True)
    status = Column(Enum(ApplicationStatus), default=ApplicationStatus.pending)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Связи
    user = relationship("User", back_populates="applications")
    job = relationship("Job", back_populates="applications")


class OTPCode(Base):
    """SMS коды для авторизации по телефону"""
    __tablename__ = "otp_codes"

    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String(20), nullable=False, index=True)
    code = Column(String(6), nullable=False)
    is_used = Column(Boolean, default=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
