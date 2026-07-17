from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, JSON, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime, timezone
from .config import settings

def utcnow():
    return datetime.now(timezone.utc)

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    is_active = Column(Boolean, default=True)
    is_recruiter = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    resumes = relationship("Resume", back_populates="user", cascade="all, delete-orphan")
    saved_jobs = relationship("SavedJob", back_populates="user", cascade="all, delete-orphan")


class Resume(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    filename = Column(String(255), index=True)
    file_path = Column(String(500))
    version = Column(Integer, default=1)
    parsed_data = Column(JSON, default=lambda: {})
    analysis_result = Column(JSON, default=lambda: {})
    heatmap_data = Column(JSON, default=lambda: {})
    rewritten_version = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    user = relationship("User", back_populates="resumes")
    versions = relationship("ResumeVersion", back_populates="resume", cascade="all, delete-orphan")
    chats = relationship("ChatHistory", back_populates="resume", cascade="all, delete-orphan")
    matches = relationship("MatchResult", back_populates="resume", cascade="all, delete-orphan")
    job_searches = relationship("JobSearchHistory", back_populates="resume", cascade="all, delete-orphan")
    saved_jobs = relationship("SavedJob", back_populates="resume", cascade="all, delete-orphan")
    skill_gap_analyses = relationship("SkillGapAnalysis", back_populates="resume", cascade="all, delete-orphan")
    interview_questions = relationship("InterviewQuestion", back_populates="resume", cascade="all, delete-orphan")


class MatchResult(Base):
    __tablename__ = "match_results"

    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey("resumes.id"), index=True)
    job_id = Column(String(255), nullable=True)
    job_title = Column(String(255), nullable=True)
    company = Column(String(255), nullable=True)
    match_score = Column(Float)
    matching_skills = Column(JSON, default=lambda: [])
    missing_skills = Column(JSON, default=lambda: [])
    analysis = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=utcnow)

    resume = relationship("Resume", back_populates="matches")


class ResumeVersion(Base):
    __tablename__ = "resume_versions"

    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey("resumes.id"), index=True)
    version_number = Column(Integer)
    content = Column(Text)
    changes = Column(JSON, default=lambda: {})
    created_at = Column(DateTime, default=utcnow)

    resume = relationship("Resume", back_populates="versions")


class ChatHistory(Base):
    __tablename__ = "chat_histories"

    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey("resumes.id"), index=True)
    user_message = Column(Text)
    ai_response = Column(Text)
    created_at = Column(DateTime, default=utcnow)

    resume = relationship("Resume", back_populates="chats")


class SavedJob(Base):
    __tablename__ = "saved_jobs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=True, index=True)
    job_title = Column(String(255))
    company = Column(String(255))
    job_description = Column(Text, nullable=True)
    job_url = Column(String(500), nullable=True)
    location = Column(String(255), nullable=True)
    match_score = Column(Float, nullable=True)
    applied = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    user = relationship("User", back_populates="saved_jobs")
    resume = relationship("Resume", back_populates="saved_jobs")


class SkillGapAnalysis(Base):
    __tablename__ = "skill_gap_analyses"

    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey("resumes.id"), index=True)
    current_skills = Column(JSON, default=lambda: [])
    required_skills = Column(JSON, default=lambda: [])
    missing_skills = Column(JSON, default=lambda: [])
    learning_resources = Column(JSON, default=lambda: [])
    created_at = Column(DateTime, default=utcnow)

    resume = relationship("Resume", back_populates="skill_gap_analyses")


class InterviewQuestion(Base):
    __tablename__ = "interview_questions"

    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey("resumes.id"), index=True)
    category = Column(String(100))
    question = Column(Text)
    sample_answer = Column(Text)
    difficulty = Column(String(50))
    created_at = Column(DateTime, default=utcnow)

    resume = relationship("Resume", back_populates="interview_questions")


class GitHubAnalysis(Base):
    __tablename__ = "github_analyses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    github_username = Column(String(255))
    repositories = Column(JSON, default=lambda: [])
    languages = Column(JSON, default=lambda: {})
    contributions = Column(JSON, default=lambda: {})
    analysis_result = Column(JSON, default=lambda: {})
    created_at = Column(DateTime, default=utcnow)


class Analytics(Base):
    __tablename__ = "analytics"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    event_type = Column(String(255))
    event_data = Column(JSON, default=lambda: {})
    created_at = Column(DateTime, default=utcnow)


class JobSearchHistory(Base):
    __tablename__ = "job_search_history"

    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey("resumes.id"), index=True)
    query = Column(String(500))
    results_count = Column(Integer, default=0)
    search_data = Column(JSON, default=lambda: {})
    created_at = Column(DateTime, default=utcnow)

    resume = relationship("Resume", back_populates="job_searches")


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()