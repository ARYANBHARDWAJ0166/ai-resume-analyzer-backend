import json
import re
import logging
from typing import Dict, Optional
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


class ResumeAnalyzer:
    def __init__(self, api_key: str):
        self.available = False
        self.client = None

        if not api_key:
            logger.warning("⚠️ No Gemini API key provided. AI analysis unavailable.")
            return

        try:
            self.client = genai.Client(api_key=api_key)
            self.available = True
            logger.info("✅ Gemini AI client initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Gemini client: {e}")

    def _call_gemini(self, prompt: str, model: str = "gemini-1.5-flash") -> Optional[str]:
        """Central method to call Gemini API with error handling"""
        if not self.available or not self.client:
            return None

        try:
            response = self.client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,
                    max_output_tokens=2048,
                )
            )
            return response.text.strip() if response.text else None

        except Exception as e:
            logger.error(f"❌ Gemini API call failed: {e}")
            return None

    def _extract_json(self, text: str) -> Optional[Dict]:
        """Safely extract JSON from Gemini response"""
        if not text:
            return None

        try:
            # Try direct JSON parse first
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        try:
            # Try to find JSON block in markdown
            match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
            if match:
                return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

        try:
            # Try to find raw JSON object
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                return json.loads(match.group())
        except json.JSONDecodeError:
            pass

        logger.error("❌ Could not extract valid JSON from Gemini response")
        return None

    def _validate_analysis(self, data: Dict) -> Dict:
        """Validate and sanitize analysis response from Gemini"""
        validated = {}

        # ATS Score - must be 0-100
        score = data.get('ats_score', 0)
        try:
            score = float(score)
            validated['ats_score'] = max(0.0, min(100.0, score))
        except (ValueError, TypeError):
            validated['ats_score'] = 0.0

        # Lists - must be lists of strings
        for key in ['strengths', 'improvements', 'missing_keywords', 'suggested_roles']:
            value = data.get(key, [])
            if isinstance(value, list):
                validated[key] = [str(v) for v in value if v]
            else:
                validated[key] = []

        # Section scores - must be dict of 0-100 values
        section_scores = data.get('section_scores', {})
        if isinstance(section_scores, dict):
            validated['section_scores'] = {
                k: max(0.0, min(100.0, float(v)))
                for k, v in section_scores.items()
                if isinstance(v, (int, float))
            }
        else:
            validated['section_scores'] = {}

        # Strings
        validated['rewritten_summary'] = str(data.get('rewritten_summary', ''))
        validated['detailed_feedback'] = data.get('detailed_feedback', {})

        return validated

    def analyze_resume(self, parsed_data: Dict, job_description: Optional[str] = None) -> Dict:
        """Analyze resume and return structured analysis"""

        # Validate input
        if not parsed_data or not isinstance(parsed_data, dict):
            logger.error("❌ Invalid parsed_data provided")
            return self._unavailable_response()

        if not self.available:
            logger.warning("⚠️ Gemini unavailable - returning unavailable response")
            return self._unavailable_response()

        # Build prompt
        skills = parsed_data.get('skills', [])
        experience = parsed_data.get('experience', [])
        education = parsed_data.get('education', [])
        full_text = parsed_data.get('full_text', '')[:3000]

        prompt = f"""
You are an expert ATS resume analyzer.
Analyze this resume and return ONLY a valid JSON object. No extra text.

Resume Details:
- Skills: {', '.join(skills) if skills else 'Not provided'}
- Experience: {experience}
- Education: {education}
- Resume Text: {full_text}

Job Description: {job_description if job_description else 'General evaluation - no specific job'}

Return this exact JSON structure:
{{
    "ats_score": <number 0-100>,
    "strengths": [<list of 3-5 specific strengths from THIS resume>],
    "improvements": [<list of 3-5 specific improvements for THIS resume>],
    "missing_keywords": [<list of important keywords missing from THIS resume>],
    "section_scores": {{
        "experience": <number 0-100>,
        "education": <number 0-100>,
        "skills": <number 0-100>,
        "projects": <number 0-100>
    }},
    "rewritten_summary": "<improved professional summary based on THIS resume>",
    "suggested_roles": [<list of 3-5 roles that match THIS resume>],
    "detailed_feedback": {{
        "content": "<specific content feedback>",
        "formatting": "<specific formatting feedback>"
    }}
}}
"""

        # Call Gemini
        response_text = self._call_gemini(prompt)

        if not response_text:
            logger.warning("⚠️ Empty response from Gemini")
            return self._unavailable_response()

        # Extract and validate JSON
        result = self._extract_json(response_text)

        if not result:
            logger.warning("⚠️ Could not parse Gemini response as JSON")
            return self._unavailable_response()

        # Validate and return
        validated = self._validate_analysis(result)
        validated['ai_powered'] = True
        return validated

    def _unavailable_response(self) -> Dict:
        """
        Return a clear unavailable response
        instead of fake/misleading data
        """
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
            "message": (
                "AI analysis is currently unavailable. "
                "Please check your Gemini API key and try again."
            )
        }