import os
import logging
import aiofiles
import filetype
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Response, Query
from sqlalchemy.orm import Session
from datetime import datetime

from ..database import get_db, Resume, MatchResult
from ..schemas import AnalysisRequest, JobMatchRequest
from ..services import ResumeParser, ResumeAnalyzer, JobMatcher, ReportGenerator
from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["resume"])

# ─── Service Instances ────────────────────────────────────
# Created once at startup, shared across requests safely
parser = ResumeParser()
analyzer = ResumeAnalyzer(settings.GEMINI_API_KEY)
matcher = JobMatcher()
report_gen = ReportGenerator()


# ─── Helper ───────────────────────────────────────────────
def _sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal"""
    # Get base name only, remove any path components
    filename = os.path.basename(filename)
    # Replace spaces and special characters
    filename = "".join(
        c if c.isalnum() or c in ".-_" else "_"
        for c in filename
    )
    return filename


# ─── Upload Resume ────────────────────────────────────────
@router.post("/upload-resume")
async def upload_resume(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # 1. Check file extension
    if not file.filename:
        raise HTTPException(400, detail="No filename provided")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in settings.allowed_extensions_list:
        raise HTTPException(
            400,
            detail=f"File type '{ext}' not allowed. Allowed: {settings.allowed_extensions_list}"
        )

    # 2. Read file content
    try:
        content = await file.read()
    except Exception as e:
        logger.error(f"❌ File read error: {e}")
        raise HTTPException(400, detail="Could not read uploaded file")

    # 3. Check file size
    if len(content) > settings.MAX_FILE_SIZE:
        raise HTTPException(
            400,
            detail=f"File too large. Maximum size is {settings.MAX_FILE_SIZE // (1024*1024)}MB"
        )

    # 4. Check file is not empty
    if len(content) == 0:
        raise HTTPException(400, detail="Uploaded file is empty")

    # 5. Verify actual file type (not just extension)
    kind = filetype.guess(content)
    if ext == '.pdf' and kind and kind.mime != 'application/pdf':
        raise HTTPException(400, detail="File content does not match PDF extension")

    # 6. Sanitize filename and build path
    safe_filename = _sanitize_filename(file.filename)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    final_filename = f"{timestamp}_{safe_filename}"
    file_path = os.path.join(settings.UPLOAD_DIR, final_filename)

    # 7. Ensure upload directory exists
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    # 8. Write file asynchronously
    try:
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)
    except Exception as e:
        logger.error(f"❌ File write error: {e}")
        raise HTTPException(500, detail="Could not save uploaded file")

    # 9. Parse resume
    try:
        parsed_data = parser.parse_resume(file_path)
    except Exception as e:
        # Clean up file if parsing fails
        if os.path.exists(file_path):
            os.remove(file_path)
        logger.error(f"❌ Resume parsing error: {e}")
        raise HTTPException(422, detail=f"Could not parse resume: {str(e)}")

    # 10. Save to database
    try:
        db_resume = Resume(
            filename=file.filename,
            file_path=file_path,
            parsed_data=parsed_data
        )
        db.add(db_resume)
        db.commit()
        db.refresh(db_resume)
    except Exception as e:
        # Clean up file if DB fails
        if os.path.exists(file_path):
            os.remove(file_path)
        logger.error(f"❌ Database error: {e}")
        raise HTTPException(500, detail="Could not save resume to database")

    logger.info(f"✅ Resume uploaded successfully: {file.filename}")

    return {
        "success": True,
        "message": "Resume uploaded and parsed successfully",
        "resume_id": db_resume.id,
        "parsed_data": parsed_data
    }


# ─── Get All Resumes ──────────────────────────────────────
@router.get("/resumes")
async def get_resumes(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    resumes = (
        db.query(Resume)
        .order_by(Resume.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    total = db.query(Resume).count()

    return {
        "success": True,
        "total": total,
        "skip": skip,
        "limit": limit,
        "resumes": [
            {
                "id": r.id,
                "filename": r.filename,
                "created_at": r.created_at,
                "has_analysis": bool(r.analysis_result),
                "skills": (
                    r.parsed_data.get("skills", [])[:5]
                    if r.parsed_data else []
                )
            }
            for r in resumes
        ]
    }


# ─── Get Single Resume ────────────────────────────────────
@router.get("/resume/{resume_id}")
async def get_resume(
    resume_id: int,
    db: Session = Depends(get_db)
):
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(404, detail="Resume not found")

    return {
        "success": True,
        "id": resume.id,
        "filename": resume.filename,
        "parsed_data": resume.parsed_data,
        "analysis": resume.analysis_result,
        "created_at": resume.created_at,
        "updated_at": resume.updated_at
    }


# ─── Delete Resume ────────────────────────────────────────
@router.delete("/resume/{resume_id}")
async def delete_resume(
    resume_id: int,
    db: Session = Depends(get_db)
):
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(404, detail="Resume not found")

    # Delete file from disk
    if resume.file_path and os.path.exists(resume.file_path):
        try:
            os.remove(resume.file_path)
        except Exception as e:
            logger.warning(f"⚠️ Could not delete file: {e}")

    # Delete from database (cascade handles related records)
    db.delete(resume)
    db.commit()

    logger.info(f"✅ Resume deleted: {resume_id}")

    return {
        "success": True,
        "message": f"Resume {resume_id} deleted successfully"
    }


# ─── Analyze Resume ───────────────────────────────────────
@router.post("/analyze-resume")
async def analyze_resume(
    req: AnalysisRequest,
    db: Session = Depends(get_db)
):
    resume = db.query(Resume).filter(Resume.id == req.resume_id).first()
    if not resume:
        raise HTTPException(404, detail="Resume not found")

    if not resume.parsed_data:
        raise HTTPException(422, detail="Resume has no parsed data. Please re-upload.")

    try:
        analysis = analyzer.analyze_resume(
            resume.parsed_data,
            req.job_description
        )
        resume.analysis_result = analysis
        db.commit()
        db.refresh(resume)
    except Exception as e:
        logger.error(f"❌ Analysis error: {e}")
        raise HTTPException(500, detail="Could not analyze resume")

    return {
        "success": True,
        "resume_id": resume.id,
        "analysis": analysis
    }


# ─── Match Job ────────────────────────────────────────────
@router.post("/match-job")
async def match_job(
    req: JobMatchRequest,
    db: Session = Depends(get_db)
):
    resume = db.query(Resume).filter(Resume.id == req.resume_id).first()
    if not resume:
        raise HTTPException(404, detail="Resume not found")

    if not resume.parsed_data:
        raise HTTPException(422, detail="Resume has no parsed data. Please re-upload.")

    try:
        resume_skills = resume.parsed_data.get("skills", [])
        job_skills = parser.extract_skills(req.job_description)

        match_res = matcher.match(
            resume_text=resume.parsed_data.get("full_text", ""),
            job_text=req.job_description,
            resume_skills=resume_skills,
            job_skills=job_skills
        )

        # Save match result
        db_match = MatchResult(
            resume_id=resume.id,
            job_title=req.job_title,
            company=req.company,
            match_score=match_res['overall_match'],
            matching_skills=match_res['matching_skills'],
            missing_skills=match_res['missing_skills'],
            analysis=match_res
        )
        db.add(db_match)
        db.commit()
        db.refresh(db_match)

    except Exception as e:
        logger.error(f"❌ Job match error: {e}")
        raise HTTPException(500, detail="Could not match job")

    return {
        "success": True,
        "resume_id": resume.id,
        "match": match_res
    }


# ─── Get Match History ────────────────────────────────────
@router.get("/match-history/{resume_id}")
async def get_match_history(
    resume_id: int,
    db: Session = Depends(get_db)
):
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(404, detail="Resume not found")

    matches = (
        db.query(MatchResult)
        .filter(MatchResult.resume_id == resume_id)
        .order_by(MatchResult.created_at.desc())
        .limit(20)
        .all()
    )

    return {
        "success": True,
        "resume_id": resume_id,
        "matches": [
            {
                "id": m.id,
                "job_title": m.job_title,
                "company": m.company,
                "match_score": m.match_score,
                "matching_skills": m.matching_skills,
                "missing_skills": m.missing_skills,
                "created_at": m.created_at
            }
            for m in matches
        ]
    }


# ─── Generate Report ──────────────────────────────────────
@router.post("/generate-report/{resume_id}")
async def generate_report(
    resume_id: int,
    db: Session = Depends(get_db)
):
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(404, detail="Resume not found")

    if not resume.analysis_result:
        raise HTTPException(
            422,
            detail="No analysis found. Please analyze resume first."
        )

    try:
        pdf_bytes = report_gen.generate_pdf_report(
            resume.analysis_result
        )
    except Exception as e:
        logger.error(f"❌ Report generation error: {e}")
        raise HTTPException(500, detail="Could not generate PDF report")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=Resume_Analysis_{resume_id}.pdf"
        }
    )