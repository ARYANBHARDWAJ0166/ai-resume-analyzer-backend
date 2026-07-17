import json
import re
import logging
import httpx
from typing import Dict, List, Optional
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


class AdvancedAnalyzer:
    def __init__(self, api_key: str):
        self.available = False
        self.client = None

        if not api_key:
            logger.warning("⚠️ No Gemini API key provided. Advanced analysis unavailable.")
            return

        try:
            self.client = genai.Client(api_key=api_key)
            self.available = True
            logger.info("✅ Gemini AI client initialized for AdvancedAnalyzer")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Gemini client: {e}")

    def _get_model(self) -> str:
        """Get model name from settings"""
        try:
            from ..config import settings
            return settings.GEMINI_MODEL
        except Exception:
            return "gemini-2.0-flash"

    def _call_gemini(self, prompt: str, temperature: float = 0.4) -> Optional[str]:
        """Central Gemini API caller with error handling"""
        if not self.available or not self.client:
            return None
        try:
            response = self.client.models.generate_content(
                model=self._get_model(),
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=temperature,
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
        logger.error("❌ Could not extract JSON from Gemini response")
        return None

    def _unavailable_response(self, message: str = "AI analysis unavailable.") -> Dict:
        """Standard unavailable response"""
        return {
            "ai_powered": False,
            "message": message,
            "data": {}
        }

    def _unavailable_text(self, feature: str) -> str:
        """Return unavailable message for text responses"""
        return (
            f"{feature} is currently unavailable. "
            "Please check your Gemini API key and try again."
        )

    # ─── Heatmap ──────────────────────────────────────────────────
    def generate_heatmap(self, resume_text: str) -> Dict:
        """Generate skill heatmap from resume text"""
        if not resume_text or not resume_text.strip():
            return self._default_heatmap()

        if not self.available:
            return self._default_heatmap()

        prompt = f"""
Analyze this resume text and return ONLY a valid JSON object. No extra text.

Resume Text: {resume_text[:3000]}

Return this exact JSON structure:
{{
    "skill_frequency": {{
        "<skill_name>": <number 0-100>,
        "<skill_name>": <number 0-100>
    }},
    "keyword_density": {{
        "<keyword>": <number 0-100>,
        "<keyword>": <number 0-100>
    }},
    "section_strength": {{
        "experience": <number 0-100>,
        "skills": <number 0-100>,
        "education": <number 0-100>,
        "projects": <number 0-100>,
        "summary": <number 0-100>
    }}
}}
"""
        response = self._call_gemini(prompt)
        result = self._extract_json(response)

        if result and all(
            k in result
            for k in ['skill_frequency', 'keyword_density', 'section_strength']
        ):
            return result

        return self._default_heatmap()

    def _default_heatmap(self) -> Dict:
        return {
            "ai_powered": False,
            "skill_frequency": {},
            "keyword_density": {},
            "section_strength": {
                "experience": 0,
                "skills": 0,
                "education": 0,
                "projects": 0,
                "summary": 0
            },
            "message": "Heatmap analysis unavailable. Please check your API key."
        }

    # ─── Rewrite Section ──────────────────────────────────────────
    def rewrite_resume_section(
        self,
        section_text: str,
        section_type: str = "experience",
        style: str = "professional"
    ) -> str:
        """Rewrite a resume section using AI"""
        if not self.available:
            return self._unavailable_text("Section rewrite")

        section_text = section_text[:3000]

        prompt = f"""
You are an expert resume writer.
Rewrite this {section_type} resume section in a {style} style.
Use strong action verbs and quantify achievements where possible.
Keep it concise and ATS-friendly.
Return ONLY the rewritten text, no explanations.

Original Text:
{section_text}
"""
        response = self._call_gemini(prompt, temperature=0.5)

        if response:
            return response

        return self._unavailable_text("Section rewrite")

    # ─── Cover Letter ─────────────────────────────────────────────
    def generate_cover_letter(self, resume_data: Dict, job_data: Dict) -> str:
        """Generate a personalized cover letter"""
        if not self.available:
            return self._unavailable_text("Cover letter generation")

        name = resume_data.get('name', 'Candidate')
        skills = resume_data.get('skills', [])[:10]
        experience = resume_data.get('experience', [])[:3]
        education = resume_data.get('education', [])[:2]
        job_title = job_data.get('title', 'the position')
        company = job_data.get('company', 'your company')
        job_description = job_data.get('description', '')[:2000]

        prompt = f"""
Write a professional and personalized cover letter.
Return ONLY the cover letter text, no explanations.

Candidate Details:
- Name: {name}
- Skills: {', '.join(skills) if skills else 'Not specified'}
- Experience: {experience}
- Education: {education}

Job Details:
- Position: {job_title}
- Company: {company}
- Job Description: {job_description}

Write a compelling 3-paragraph cover letter that:
1. Opens with enthusiasm for the specific role
2. Highlights relevant skills and experience
3. Closes with a call to action
"""
        response = self._call_gemini(prompt, temperature=0.6)

        if response:
            return response

        return self._unavailable_text("Cover letter generation")

    # ─── Skill Gap ────────────────────────────────────────────────
    def analyze_skill_gap(
        self,
        current_skills: List[str],
        job_skills: List[str]
    ) -> Dict:
        """Analyze skill gap between resume and job requirements"""
        if not current_skills and not job_skills:
            return {
                "ai_powered": False,
                "current_skills": [],
                "required_skills": [],
                "missing_skills": [],
                "matching_skills": [],
                "overlap_percentage": 0.0,
                "learning_resources": [],
                "message": "No skills provided for analysis."
            }

        cur_set = {s.lower().strip() for s in current_skills if s}
        req_set = {s.lower().strip() for s in job_skills if s}

        missing = list(req_set - cur_set)
        matching = list(cur_set & req_set)

        overlap = round(
            (len(matching) / len(req_set) * 100), 2
        ) if req_set else 0.0

        resources = self._generate_learning_resources(missing[:5])

        return {
            "ai_powered": self.available,
            "current_skills": sorted(list(cur_set)),
            "required_skills": sorted(list(req_set)),
            "missing_skills": missing,
            "matching_skills": matching,
            "overlap_percentage": overlap,
            "learning_resources": resources
        }

    def _generate_learning_resources(self, skills: List[str]) -> List[Dict]:
        """Generate learning resources for missing skills"""
        if not skills:
            return []

        if not self.available:
            return [
                {
                    "skill": skill,
                    "url": f"https://www.coursera.org/courses?query={skill.replace(' ', '+')}",
                    "platform": "Coursera",
                    "description": f"Courses for {skill}"
                }
                for skill in skills
            ]

        prompt = f"""
For each of these skills, suggest ONE specific learning resource.
Return ONLY a valid JSON array. No extra text.

Skills: {', '.join(skills)}

Return this exact JSON structure:
[
    {{
        "skill": "<skill name>",
        "platform": "<platform name>",
        "url": "<learning url>",
        "description": "<one sentence description>"
    }}
]
"""
        response = self._call_gemini(prompt)

        if response:
            try:
                match = re.search(r'\[.*\]', response, re.DOTALL)
                if match:
                    resources = json.loads(match.group())
                    if isinstance(resources, list):
                        return resources
            except json.JSONDecodeError:
                logger.error("❌ Could not parse learning resources JSON")

        return [
            {
                "skill": skill,
                "url": f"https://www.coursera.org/courses?query={skill.replace(' ', '+')}",
                "platform": "Coursera",
                "description": f"Courses for {skill}"
            }
            for skill in skills
        ]

    # ─── Learning Roadmap ─────────────────────────────────────────
    def generate_learning_roadmap(
        self,
        current_skills: List[str],
        target_role: str
    ) -> Dict:
        """Generate a personalized learning roadmap"""
        if not self.available:
            return self._unavailable_response(
                "Learning roadmap generation unavailable."
            )

        skills_str = ', '.join(current_skills[:20]) if current_skills else 'Not specified'

        prompt = f"""
Create a personalized learning roadmap for someone wanting to become a {target_role}.
Return ONLY a valid JSON object. No extra text.

Current Skills: {skills_str}
Target Role: {target_role}

Return this exact JSON structure:
{{
    "target_role": "{target_role}",
    "estimated_duration": "<e.g. 3-6 months>",
    "current_level": "<beginner/intermediate/advanced>",
    "phases": [
        {{
            "phase": 1,
            "title": "<phase title>",
            "duration": "<e.g. 1 month>",
            "skills": ["<skill1>", "<skill2>"],
            "resources": ["<resource1>", "<resource2>"]
        }}
    ],
    "final_skills": ["<skill1>", "<skill2>"]
}}
"""
        response = self._call_gemini(prompt)
        result = self._extract_json(response)

        if result:
            result['ai_powered'] = True
            return result

        return self._unavailable_response(
            "Could not generate roadmap. Please try again."
        )

    # ─── Interview Questions ───────────────────────────────────────
    def generate_interview_questions(
        self,
        resume_data: Dict,
        job_data: Dict
    ) -> List[Dict]:
        """Generate personalized interview questions"""
        if not self.available:
            return self._default_interview_questions(resume_data)

        skills = resume_data.get('skills', [])[:10]
        job_title = job_data.get('title', 'Software Engineer')
        job_description = job_data.get('description', '')[:2000]

        prompt = f"""
Generate 6 interview questions for a {job_title} position.
Return ONLY a valid JSON array. No extra text.

Candidate Skills: {', '.join(skills) if skills else 'Not specified'}
Job Description: {job_description}

Return this exact JSON structure:
[
    {{
        "category": "<technical/behavioral/situational>",
        "question": "<specific interview question>",
        "sample_answer": "<brief guide for answering>",
        "difficulty": "<easy/medium/hard>"
    }}
]
"""
        response = self._call_gemini(prompt)

        if response:
            try:
                match = re.search(r'\[.*\]', response, re.DOTALL)
                if match:
                    questions = json.loads(match.group())
                    if isinstance(questions, list) and len(questions) > 0:
                        return questions
            except json.JSONDecodeError:
                logger.error("❌ Could not parse interview questions JSON")

        return self._default_interview_questions(resume_data)

    def _default_interview_questions(self, resume_data: Dict) -> List[Dict]:
        """Return generic questions when AI unavailable"""
        skills = resume_data.get('skills', ['your primary skill'])
        first_skill = skills[0] if skills else 'your primary skill'

        return [
            {
                "category": "technical",
                "question": f"Can you describe your experience with {first_skill}?",
                "sample_answer": "Describe specific projects and measurable outcomes.",
                "difficulty": "medium",
                "ai_powered": False
            },
            {
                "category": "behavioral",
                "question": "Tell me about a challenging project you worked on.",
                "sample_answer": "Use the STAR method: Situation, Task, Action, Result.",
                "difficulty": "medium",
                "ai_powered": False
            },
            {
                "category": "situational",
                "question": "How do you handle tight deadlines?",
                "sample_answer": "Focus on prioritization and communication.",
                "difficulty": "easy",
                "ai_powered": False
            }
        ]

    # ─── GitHub Analysis ──────────────────────────────────────────
    async def analyze_github(self, username: str) -> Dict:
        """Analyze GitHub profile using public API"""
        if not username or not username.strip():
            return {"error": "Username is required"}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                user_response = await client.get(
                    f"https://api.github.com/users/{username}",
                    headers={"Accept": "application/vnd.github.v3+json"}
                )

                if user_response.status_code == 404:
                    return {"error": f"GitHub user '{username}' not found"}

                if user_response.status_code != 200:
                    return {"error": "Could not fetch GitHub profile"}

                user_data = user_response.json()

                repos_response = await client.get(
                    f"https://api.github.com/users/{username}/repos",
                    params={"sort": "updated", "per_page": 20},
                    headers={"Accept": "application/vnd.github.v3+json"}
                )

                repos = repos_response.json() if repos_response.status_code == 200 else []

                languages = {}
                repo_list = []

                for repo in repos:
                    if isinstance(repo, dict) and not repo.get('fork', False):
                        lang = repo.get('language')
                        if lang:
                            languages[lang] = languages.get(lang, 0) + 1

                        repo_list.append({
                            "name": repo.get('name', ''),
                            "description": repo.get('description', ''),
                            "stars": repo.get('stargazers_count', 0),
                            "language": lang,
                            "url": repo.get('html_url', '')
                        })

                result = {
                    "ai_powered": False,
                    "username": username,
                    "name": user_data.get('name', username),
                    "bio": user_data.get('bio', ''),
                    "public_repos": user_data.get('public_repos', 0),
                    "followers": user_data.get('followers', 0),
                    "following": user_data.get('following', 0),
                    "repositories": repo_list[:10],
                    "languages": languages,
                    "contributions": {
                        "public_repos": user_data.get('public_repos', 0)
                    }
                }

                if self.available and repo_list:
                    ai_analysis = await self._analyze_github_with_ai(
                        username, languages, repo_list
                    )
                    result['analysis_result'] = ai_analysis
                    result['ai_powered'] = True
                else:
                    result['analysis_result'] = {
                        "message": "AI analysis unavailable"
                    }

                return result

        except httpx.TimeoutException:
            logger.error(f"❌ GitHub API timeout for user: {username}")
            return {"error": "GitHub API request timed out"}
        except Exception as e:
            logger.error(f"❌ GitHub analysis error: {e}")
            return {"error": "Could not analyze GitHub profile"}

    async def _analyze_github_with_ai(
        self,
        username: str,
        languages: Dict,
        repos: List[Dict]
    ) -> Dict:
        """Use Gemini to analyze GitHub profile"""
        prompt = f"""
Analyze this GitHub profile and return ONLY a valid JSON object.

Username: {username}
Languages: {languages}
Top Repositories: {repos[:5]}

Return this exact JSON structure:
{{
    "code_quality": "<assessment>",
    "activity_level": "<low/medium/high>",
    "primary_focus": "<e.g. web development>",
    "strengths": ["<strength1>", "<strength2>"],
    "suggestions": ["<suggestion1>", "<suggestion2>"]
}}
"""
        response = self._call_gemini(prompt)
        result = self._extract_json(response)

        return result if result else {"message": "AI analysis could not be generated"}

    # ─── Chat With Resume ─────────────────────────────────────────
    def chat_with_resume(
        self,
        resume_data: Dict,
        user_message: str,
        chat_history: List = None
    ) -> str:
        """Chat with AI about resume content"""
        if not self.available:
            return self._unavailable_text("Chat")

        name = resume_data.get('name', 'the candidate')
        skills = resume_data.get('skills', [])[:15]
        full_text = resume_data.get('full_text', '')[:2000]

        history_text = ""
        if chat_history:
            ordered_history = list(reversed(chat_history))
            for entry in ordered_history[-5:]:
                history_text += f"User: {entry.get('user_message', '')}\n"
                history_text += f"Assistant: {entry.get('ai_response', '')}\n"

        prompt = f"""
You are a helpful career advisor with access to this candidate's resume.
Answer questions specifically about their resume and career.
Be concise, helpful and specific.

Resume Summary:
- Candidate: {name}
- Skills: {', '.join(skills) if skills else 'Not specified'}
- Resume Content: {full_text}

Previous Conversation:
{history_text if history_text else 'No previous conversation'}

Current Question: {user_message}

Provide a helpful, specific answer based on the resume content.
"""
        response = self._call_gemini(prompt, temperature=0.5)

        if response:
            return response

        return self._unavailable_text("Chat")