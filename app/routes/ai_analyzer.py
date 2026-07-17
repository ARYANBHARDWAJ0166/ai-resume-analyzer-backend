import logging
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Dict

from ..database import (
    get_db, Resume, SkillGapAnalysis, InterviewQuestion,
    GitHubAnalysis, ChatHistory, Analytics, ResumeVersion,
    JobSearchHistory, SavedJob
)
from ..schemas import (
    RewriteRequest, CoverLetterRequest, SkillGapRequest,
    RoadmapRequest, InterviewQuestionsRequest, GitHubAnalysisRequest,
    ChatRequest, AnalyticsTrackRequest, SaveVersionRequest,
    BulkAnalysisRequest, CompareResumesRequest,
    JobSearchRequest, SaveJobRequest,
)
from ..config import settings
from ..services import AdvancedAnalyzer, ResumeAnalyzer

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ai_analyzer"])

# ─── Service Instances ────────────────────────────────────
advanced_analyzer = AdvancedAnalyzer()
analyzer = ResumeAnalyzer()


# ─── Generate Heatmap ─────────────────────────────────────
@router.post("/generate-heatmap/{resume_id}")
async def generate_heatmap(
    resume_id: int,
    db: Session = Depends(get_db)
):
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(404, detail="Resume not found")

    if not resume.parsed_data:
        raise HTTPException(422, detail="Resume has no parsed data")

    try:
        heatmap = advanced_analyzer.generate_heatmap(
            resume.parsed_data.get('full_text', '')
        )
        resume.heatmap_data = heatmap
        db.commit()
        db.refresh(resume)
    except Exception as e:
        logger.error(f"❌ Heatmap generation error: {e}")
        raise HTTPException(500, detail="Could not generate heatmap")

    return {
        "success": True,
        "resume_id": resume_id,
        "heatmap": heatmap
    }


# ─── Rewrite Resume Section ───────────────────────────────
@router.post("/rewrite-resume-section")
async def rewrite_resume_section(req: RewriteRequest):
    try:
        rewritten = advanced_analyzer.rewrite_resume_section(
            req.section_text,
            req.section_type.value if req.section_type else "experience",
            req.style.value if req.style else "professional"
        )
    except Exception as e:
        logger.error(f"❌ Rewrite error: {e}")
        raise HTTPException(500, detail="Could not rewrite section")

    return {
        "success": True,
        "rewritten_text": rewritten
    }


# ─── Generate Cover Letter ────────────────────────────────
@router.post("/generate-cover-letter")
async def generate_cover_letter(
    req: CoverLetterRequest,
    db: Session = Depends(get_db)
):
    resume = db.query(Resume).filter(Resume.id == req.resume_id).first()
    if not resume:
        raise HTTPException(404, detail="Resume not found")

    if not resume.parsed_data:
        raise HTTPException(422, detail="Resume has no parsed data")

    try:
        cover_letter = advanced_analyzer.generate_cover_letter(
            resume.parsed_data,
            {
                "title": req.job_title,
                "company": req.company,
                "description": req.job_description
            }
        )
    except Exception as e:
        logger.error(f"❌ Cover letter error: {e}")
        raise HTTPException(500, detail="Could not generate cover letter")

    return {
        "success": True,
        "resume_id": req.resume_id,
        "cover_letter": cover_letter
    }


# ─── Analyze Skill Gap ────────────────────────────────────
@router.post("/analyze-skill-gap")
async def analyze_skill_gap(
    req: SkillGapRequest,
    db: Session = Depends(get_db)
):
    resume = db.query(Resume).filter(Resume.id == req.resume_id).first()
    if not resume:
        raise HTTPException(404, detail="Resume not found")

    if not resume.parsed_data:
        raise HTTPException(422, detail="Resume has no parsed data")

    current_skills = resume.parsed_data.get('skills', [])

    try:
        gap_analysis = advanced_analyzer.analyze_skill_gap(
            current_skills,
            req.job_skills
        )

        # Check if analysis already exists for this resume
        existing = db.query(SkillGapAnalysis).filter(
            SkillGapAnalysis.resume_id == req.resume_id
        ).first()

        if existing:
            # Update existing
            existing.current_skills = current_skills
            existing.required_skills = req.job_skills
            existing.missing_skills = gap_analysis.get('missing_skills', [])
            existing.learning_resources = gap_analysis.get('learning_resources', [])
        else:
            # Create new
            skill_gap = SkillGapAnalysis(
                resume_id=req.resume_id,
                current_skills=current_skills,
                required_skills=req.job_skills,
                missing_skills=gap_analysis.get('missing_skills', []),
                learning_resources=gap_analysis.get('learning_resources', [])
            )
            db.add(skill_gap)

        db.commit()

    except Exception as e:
        logger.error(f"❌ Skill gap error: {e}")
        raise HTTPException(500, detail="Could not analyze skill gap")

    return {
        "success": True,
        "resume_id": req.resume_id,
        "analysis": gap_analysis
    }


