"""
GURUKUL AI Resume Screening Service
===================================
Student Academic Project Implementation:
Core NLP Resume Screening Engine based on TF-IDF Vectorization, Cosine Similarity,
and Explainable Required-Skill Matching.

ACADEMIC DEFENSE OVERVIEW:
--------------------------
1. Why TF-IDF (Term Frequency - Inverse Document Frequency)?
   - Term Frequency (TF) measures how frequently a term appears in a document.
   - Inverse Document Frequency (IDF) scales down common non-discriminative words 
     and scales up rare, domain-specific terminology (e.g., "Loksewa", "Django", "Pedagogy").
   - Result: Emphasizes unique skills and job qualifications while dampening noise.

2. Why Cosine Similarity?
   - Cosine Similarity calculates the cosine of the angle between two multi-dimensional 
     TF-IDF vectors:
       cos(theta) = (A . B) / (||A|| * ||B||)
   - Crucially, Cosine Similarity is length-invariant: a candidate with a concise 1-page 
     targeted resume is not penalized against a candidate with an overly verbose 5-page CV.
   - Values range from 0.0 (no overlapping terms) to 1.0 (identical term distributions).

3. Explainable Required-Skill Matching:
   - Directly checks each required skill from Job.required_skills against normalized resume text.
   - Categorizes each skill cleanly as MATCHED or MISSING.
   - Preserves original skill nomenclature for human evaluator readability.

4. Conservative Qualification & Experience Verification:
   - Detects academic degree tiers and numeric experience statements when clearly present.
   - If information is missing or ambiguous, marks as 'Needs Verification' rather than 
     hallucinating or inventing a result.

5. Ethical AI & Decision Support Guarantee:
   - This service is strictly a DECISION-SUPPORT TOOL for human administrators.
   - It NEVER automatically rejects or hires any applicant.
   - Final evaluation and employment decisions remain 100% human-controlled.
"""

import re
from typing import Dict, Any, List, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def clean_text(text: Optional[str]) -> str:
    """
    Cleans and standardizes raw input text for TF-IDF NLP processing.

    Steps:
    1. Converts text to lowercase to ensure case-insensitivity.
    2. Replaces punctuation and special characters with spaces (preserves letters and digits).
    3. Normalizes repeated whitespace into single spaces.
    4. Strips leading and trailing spaces.

    Academic Defense Note:
    Standardizing ensures that tokens like "Python", "python", and "Python," 
    are treated as identical terms by the vectorizer.
    """
    if not text:
        return ""
    
    # 1. Lowercase
    cleaned = text.lower()
    
    # 2. Remove punctuation and non-alphanumeric symbols (preserve letters, digits, and spaces)
    cleaned = re.sub(r'[^a-z0-9\s]', ' ', cleaned)
    
    # 3. Collapse multiple whitespaces and strip boundaries
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    return cleaned


def normalize_for_matching(text: Optional[str]) -> str:
    """
    Normalizes text specifically for keyword and skill matching:
    - Lowercase conversion
    - Whitespace normalization
    - Basic punctuation handling (preserves '+' and '#' for C++, C#, .NET, 10+2, 2+)
    """
    if not text:
        return ""
    normalized = text.lower()
    # Replace general punctuation characters with space, preserving alphanumeric and technical characters (+, #)
    normalized = re.sub(r'[^a-z0-9+#\s]', ' ', normalized)
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    return normalized


