import re
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

class JobMatcher:
    def __init__(self):
        # Basic stop words to ignore during text comparison
        self.stop_words = {
            'the', 'and', 'is', 'in', 'it', 'of', 'to', 'a', 'for', 'on', 
            'with', 'as', 'by', 'an', 'be', 'this', 'that', 'are', 'from', 
            'or', 'at', 'not', 'but', 'have', 'has', 'was', 'were', 'will',
            'we', 'our', 'you', 'your', 'can', 'may', 'should', 'would'
        }
        
        # Common skill aliases for better matching
        self.skill_aliases = {
            'js': 'javascript',
            'ts': 'typescript',
            'py': 'python',
            'react.js': 'react',
            'reactjs': 'react',
            'node': 'node.js',
            'nodejs': 'node.js',
            'express.js': 'express',
            'expressjs': 'express',
            'vue.js': 'vue',
            'vuejs': 'vue',
            'next.js': 'nextjs',
            'nuxt.js': 'nuxtjs',
            'aws': 'amazon web services',
            'gcp': 'google cloud platform',
            'ml': 'machine learning',
            'ai': 'artificial intelligence',
            'ds': 'data science',
            'postgres': 'postgresql',
            'mongo': 'mongodb',
            'k8s': 'kubernetes',
            'tf': 'terraform',
            'ci/cd': 'cicd',
        }

    def _normalize_skills(self, skills: List[str]) -> set:
        """Normalize skills to handle aliases and formatting"""
        normalized = set()
        for skill in skills:
            clean_skill = skill.lower().strip()
            # Map alias to standard name if exists
            standard_skill = self.skill_aliases.get(clean_skill, clean_skill)
            normalized.add(standard_skill)
        return normalized

    def _tokenize(self, text: str) -> set:
        """Convert text to a set of meaningful words"""
        if not text:
            return set()
        # Extract alphanumeric words
        words = re.findall(r'\b[a-z0-9\+\#\.]+\b', text.lower())
        # Remove stop words
        return {w for w in words if w not in self.stop_words and len(w) > 1}

    def _jaccard_similarity(self, text1: str, text2: str) -> float:
        """Calculate Jaccard similarity between two texts (0.0 to 1.0)"""
        set1 = self._tokenize(text1)
        set2 = self._tokenize(text2)
        
        if not set1 or not set2:
            return 0.0
            
        intersection = set1.intersection(set2)
        union = set1.union(set2)
        
        return len(intersection) / len(union)

    def match(self, resume_text: str, job_text: str, resume_skills: List[str], job_skills: List[str]) -> Dict:
        """Match resume against job description"""
        try:
            # 1. Calculate Skill Overlap
            norm_resume_skills = self._normalize_skills(resume_skills or [])
            norm_job_skills = self._normalize_skills(job_skills or [])
            
            matching_skills = list(norm_resume_skills.intersection(norm_job_skills))
            missing_skills = list(norm_job_skills - norm_resume_skills)
            
            if norm_job_skills:
                skill_overlap = len(matching_skills) / len(norm_job_skills)
            else:
                skill_overlap = 0.0  # No job skills provided, don't fake a score

            # 2. Calculate Text Similarity (TF-IDF replacement)
            text_similarity = self._jaccard_similarity(resume_text, job_text)

            # 3. Calculate Final Score
            if norm_job_skills:
                # Weighted score: 60% skills, 40% text context
                raw_score = (skill_overlap * 0.6) + (text_similarity * 0.4)
            else:
                # Only text similarity if no skills provided
                raw_score = text_similarity

            # Convert to percentage and clamp between 0 and 100
            final_score = max(0.0, min(100.0, round(raw_score * 100, 2)))

            return {
                'overall_match': final_score,
                'text_similarity': round(text_similarity * 100, 2),
                'skill_overlap': round(skill_overlap * 100, 2),
                'matching_skills': matching_skills,
                'missing_skills': missing_skills,
                'match_percentage': f"{int(final_score)}%"
            }

        except Exception as e:
            logger.error(f"Error in job matching: {e}")
            # Return safe fallback without faking a high score
            return {
                'overall_match': 0.0,
                'text_similarity': 0.0,
                'skill_overlap': 0.0,
                'matching_skills': [],
                'missing_skills': job_skills or [],
                'match_percentage': "0%",
                'error': 'Matching failed'
            }