# ─── Generate Learning Roadmap ────────────────────────────
@router.post("/generate-learning-roadmap")
async def generate_learning_roadmap(
    req: RoadmapRequest,
    db: Session = Depends(get_db)
):
    resume = db.query(Resume).filter(Resume.id == req.resume_id).first()
    if not resume:
        raise HTTPException(404, detail="Resume not found")

    try:
        roadmap = advanced_analyzer.generate_learning_roadmap(
            resume.parsed_data.get('skills', []) if resume.parsed_data else [],
            req.target_role
        )
    except Exception as e:
        logger.error(f"❌ Roadmap error: {e}")
        raise HTTPException(500, detail="Could not generate roadmap")

    return {
        "success": True,
        "resume_id": req.resume_id,
        "roadmap": roadmap
    }


# ─── Generate Interview Questions ─────────────────────────
@router.post("/generate-interview-questions")
async def generate_interview_questions(
    req: InterviewQuestionsRequest,
    db: Session = Depends(get_db)
):
    resume = db.query(Resume).filter(Resume.id == req.resume_id).first()
    if not resume:
        raise HTTPException(404, detail="Resume not found")

    if not resume.parsed_data:
        raise HTTPException(422, detail="Resume has no parsed data")

    try:
        questions = advanced_analyzer.generate_interview_questions(
            resume.parsed_data,
            {
                "title": req.job_title,
                "description": req.job_description
            }
        )

        # Save questions to DB
        for q in questions:
            db.add(InterviewQuestion(
                resume_id=req.resume_id,
                category=q.get('category', 'general'),
                question=q.get('question', ''),
                sample_answer=q.get('sample_answer', ''),
                difficulty=q.get('difficulty', 'medium')
            ))
        db.commit()

    except Exception as e:
        logger.error(f"❌ Interview questions error: {e}")
        raise HTTPException(500, detail="Could not generate interview questions")

    return {
        "success": True,
        "resume_id": req.resume_id,
        "questions": questions
    }


# ─── Chat With Resume ─────────────────────────────────────
@router.post("/chat-with-resume")
async def chat_with_resume(
    req: ChatRequest,
    db: Session = Depends(get_db)
):
    resume = db.query(Resume).filter(Resume.id == req.resume_id).first()
    if not resume:
        raise HTTPException(404, detail="Resume not found")

    if not resume.parsed_data:
        raise HTTPException(422, detail="Resume has no parsed data")

    # Get chat history in chronological order
    chat_history = (
        db.query(ChatHistory)
        .filter(ChatHistory.resume_id == req.resume_id)
        .order_by(ChatHistory.created_at.desc())
        .limit(5)
        .all()
    )

    # Pass in chronological order (oldest first)
    history = [
        {
            "user_message": c.user_message,
            "ai_response": c.ai_response
        }
        for c in chat_history
    ]

    try:
        response = advanced_analyzer.chat_with_resume(
            resume.parsed_data,
            req.message,
            history
        )

        # Save to DB
        chat = ChatHistory(
            resume_id=req.resume_id,
            user_message=req.message,
            ai_response=response
        )
        db.add(chat)
        db.commit()
        db.refresh(chat)

    except Exception as e:
        logger.error(f"❌ Chat error: {e}")
        raise HTTPException(500, detail="Could not process chat message")

    return {
        "success": True,
        "resume_id": req.resume_id,
        "response": response,
        "chat_id": chat.id
    }


# ─── Get Chat History ─────────────────────────────────────
@router.get("/chat-history/{resume_id}")
async def get_chat_history(
    resume_id: int,
    db: Session = Depends(get_db)
):
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(404, detail="Resume not found")

    chats = (
        db.query(ChatHistory)
        .filter(ChatHistory.resume_id == resume_id)
        .order_by(ChatHistory.created_at.asc())
        .all()
    )

    return {
        "success": True,
        "resume_id": resume_id,
        "chats": [
            {
                "id": c.id,
                "user_message": c.user_message,
                "ai_response": c.ai_response,
                "created_at": c.created_at
            }
            for c in chats
        ]
    }