def match_required_skills(required_skills: Optional[str], resume_text: Optional[str]) -> Dict[str, Any]:
    """
    Compares the job's required skills against the extracted resume text.
    Determines for each required skill: MATCHED or MISSING.

    INPUT:
    - required_skills: String of required skills (comma-separated, semicolon-separated, or newline-separated).
    - resume_text: Extracted text from candidate's CV.

    NORMALIZATION:
    - lowercase
    - whitespace normalization
    - basic punctuation handling

    RETURNS:
    - matched_skills: List of original skill strings found in CV.
    - missing_skills: List of original skill strings missing from CV.
    - skill_details: List of dicts with each skill and its MATCHED/MISSING status.
    - matched_count, missing_count, total_skills, skills_match_percentage.

    Academic Defense Principle:
    Simple, deterministic keyword matching with word-boundary awareness so 'Git'
    does not falsely match within 'digital', and multi-word phrases match accurately.
    """
    if not required_skills or not required_skills.strip():
        return {
            'matched_skills': [],
            'missing_skills': [],
            'total_skills': 0,
            'matched_count': 0,
            'missing_count': 0,
            'skills_match_percentage': 0.0,
            'skill_details': []
        }

    # Split by commas, semicolons, or newlines
    raw_skills = re.split(r'[,;\n]+', required_skills)
    skill_names = [s.strip() for s in raw_skills if s.strip()]

    normalized_resume = normalize_for_matching(resume_text)

    matched_skills: List[str] = []
    missing_skills: List[str] = []
    skill_details: List[Dict[str, str]] = []

    for original_skill in skill_names:
        cleaned_skill = normalize_for_matching(original_skill)
        if not cleaned_skill:
            continue

        # Use word boundaries or whitespace boundary matching
        # Matches exact word or multi-word phrase
        pattern = rf"(?:\b|\s|^){re.escape(cleaned_skill)}(?:\b|\s|$)"
        if re.search(pattern, normalized_resume):
            matched_skills.append(original_skill)
            skill_details.append({'skill': original_skill, 'status': 'MATCHED'})
        else:
            missing_skills.append(original_skill)
            skill_details.append({'skill': original_skill, 'status': 'MISSING'})

    total = len(matched_skills) + len(missing_skills)
    match_pct = round((len(matched_skills) / total) * 100.0, 1) if total > 0 else 0.0

    return {
        'matched_skills': matched_skills,
        'missing_skills': missing_skills,
        'total_skills': total,
        'matched_count': len(matched_skills),
        'missing_count': len(missing_skills),
        'skills_match_percentage': match_pct,
        'skill_details': skill_details
    }


