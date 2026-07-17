

import json
import re
import logging
import time
from typing import Dict, Optional
from groq import Groq

logger = logging.getLogger(__name__)


class ResumeAnalyzer:
    def __init__(self, api_key: str = None):
        self.available = False
        self.client = None

        # Try Groq first
        try:
            from ..config import settings
            groq_key = settings.GROQ_API_KEY
            if groq_key:
                self.client = Groq(api_key=groq_key)
                self.available = True
                logger.info("✅ Groq AI client initialized successfully")
                return
        except Exception as e:
            logger.error(f"❌ Failed to initialize Groq client: {e}")

        logger.warning("⚠️ No AI client available")

    def _get_model(self) -> str:
        """Get model name from settings"""
        try:
            from ..config import settings
            return settings.GROQ_MODEL
        except Exception:
            return "llama-3.3-70b-versatile"

    def _call_ai(self, prompt: str) -> Optional[str]:
        """Central method to call Groq API with retry logic"""
        if not self.available or not self.client:
            return None

        max_retries = 3
        retry_delays = [5, 15, 30]

        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self._get_model(),
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an expert resume analyzer. Always respond with valid JSON only."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.3,
                    max_tokens=2048,
                )
                return response.choices[0].message.content.strip()

            except Exception as e:
                error_str = str(e)
                logger.error(
                    f"❌ Groq API call failed attempt {attempt + 1}: {e}"
                )

                if '429' in error_str or 'rate' in error_str.lower():
                    if attempt < max_retries - 1:
                        delay = retry_delays[attempt]
                        logger.warning(
                            f"⚠️ Rate limited. Retrying in {delay}s..."
                        )
                        time.sleep(delay)
                        continue
                    else:
                        logger.error("❌ Max retries reached")
                        return None

                return None

        return None

    def _extract_json(self, text: str) -> Optional[Dict]:
        """Safely extract JSON from AI response"""
        if not text:
            return None

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        try:
            match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
            if match:
                return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

        try:
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                return json.loads(match.group())
        except json.JSONDecodeError:
            pass

        logger.error("❌ Could not extract valid JSON from AI response")
        return None

    def _validate_analysis(self, data: Dict) -> Dict:
        """Validate and sanitize analysis response"""
        validated = {}

        score = data.get('ats_score', 0)
        try:
            score = float(score)
            validated['ats_score'] = max(0.0, min(100.0, score))
        except (ValueError, TypeError):
            validated['ats_score'] = 0.0

        for key in ['strengths', 'improvements', 'missing_keywords', 'suggested_roles']:
            value = data.get(key, [])
            if isinstance(value, list):
                validated[key] = [str(v) for v in value if v]
            else:
                validated[key] = []

        section_scores = data.get('section_scores', {})
        if isinstance(section_scores, dict):
            validated['section_scores'] = {
                k: max(0.0, min(100.0, float(v)))
                for k, v in section_scores.items()
                if isinstance(v, (int, float))
            }
        else:
            validated['section_scores'] = {}

        validated['rewritten_summary'] = str(data.get('rewritten_summary', ''))
        validated['detailed_feedback'] = data.get('detailed_feedback', {})

        return validated

    def analyze_resume(
        self,
        parsed_data: Dict,
        job_description: Optional[str] = None
    ) -> Dict:
        """Analyze resume and return structured analysis"""

        if not parsed_data or not isinstance(parsed_data, dict):
            logger.error("❌ Invalid parsed_data provided")
            return self._unavailable_response()

        if not self.available:
            return self._unavailable_response()

        skills = parsed_data.get('skills', [])
        experience = parsed_data.get('experience', [])
        education = parsed_data.get('education', [])
        full_text = parsed_data.get('full_text', '')[:3000]

        prompt = f"""
Analyze this resume and return ONLY a valid JSON object. No extra text.

Resume Details:
- Skills: {', '.join(skills) if skills else 'Not provided'}
- Experience: {experience}
- Education: {education}
- Resume Text: {full_text}

Job Description: {job_description if job_description else 'General evaluation'}

Return this exact JSON structure:
{{
    "ats_score": <number 0-100>,
    "strengths": [<list of 3-5 specific strengths>],
    "improvements": [<list of 3-5 specific improvements>],
    "missing_keywords": [<list of missing keywords>],
    "section_scores": {{
        "experience": <number 0-100>,
        "education": <number 0-100>,
        "skills": <number 0-100>,
        "projects": <number 0-100>
    }},
    "rewritten_summary": "<improved professional summary>",
    "suggested_roles": [<list of 3-5 matching roles>],
    "detailed_feedback": {{
        "content": "<content feedback>",
        "formatting": "<formatting feedback>"
    }}
}}
"""

        response_text = self._call_ai(prompt)

        if not response_text:
            return self._unavailable_response()

        result = self._extract_json(response_text)

        if not result:
            return self._unavailable_response()

        validated = self._validate_analysis(result)
        validated['ai_powered'] = True
        return validated

    def _unavailable_response(self) -> Dict:
        return {
            "ai_powered": False,
            "ats_score": None,
            "strengths": [],
            "improvements": [],
            "missing_keywords": [],
            "section_scores": {},
            "rewritten_summary": "",
            "suggested_roles": [],
            "detailed_feedback": {},
            "message": "AI analysis unavailable. Please check your API key."
        }