# ─── Save Resume Version ──────────────────────────────────
@router.post("/save-resume-version")
async def save_resume_version(
    req: SaveVersionRequest,
    db: Session = Depends(get_db)
):
    resume = db.query(Resume).filter(Resume.id == req.resume_id).first()
    if not resume:
        raise HTTPException(404, detail="Resume not found")

    try:
        # Get next version number
        version_count = (
            db.query(ResumeVersion)
            .filter(ResumeVersion.resume_id == req.resume_id)
            .count()
        )
        version_number = version_count + 1

        version = ResumeVersion(
            resume_id=req.resume_id,
            version_number=version_number,
            content=req.content,
            changes=req.changes or {}
        )
        db.add(version)
        db.commit()
        db.refresh(version)

    except Exception as e:
        logger.error(f"❌ Save version error: {e}")
        raise HTTPException(500, detail="Could not save resume version")

    return {
        "success": True,
        "resume_id": req.resume_id,
        "version_number": version_number,
        "version_id": version.id
    }


# ─── Get Resume Versions ──────────────────────────────────
@router.get("/resume-versions/{resume_id}")
async def get_resume_versions(
    resume_id: int,
    db: Session = Depends(get_db)
):
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(404, detail="Resume not found")

    versions = (
        db.query(ResumeVersion)
        .filter(ResumeVersion.resume_id == resume_id)
        .order_by(ResumeVersion.version_number.desc())
        .all()
    )

    return {
        "success": True,
        "resume_id": resume_id,
        "versions": [
            {
                "id": v.id,
                "version_number": v.version_number,
                "changes": v.changes,
                "created_at": v.created_at
            }
            for v in versions
        ]
    }


# ─── Bulk Analyze ─────────────────────────────────────────
@router.post("/bulk-analyze")
async def bulk_analyze_resumes(
    req: BulkAnalysisRequest,
    db: Session = Depends(get_db)
):
    results = []

    for resume_id in req.resume_ids:
        resume = db.query(Resume).filter(Resume.id == resume_id).first()
        if not resume:
            results.append({
                "resume_id": resume_id,
                "error": "Resume not found"
            })
            continue

        if not resume.parsed_data:
            results.append({
                "resume_id": resume_id,
                "error": "No parsed data"
            })
            continue

        try:
            analysis = analyzer.analyze_resume(
                resume.parsed_data,
                req.job_description
            )
            resume.analysis_result = analysis
            db.commit()

            results.append({
                "resume_id": resume_id,
                "filename": resume.filename,
                "analysis": analysis
            })
        except Exception as e:
            logger.error(f"❌ Bulk analyze error for {resume_id}: {e}")
            results.append({
                "resume_id": resume_id,
                "error": "Analysis failed"
            })

    return {
        "success": True,
        "total": len(req.resume_ids),
        "results": results
    }


# ─── Compare Resumes ──────────────────────────────────────
@router.post("/compare-resumes")
async def compare_resumes(
    req: CompareResumesRequest,
    db: Session = Depends(get_db)
):
    resume1 = db.query(Resume).filter(Resume.id == req.resume_id_1).first()
    resume2 = db.query(Resume).filter(Resume.id == req.resume_id_2).first()

    if not resume1:
        raise HTTPException(404, detail=f"Resume {req.resume_id_1} not found")
    if not resume2:
        raise HTTPException(404, detail=f"Resume {req.resume_id_2} not found")

    skills1 = set(resume1.parsed_data.get('skills', [])) if resume1.parsed_data else set()
    skills2 = set(resume2.parsed_data.get('skills', [])) if resume2.parsed_data else set()

    common_skills = list(skills1 & skills2)
    unique_to_1 = list(skills1 - skills2)
    unique_to_2 = list(skills2 - skills1)

    score1 = (
        resume1.analysis_result.get('ats_score', 0)
        if resume1.analysis_result else 0
    )
    score2 = (
        resume2.analysis_result.get('ats_score', 0)
        if resume2.analysis_result else 0
    )

    return {
        "success": True,
        "resume_1": {
            "id": resume1.id,
            "filename": resume1.filename,
            "skills": list(skills1),
            "ats_score": score1
        },
        "resume_2": {
            "id": resume2.id,
            "filename": resume2.filename,
            "skills": list(skills2),
            "ats_score": score2
        },
        "comparison": {
            "common_skills": common_skills,
            "unique_to_resume_1": unique_to_1,
            "unique_to_resume_2": unique_to_2,
            "score_difference": round(abs(score1 - score2), 2),
            "better_resume": (
                resume1.id if score1 >= score2 else resume2.id
            )
        }
    }