def evaluate_qualification(job_qualification: Optional[str], resume_text: Optional[str]) -> Dict[str, str]:
    """
    Evaluates whether the candidate's CV text demonstrates the required qualification.

    Academic Defense Principle:
    Strict conservative verification: If the information cannot be reasonably detected 
    from the provided data, returns 'Needs Verification' rather than inventing a result.
    """
    if not job_qualification or not job_qualification.strip():
        return {
            'status': 'Needs Verification',
            'detail': 'No explicit academic qualification specified in job vacancy.'
        }

    if not resume_text or not resume_text.strip():
        return {
            'status': 'Needs Verification',
            'detail': 'Candidate CV text is missing or unreadable.'
        }

    norm_job_qual = normalize_for_matching(job_qualification)
    norm_resume = normalize_for_matching(resume_text)

    # Degree hierarchy tiers:
    # Tier 5: Doctorate / PhD
    # Tier 4: Master's / Postgraduate
    # Tier 3: Bachelor's / Undergraduate
    # Tier 2: Intermediate / +2 / Higher Secondary
    # Tier 1: Secondary / SEE / SLC
    DEGREE_TIERS = {
        'doctorate': (5, ['phd', 'doctorate', 'ph d', 'doctoral']),
        'master': (4, ['master', 'masters', 'postgraduate', 'msc', 'm sc', 'm a', 'mba', 'mbs', 'm ed', 'm tech', 'me']),
        'bachelor': (3, ['bachelor', 'bachelors', 'undergraduate', 'bsc', 'b sc', 'b a', 'bba', 'bbs', 'b ed', 'b tech', 'be', 'bca', 'bit']),
        'intermediate': (2, ['10+2', '+2', 'intermediate', 'plus two', 'higher secondary', 'a level', '12th']),
        'secondary': (1, ['see', 'slc', 'secondary education', '10th grade', 'grade 10', 'high school']),
    }

    # Detect required degree tier from vacancy
    target_tier = None
    target_tier_name = None
    for tier_name, (level, keywords) in DEGREE_TIERS.items():
        for kw in keywords:
            if re.search(rf"\b{re.escape(kw)}\b", norm_job_qual):
                if target_tier is None or level > target_tier:
                    target_tier = level
                    target_tier_name = tier_name.capitalize()
                break

    # If job doesn't specify a standard degree tier (e.g. "Relevant Certification", "Open")
    if target_tier is None:
        qual_words = [w for w in norm_job_qual.split() if len(w) > 3]
        matched_words = [w for w in qual_words if re.search(rf"\b{re.escape(w)}\b", norm_resume)]
        if len(matched_words) >= max(1, len(qual_words) // 2):
            return {
                'status': 'Matched',
                'detail': f'Qualification keywords detected in CV ({", ".join(matched_words)}).'
            }
        return {
            'status': 'Needs Verification',
            'detail': 'Job qualification does not specify a standard degree tier; manual verification recommended.'
        }

    # Detect candidate's highest degree in CV
    candidate_tier = None
    candidate_tier_name = None
    detected_kw = None
    for tier_name, (level, keywords) in DEGREE_TIERS.items():
        for kw in keywords:
            if re.search(rf"\b{re.escape(kw)}\b", norm_resume):
                if candidate_tier is None or level > candidate_tier:
                    candidate_tier = level
                    candidate_tier_name = tier_name.capitalize()
                    detected_kw = kw
                break

    if candidate_tier is None:
        return {
            'status': 'Needs Verification',
            'detail': f'Requires {target_tier_name} degree; no clear degree credentials detected in CV text.'
        }

    if candidate_tier >= target_tier:
        return {
            'status': 'Matched',
            'detail': f'Candidate holds {candidate_tier_name} level qualification (detected "{detected_kw}"), meeting the {target_tier_name} requirement.'
        }
    else:
        return {
            'status': 'Not Matched',
            'detail': f'Requires {target_tier_name} level qualification, but CV only indicates {candidate_tier_name} level.'
        }


def evaluate_experience(job_experience: Optional[str], resume_text: Optional[str]) -> Dict[str, str]:
    """
    Evaluates whether the candidate's CV text demonstrates the required experience duration.

    Academic Defense Principle:
    Strict conservative verification: If the information cannot be reasonably detected 
    from the provided data, returns 'Needs Verification' rather than inventing a result.
    """
    if not job_experience or not job_experience.strip():
        return {
            'status': 'Needs Verification',
            'detail': 'No explicit experience duration specified in job requirements.'
        }

    if not resume_text or not resume_text.strip():
        return {
            'status': 'Needs Verification',
            'detail': 'Candidate CV text is missing or unreadable.'
        }

    norm_job_exp = normalize_for_matching(job_experience)
    norm_resume = normalize_for_matching(resume_text)

    # 1. Check for freshers allowed
    fresher_indicators = ['fresher', 'freshers', 'entry level', '0 year', 'no experience', 'fresh graduate']
    for ind in fresher_indicators:
        if ind in norm_job_exp:
            return {
                'status': 'Matched',
                'detail': 'Job vacancy explicitly accepts freshers or candidates without prior experience.'
            }

    # 2. Extract numeric required years from job experience (e.g., "2+ Years", "3-5 years")
    job_match = re.search(r'(\d+)\s*(?:\+|to|-|\s)*\s*(?:years?|yrs?)', norm_job_exp)
    if not job_match:
        job_match = re.search(r'(\d+)\s*(?:years?|yrs?)', norm_job_exp)

    if not job_match:
        return {
            'status': 'Needs Verification',
            'detail': 'Specific experience years could not be parsed from job requirements.'
        }

    try:
        required_years = int(job_match.group(1))
    except ValueError:
        return {
            'status': 'Needs Verification',
            'detail': 'Could not parse numerical years from job requirements.'
        }

    # 3. Detect candidate experience years in resume
    candidate_exp_patterns = [
        r'(\d+)\+?\s*(?:to|-)?\s*\d*\s*(?:years?|yrs?)\s*(?:of\s*)?(?:teaching|work|professional|industry|relevant)?\s*experience',
        r'(\d+)\+?\s*(?:years?|yrs?)\s*(?:of\s*)?(?:teaching|work|experience|tutoring|practice)',
        r'experience\s*(?:of|:)?\s*(\d+)\+?\s*(?:years?|yrs?)',
        r'(\d+)\+?\s*(?:years?|yrs?)\s*in\s*(?:teaching|education|development|engineering|administration)',
    ]

    detected_years = []
    for pat in candidate_exp_patterns:
        matches = re.findall(pat, norm_resume)
        for m in matches:
            if isinstance(m, str) and m.isdigit():
                detected_years.append(int(m))
            elif isinstance(m, tuple) and m[0].isdigit():
                detected_years.append(int(m[0]))

    if not detected_years:
        return {
            'status': 'Needs Verification',
            'detail': f'Job requires {required_years}+ year(s) experience; explicit duration not stated in CV text.'
        }

    max_candidate_years = max(detected_years)

    if max_candidate_years >= required_years:
        return {
            'status': 'Matched',
            'detail': f'Candidate mentions {max_candidate_years} year(s) experience, satisfying the {required_years}+ year requirement.'
        }
    else:
        return {
            'status': 'Not Matched',
            'detail': f'Candidate mentions {max_candidate_years} year(s) experience, which is below the required {required_years}+ year(s).'
        }


class ResumeScreeningService:
    """
    Reusable AI Service for screening candidate resumes against job specifications.
    Combines scikit-learn TF-IDF cosine similarity, required-skills matching,
    and conservative qualification & experience verification.
    """

    MIN_WORDS_THRESHOLD = 5

    @classmethod
    def calculate_match(
        cls,
        job_description: Optional[str],
        required_skills: Optional[str],
        resume_text: Optional[str],
        job_qualification: Optional[str] = None,
        job_experience: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executes the end-to-end NLP matching pipeline.

        INPUTS:
        1. job_description: Text detailing job duties and expectations.
        2. required_skills: Comma-separated or listed skills and competencies.
        3. resume_text: Extracted plain text from the candidate's PDF CV.
        4. job_qualification: Optional qualification requirement string.
        5. job_experience: Optional experience requirement string.

        RETURNS:
        Structured dictionary with match_percentage, similarity_score, job_vector,
        resume_vector, matched_keywords, matched_skills, missing_skills,
        qualification_match, experience_match, status, and error_message.
        """

        # -------------------------------------------------------------
        # 1. ERROR HANDLING & VALIDATION
        # -------------------------------------------------------------

        # Check for empty or missing job description
        if not job_description or not job_description.strip():
            return cls._build_error_response(
                status='ERROR',
                error_type='EMPTY_JOB_DESCRIPTION',
                message='Job description is empty or missing.'
            )

        # Check for empty or missing candidate resume text
        if not resume_text or not resume_text.strip():
            return cls._build_error_response(
                status='ERROR',
                error_type='EMPTY_CV_TEXT',
                message='Candidate resume text is empty or missing.'
            )

        # Check for known extraction failure flags in resume text
        if resume_text.startswith('[EXTRACTION_ERROR]') or 'could not extract text' in resume_text.lower():
            return cls._build_error_response(
                status='ERROR',
                error_type='EXTRACTION_FAILURE',
                message='Resume text extraction failed or document contains unreadable scanned content.'
            )

        # -------------------------------------------------------------
        # 2. REQUIRED SKILLS, QUALIFICATION & EXPERIENCE MATCHING
        # -------------------------------------------------------------
        skill_analysis = match_required_skills(required_skills, resume_text)
        qual_analysis = evaluate_qualification(job_qualification, resume_text)
        exp_analysis = evaluate_experience(job_experience, resume_text)

        # -------------------------------------------------------------
        # 3. COMBINE JOB DESCRIPTION AND REQUIRED SKILLS
        # -------------------------------------------------------------
        safe_skills = (required_skills or "").strip()
        job_text = f"{job_description.strip()} {safe_skills}".strip()

        # -------------------------------------------------------------
        # 4. CLEAN TEXT
        # -------------------------------------------------------------
        cleaned_job = clean_text(job_text)
        cleaned_resume = clean_text(resume_text)

        job_words = cleaned_job.split()
        resume_words = cleaned_resume.split()

        # Check for insufficient text content
        if len(job_words) < cls.MIN_WORDS_THRESHOLD:
            resp = cls._build_error_response(
                status='INSUFFICIENT_TEXT',
                error_type='INSUFFICIENT_JOB_TEXT',
                message=f'Insufficient job description text ({len(job_words)} words). Minimum {cls.MIN_WORDS_THRESHOLD} words required.',
                job_word_count=len(job_words),
                resume_word_count=len(resume_words)
            )
            resp.update({
                'matched_skills': skill_analysis['matched_skills'],
                'missing_skills': skill_analysis['missing_skills'],
                'skills_match_percentage': skill_analysis['skills_match_percentage'],
                'qualification_match': qual_analysis['status'],
                'qualification_detail': qual_analysis['detail'],
                'experience_match': exp_analysis['status'],
                'experience_detail': exp_analysis['detail'],
            })
            return resp

        if len(resume_words) < cls.MIN_WORDS_THRESHOLD:
            resp = cls._build_error_response(
                status='INSUFFICIENT_TEXT',
                error_type='INSUFFICIENT_CV_TEXT',
                message=f'Insufficient resume text content ({len(resume_words)} words). Minimum {cls.MIN_WORDS_THRESHOLD} words required for reliable NLP screening.',
                job_word_count=len(job_words),
                resume_word_count=len(resume_words)
            )
            resp.update({
                'matched_skills': skill_analysis['matched_skills'],
                'missing_skills': skill_analysis['missing_skills'],
                'skills_match_percentage': skill_analysis['skills_match_percentage'],
                'qualification_match': qual_analysis['status'],
                'qualification_detail': qual_analysis['detail'],
                'experience_match': exp_analysis['status'],
                'experience_detail': exp_analysis['detail'],
            })
            return resp

        # -------------------------------------------------------------
        # 5. TF-IDF VECTORIZATION
        # -------------------------------------------------------------
        try:
            vectorizer = TfidfVectorizer(
                stop_words='english',
                norm='l2',
                lowercase=True
            )
            tfidf_matrix = vectorizer.fit_transform([cleaned_job, cleaned_resume])
        except ValueError:
            resp = cls._build_error_response(
                status='INSUFFICIENT_TEXT',
                error_type='EMPTY_VOCABULARY',
                message='No informative keywords remained after filtering English stop words.',
                job_word_count=len(job_words),
                resume_word_count=len(resume_words)
            )
            resp.update({
                'matched_skills': skill_analysis['matched_skills'],
                'missing_skills': skill_analysis['missing_skills'],
                'skills_match_percentage': skill_analysis['skills_match_percentage'],
                'qualification_match': qual_analysis['status'],
                'qualification_detail': qual_analysis['detail'],
                'experience_match': exp_analysis['status'],
                'experience_detail': exp_analysis['detail'],
            })
            return resp

        feature_names = vectorizer.get_feature_names_out()

        job_sparse = tfidf_matrix[0:1]
        resume_sparse = tfidf_matrix[1:2]

        # -------------------------------------------------------------
        # 6. CALCULATE COSINE SIMILARITY
        # -------------------------------------------------------------
        similarity_matrix = cosine_similarity(job_sparse, resume_sparse)
        raw_similarity = float(similarity_matrix[0][0])
        similarity_score = max(0.0, min(1.0, raw_similarity))
        match_percentage = round(similarity_score * 100.0, 2)

        # -------------------------------------------------------------
        # 7. EXTRACT STRUCTURED VECTORS & MATCHED KEYWORDS
        # -------------------------------------------------------------
        job_dense = job_sparse.toarray()[0]
        resume_dense = resume_sparse.toarray()[0]

        job_vector: Dict[str, float] = {}
        resume_vector: Dict[str, float] = {}

        for idx in job_dense.nonzero()[0]:
            term = str(feature_names[idx])
            job_vector[term] = round(float(job_dense[idx]), 4)

        for idx in resume_dense.nonzero()[0]:
            term = str(feature_names[idx])
            resume_vector[term] = round(float(resume_dense[idx]), 4)

        job_vector = dict(sorted(job_vector.items(), key=lambda item: item[1], reverse=True))
        resume_vector = dict(sorted(resume_vector.items(), key=lambda item: item[1], reverse=True))

        common_terms = set(job_vector.keys()).intersection(set(resume_vector.keys()))
        matched_keywords: List[Dict[str, Any]] = []

        for term in common_terms:
            j_weight = job_vector[term]
            r_weight = resume_vector[term]
            contribution = round(j_weight * r_weight, 4)
            matched_keywords.append({
                'term': term,
                'job_weight': j_weight,
                'resume_weight': r_weight,
                'contribution': contribution
            })

        matched_keywords.sort(key=lambda x: x['contribution'], reverse=True)

        # -------------------------------------------------------------
        # 8. RETURN STRUCTURED RESULT
        # -------------------------------------------------------------
        return {
            'status': 'SUCCESS',
            'match_percentage': match_percentage,
            'similarity_score': round(similarity_score, 4),
            'job_vector': job_vector,
            'resume_vector': resume_vector,
            'matched_keywords': matched_keywords,
            'matched_terms_count': len(matched_keywords),
            'matched_skills': skill_analysis['matched_skills'],
            'missing_skills': skill_analysis['missing_skills'],
            'skill_details': skill_analysis['skill_details'],
            'skills_match_percentage': skill_analysis['skills_match_percentage'],
            'qualification_match': qual_analysis['status'],
            'qualification_detail': qual_analysis['detail'],
            'experience_match': exp_analysis['status'],
            'experience_detail': exp_analysis['detail'],
            'total_vocabulary_size': len(feature_names),
            'job_word_count': len(job_words),
            'resume_word_count': len(resume_words),
            'error_message': None,
            'is_decision_support_only': True,
        }

    @classmethod
    def _build_error_response(
        cls,
        status: str,
        error_type: str,
        message: str,
        job_word_count: int = 0,
        resume_word_count: int = 0
    ) -> Dict[str, Any]:
        """
        Helper method to construct standardized error payloads without crashing.
        """
        return {
            'status': status,
            'error_type': error_type,
            'error_message': message,
            'match_percentage': 0.0,
            'similarity_score': 0.0,
            'job_vector': {},
            'resume_vector': {},
            'matched_keywords': [],
            'matched_terms_count': 0,
            'matched_skills': [],
            'missing_skills': [],
            'skill_details': [],
            'skills_match_percentage': 0.0,
            'qualification_match': 'Needs Verification',
            'qualification_detail': message,
            'experience_match': 'Needs Verification',
            'experience_detail': message,
            'total_vocabulary_size': 0,
            'job_word_count': job_word_count,
            'resume_word_count': resume_word_count,
            'is_decision_support_only': True,
        }


# Convenience alias for functional imports
calculate_resume_match = ResumeScreeningService.calculate_match


def generate_explanation(
    matched_skills: List[str],
    missing_skills: List[str],
    qualification_match: str,
    experience_match: str,
    match_percentage: float = 0.0,
    qualification_detail: Optional[str] = None,
    experience_detail: Optional[str] = None
) -> str:
    """
    Generates a natural, explainable, rule-based summary derived directly from the
    quantitative analysis results without inventing candidate information.

    Example output:
    "The candidate's resume contains several skills required for this position, including
    Python, Django, HTML and MySQL. The skill Git was not identified in the uploaded resume.
    The qualification and experience information should be verified by the administrator."
    """
    sentences: List[str] = []

    # 1. Matched skills phrase
    if matched_skills:
        if len(matched_skills) == 1:
            skill_str = matched_skills[0]
            phrase = f"one required skill, specifically {skill_str}"
        elif len(matched_skills) <= 3:
            skill_str = ", ".join(matched_skills[:-1]) + f" and {matched_skills[-1]}"
            phrase = f"{len(matched_skills)} skills required for this position, including {skill_str}"
        else:
            skill_str = ", ".join(matched_skills[:-1]) + f" and {matched_skills[-1]}"
            phrase = f"several skills required for this position, including {skill_str}"
        sentences.append(f"The candidate's resume contains {phrase}.")
    else:
        sentences.append("None of the skills explicitly required for this position were identified in the candidate's resume.")

    # 2. Missing skills phrase
    if missing_skills:
        if len(missing_skills) == 1:
            sentences.append(f"The skill {missing_skills[0]} was not identified in the uploaded resume.")
        else:
            missing_str = ", ".join(missing_skills[:-1]) + f" and {missing_skills[-1]}"
            sentences.append(f"The skills {missing_str} were not identified in the uploaded resume.")
    elif matched_skills:
        sentences.append("All skills specified in the job posting were identified in the candidate's resume.")

    # 3. Qualification & Experience review phrase
    if qualification_match == 'Needs Verification' and experience_match == 'Needs Verification':
        sentences.append("The qualification and experience information should be verified by the administrator.")
    elif qualification_match == 'Needs Verification':
        if experience_match == 'Matched':
            sentences.append("Work experience meets the specified duration, while qualification credentials should be verified by the administrator.")
        elif experience_match == 'Not Matched':
            sentences.append("Work experience appears below the stated requirement, and qualification credentials should be verified by the administrator.")
        else:
            sentences.append("The qualification information should be verified by the administrator.")
    elif experience_match == 'Needs Verification':
        if qualification_match == 'Matched':
            sentences.append("Academic qualifications appear to satisfy position requirements, while experience history should be verified by the administrator.")
        elif qualification_match == 'Not Matched':
            sentences.append("Academic qualifications appear below the required tier, and experience history should be verified by the administrator.")
        else:
            sentences.append("The experience information should be verified by the administrator.")
    else:
        q_text = "Academic qualification satisfies the requirement" if qualification_match == 'Matched' else "Academic qualification appears below the requirement"
        e_text = "work experience meets the specified duration." if experience_match == 'Matched' else "work experience duration appears below the requirement."
        sentences.append(f"{q_text}, and {e_text}")

    return " ".join(sentences)

