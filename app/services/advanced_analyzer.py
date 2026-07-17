import json
import re
import logging
import time
import httpx
from typing import Dict, List, Optional
from groq import Groq

logger = logging.getLogger(__name__)


class AdvancedAnalyzer:
    def __init__(self, api_key: str = None):
        self.available = False
        self.client = None

        try:
            from ..config import settings
            groq_key = settings.GROQ_API_KEY
            if groq_key:
                self.client = Groq(api_key=groq_key)
                self.available = True
                logger.info("✅ Groq AI client initialized for AdvancedAnalyzer")
                return
        except Exception as e:
            logger.error(f"❌ Failed to initialize Groq client: {e}")

        logger.warning("⚠️ No AI client available for AdvancedAnalyzer")

    def _get_model(self) -> str:
        try:
            from ..config import settings
            return settings.GROQ_MODEL
        except Exception:
            return "llama-3.3-70b-versatile"

    def _call_ai(
        self,
        prompt: str,
        temperature: float = 0.4,
        system: str = "You are a helpful AI assistant. Always respond with valid JSON when asked."
    ) -> Optional[str]:
        """Central Groq API caller with retry logic"""
        if not self.available or not self.client:
            return None

        max_retries = 3
        retry_delays = [5, 15, 30]

        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self._get_model(),
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=temperature,
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
                        logger.warning(f"⚠️ Rate limited. Retrying in {delay}s...")
                        time.sleep(delay)
                        continue
                    else:
                        logger.error("❌ Max retries reached")
                        return None

                return None

        return None

    def _extract_json(self, text: str) -> Optional[Dict]:
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
        logger.error("❌ Could not extract JSON from AI response")
        return None

    def _unavailable_response(self, message: str = "AI analysis unavailable.") -> Dict:
        return {"ai_powered": False, "message": message, "data": {}}

    def _unavailable_text(self, feature: str) -> str:
        return f"{feature} is currently unavailable. Please check your API key."

    # ─── Heatmap ──────────────────────────────────────────────────
    def generate_heatmap(self, resume_text: str) -> Dict:
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
        "<skill_name>": <number 0-100>
    }},
    "keyword_density": {{
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
        response = self._call_ai(prompt)
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
            "message": "Heatmap unavailable."
        }

    # ─── Rewrite Section ──────────────────────────────────────────
    def rewrite_resume_section(
        self,
        section_text: str,
        section_type: str = "experience",
        style: str = "professional"
    ) -> str:
        if not self.available:
            return self._unavailable_text("Section rewrite")

        prompt = f"""
Rewrite this {section_type} resume section in a {style} style.
Use strong action verbs and quantify achievements where possible.
Return ONLY the rewritten text, no explanations.

Original Text:
{section_text[:3000]}
"""
        response = self._call_ai(
            prompt,
            temperature=0.5,
            system="You are an expert resume writer."
        )
        return response if response else self._unavailable_text("Section rewrite")

    # ─── Cover Letter ─────────────────────────────────────────────
    def generate_cover_letter(self, resume_data: Dict, job_data: Dict) -> str:
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
Write a professional cover letter.
Return ONLY the cover letter text, no explanations.

Candidate:
- Name: {name}
- Skills: {', '.join(skills) if skills else 'Not specified'}
- Experience: {experience}
- Education: {education}

Job:
- Position: {job_title}
- Company: {company}
- Description: {job_description}

Write a compelling 3-paragraph cover letter.
"""
        response = self._call_ai(
            prompt,
            temperature=0.6,
            system="You are an expert cover letter writer."
        )
        return response if response else self._unavailable_text("Cover letter")

    # ─── Skill Gap ────────────────────────────────────────────────
    def analyze_skill_gap(
        self,
        current_skills: List[str],
        job_skills: List[str]
    ) -> Dict:
        if not current_skills and not job_skills:
            return {
                "ai_powered": False,
                "current_skills": [],
                "required_skills": [],
                "missing_skills": [],
                "matching_skills": [],
                "overlap_percentage": 0.0,
                "learning_resources": [],
                "message": "No skills provided."
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
For each skill suggest ONE learning resource.
Return ONLY a valid JSON array. No extra text.

Skills: {', '.join(skills)}

Return:
[
    {{
        "skill": "<skill>",
        "platform": "<platform>",
        "url": "<url>",
        "description": "<description>"
    }}
]
"""
        response = self._call_ai(prompt)
        if response:
            try:
                match = re.search(r'\[.*\]', response, re.DOTALL)
                if match:
                    resources = json.loads(match.group())
                    if isinstance(resources, list):
                        return resources
            except json.JSONDecodeError:
                pass

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
        if not self.available:
            return self._unavailable_response("Roadmap generation unavailable.")

        skills_str = (
            ', '.join(current_skills[:20])
            if current_skills
            else 'Not specified'
        )

        prompt = f"""
Create a learning roadmap for someone wanting to become a {target_role}.
Return ONLY a valid JSON object. No extra text.

Current Skills: {skills_str}
Target Role: {target_role}

Return:
{{
    "target_role": "{target_role}",
    "estimated_duration": "<e.g. 3-6 months>",
    "current_level": "<beginner/intermediate/advanced>",
    "phases": [
        {{
            "phase": 1,
            "title": "<title>",
            "duration": "<duration>",
            "skills": ["<skill1>"],
            "resources": ["<resource1>"]
        }}
    ],
    "final_skills": ["<skill1>"]
}}
"""
        response = self._call_ai(prompt)
        result = self._extract_json(response)

        if result:
            result['ai_powered'] = True
            return result

        return self._unavailable_response("Could not generate roadmap.")

    # ─── Interview Questions ───────────────────────────────────────
    def generate_interview_questions(
        self,
        resume_data: Dict,
        job_data: Dict
    ) -> List[Dict]:
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

Return:
[
    {{
        "category": "<technical/behavioral/situational>",
        "question": "<question>",
        "sample_answer": "<answer guide>",
        "difficulty": "<easy/medium/hard>"
    }}
]
"""
        response = self._call_ai(prompt)
        if response:
            try:
                match = re.search(r'\[.*\]', response, re.DOTALL)
                if match:
                    questions = json.loads(match.group())
                    if isinstance(questions, list) and len(questions) > 0:
                        return questions
            except json.JSONDecodeError:
                pass

        return self._default_interview_questions(resume_data)

    def _default_interview_questions(self, resume_data: Dict) -> List[Dict]:
        skills = resume_data.get('skills', ['your primary skill'])
        first_skill = skills[0] if skills else 'your primary skill'
        return [
            {
                "category": "technical",
                "question": f"Describe your experience with {first_skill}?",
                "sample_answer": "Describe specific projects and outcomes.",
                "difficulty": "medium",
                "ai_powered": False
            },
            {
                "category": "behavioral",
                "question": "Tell me about a challenging project.",
                "sample_answer": "Use STAR method.",
                "difficulty": "medium",
                "ai_powered": False
            },
            {
                "category": "situational",
                "question": "How do you handle tight deadlines?",
                "sample_answer": "Focus on prioritization.",
                "difficulty": "easy",
                "ai_powered": False
            }
        ]

    # ─── GitHub Analysis ──────────────────────────────────────────
    async def analyze_github(self, username: str) -> Dict:
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

                repos = (
                    repos_response.json()
                    if repos_response.status_code == 200
                    else []
                )

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
            logger.error(f"❌ GitHub API timeout for: {username}")
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
        prompt = f"""
Analyze this GitHub profile and return ONLY a valid JSON object.

Username: {username}
Languages: {languages}
Repositories: {repos[:5]}

Return:
{{
    "code_quality": "<assessment>",
    "activity_level": "<low/medium/high>",
    "primary_focus": "<focus area>",
    "strengths": ["<strength1>"],
    "suggestions": ["<suggestion1>"]
}}
"""
        response = self._call_ai(prompt)
        result = self._extract_json(response)
        return result if result else {"message": "AI analysis unavailable"}

    # ─── Chat With Resume ─────────────────────────────────────────
    def chat_with_resume(
        self,
        resume_data: Dict,
        user_message: str,
        chat_history: List = None
    ) -> str:
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
Resume:
- Name: {name}
- Skills: {', '.join(skills) if skills else 'Not specified'}
- Content: {full_text}

Previous Chat:
{history_text if history_text else 'None'}

Question: {user_message}
"""
        response = self._call_ai(
            prompt,
            temperature=0.5,
            system="You are a helpful career advisor. Answer questions about the candidate's resume specifically and concisely."
        )
        return response if response else self._unavailable_text("Chat")