# ─── Export Resume ────────────────────────────────────────
@router.get("/export-resume/{resume_id}")
async def export_resume_data(
    resume_id: int,
    format: str = Query("json", regex="^(json)$"),
    db: Session = Depends(get_db)
):
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(404, detail="Resume not found")

    data = {
        "id": resume.id,
        "filename": resume.filename,
        "parsed_data": resume.parsed_data,
        "analysis": resume.analysis_result,
        "created_at": resume.created_at.isoformat() if resume.created_at else None,
        "updated_at": resume.updated_at.isoformat() if resume.updated_at else None
    }

    return JSONResponse(content=data)


# ─── Find Jobs ────────────────────────────────────────────
@router.post("/find-jobs")
async def find_jobs(
    req: JobSearchRequest,
    db: Session = Depends(get_db)
):
    resume = db.query(Resume).filter(Resume.id == req.resume_id).first()
    if not resume:
        raise HTTPException(404, detail="Resume not found")

    if not resume.parsed_data:
        raise HTTPException(422, detail="Resume has no parsed data")

    skills = resume.parsed_data.get('skills', [])

    # Build search query
    search_query = req.job_title or ""
    if skills:
        top_skills = " ".join(skills[:5])
        search_query = f"{search_query} {top_skills}".strip()

    if not search_query:
        raise HTTPException(400, detail="Could not build search query from resume")

    try:
        jobs = await fetch_jobs_from_adzuna(
            query=search_query,
            location=req.location or "",
            limit=req.limit or 10
        )

        # Calculate match scores
        from ..services import ResumeParser
        local_parser = ResumeParser()

        for job in jobs:
            job_skills = local_parser.extract_skills(
                job.get('description', '')
            )
            if skills and job_skills:
                matching = set(s.lower() for s in skills) & set(s.lower() for s in job_skills)
                score = min(100, int((len(matching) / max(len(job_skills), 1)) * 100))
            else:
                score = 0

            job['match_score'] = score
            job['match_percentage'] = f"{score}%"

        # Sort by match score
        jobs.sort(key=lambda x: x.get('match_score', 0), reverse=True)

        # Save search history
        search_history = JobSearchHistory(
            resume_id=req.resume_id,
            query=search_query,
            results_count=len(jobs),
            search_data={
                "location": req.location,
                "limit": req.limit,
                "source": req.source.value if req.source else "all"
            }
        )
        db.add(search_history)
        db.commit()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Job search error: {e}")
        raise HTTPException(500, detail="Could not fetch job listings")

    return {
        "success": True,
        "jobs": jobs,
        "total_found": len(jobs),
        "search_query": search_query
    }


# ─── Adzuna Job Fetcher ───────────────────────────────────
async def fetch_jobs_from_adzuna(
    query: str,
    location: str = "",
    limit: int = 10
) -> List[Dict]:
    """Fetch real job listings from Adzuna API"""

    if not settings.ADZUNA_APP_ID or not settings.ADZUNA_APP_KEY:
        logger.warning("⚠️ Adzuna API keys not configured")
        return []

    try:
        params = {
            "app_id": settings.ADZUNA_APP_ID,
            "app_key": settings.ADZUNA_APP_KEY,
            "results_per_page": min(limit, 50),
            "what": query,
            "content-type": "application/json"
        }

        if location:
            params["where"] = location

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                "https://api.adzuna.com/v1/api/jobs/us/search/1",
                params=params,
                headers={"Accept": "application/json"}
            )

            if response.status_code != 200:
                logger.error(f"❌ Adzuna API error: {response.status_code}")
                return []

            data = response.json()
            jobs = []

            for item in data.get('results', []):
                jobs.append({
                    "title": item.get('title', ''),
                    "company": item.get('company', {}).get('display_name', 'Unknown'),
                    "location": item.get('location', {}).get('display_name', location or 'Various'),
                    "description": item.get('description', '')[:500],
                    "url": item.get('redirect_url', ''),
                    "source": "Adzuna",
                    "posted_at": item.get('created', ''),
                    "apply_url": item.get('redirect_url', ''),
                    "salary_min": item.get('salary_min'),
                    "salary_max": item.get('salary_max'),
                })

            return jobs

    except httpx.TimeoutException:
        logger.error("❌ Adzuna API request timed out")
        return []
    except Exception as e:
        logger.error(f"❌ Adzuna fetch error: {e}")
        return []


# ─── Save Job ─────────────────────────────────────────────
@router.post("/save-job")
async def save_job(
    req: SaveJobRequest,
    db: Session = Depends(get_db)
):
    resume = db.query(Resume).filter(Resume.id == req.resume_id).first()
    if not resume:
        raise HTTPException(404, detail="Resume not found")

    # Check if already saved
    existing = db.query(SavedJob).filter(
        SavedJob.resume_id == req.resume_id,
        SavedJob.job_url == req.job_url
    ).first()

    if existing:
        return {
            "success": True,
            "message": "Job already saved",
            "saved_job_id": existing.id
        }

    try:
        saved_job = SavedJob(
            resume_id=req.resume_id,
            job_title=req.job_title,
            company=req.company,
            job_url=req.job_url,
            match_score=req.match_score,
            location=req.location
        )
        db.add(saved_job)
        db.commit()
        db.refresh(saved_job)

    except Exception as e:
        logger.error(f"❌ Save job error: {e}")
        raise HTTPException(500, detail="Could not save job")

    return {
        "success": True,
        "message": "Job saved successfully",
        "saved_job": {
            "id": saved_job.id,
            "job_title": saved_job.job_title,
            "company": saved_job.company,
            "match_score": saved_job.match_score,
            "created_at": saved_job.created_at
        }
    }


# ─── Get Saved Jobs ───────────────────────────────────────
@router.get("/saved-jobs/{resume_id}")
async def get_saved_jobs(
    resume_id: int,
    db: Session = Depends(get_db)
):
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(404, detail="Resume not found")

    saved_jobs = (
        db.query(SavedJob)
        .filter(SavedJob.resume_id == resume_id)
        .order_by(SavedJob.created_at.desc())
        .all()
    )

    return {
        "success": True,
        "resume_id": resume_id,
        "jobs": [
            {
                "id": job.id,
                "job_title": job.job_title,
                "company": job.company,
                "job_url": job.job_url,
                "location": job.location,
                "match_score": job.match_score,
                "applied": job.applied,
                "created_at": job.created_at
            }
            for job in saved_jobs
        ]
    }


# ─── Delete Saved Job ─────────────────────────────────────
@router.delete("/saved-jobs/{job_id}")
async def delete_saved_job(
    job_id: int,
    db: Session = Depends(get_db)
):
    job = db.query(SavedJob).filter(SavedJob.id == job_id).first()
    if not job:
        raise HTTPException(404, detail="Saved job not found")

    db.delete(job)
    db.commit()

    return {
        "success": True,
        "message": f"Job {job_id} removed from saved jobs"
    }


# ─── Job Search History ───────────────────────────────────
@router.get("/job-search-history/{resume_id}")
async def get_job_search_history(
    resume_id: int,
    db: Session = Depends(get_db)
):
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(404, detail="Resume not found")

    history = (
        db.query(JobSearchHistory)
        .filter(JobSearchHistory.resume_id == resume_id)
        .order_by(JobSearchHistory.created_at.desc())
        .limit(20)
        .all()
    )

    return {
        "success": True,
        "resume_id": resume_id,
        "history": [
            {
                "id": h.id,
                "query": h.query,
                "results_count": h.results_count,
                "created_at": h.created_at
            }
            for h in history
        ]
    }


# ─── GitHub Analysis ──────────────────────────────────────
@router.post("/analyze-github")
async def analyze_github(
    req: GitHubAnalysisRequest,
    db: Session = Depends(get_db)
):
    try:
        result = await advanced_analyzer.analyze_github(req.username)
    except Exception as e:
        logger.error(f"❌ GitHub analysis error: {e}")
        raise HTTPException(500, detail="Could not analyze GitHub profile")

    if "error" in result:
        raise HTTPException(404, detail=result["error"])

    # Save to DB
    try:
        github_analysis = GitHubAnalysis(
            user_id=req.user_id,
            github_username=req.username,
            repositories=result.get('repositories', []),
            languages=result.get('languages', {}),
            contributions=result.get('contributions', {}),
            analysis_result=result.get('analysis_result', {})
        )
        db.add(github_analysis)
        db.commit()
        db.refresh(github_analysis)
    except Exception as e:
        logger.error(f"❌ GitHub DB save error: {e}")

    return {
        "success": True,
        "analysis": result
    }


# ─── Track Analytics ──────────────────────────────────────
@router.post("/track-analytics")
async def track_analytics(
    req: AnalyticsTrackRequest,
    db: Session = Depends(get_db)
):
    try:
        analytics = Analytics(
            user_id=req.user_id,
            event_type=req.event_type,
            event_data=req.event_data or {}
        )
        db.add(analytics)
        db.commit()
    except Exception as e:
        logger.error(f"❌ Analytics track error: {e}")
        raise HTTPException(500, detail="Could not track analytics")

    return {
        "success": True,
        "message": "Event tracked successfully"
    }