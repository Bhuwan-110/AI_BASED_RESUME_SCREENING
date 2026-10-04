import json
from django.db import models
from applications.models import Application
from .extractor import extract_text_from_pdf
from .service import calculate_resume_match


class ResumeExtraction(models.Model):
    """
    Stores extracted text and metadata from an applicant's uploaded PDF CV.
    Keeps extracted text accessible to the AI screening / TF-IDF vectorizer module.
    """
    STATUS_SUCCESS = 'SUCCESS'
    STATUS_EMPTY = 'EMPTY'
    STATUS_ERROR = 'ERROR'
    STATUS_PENDING = 'PENDING'

    STATUS_CHOICES = [
        (STATUS_SUCCESS, 'Success'),
        (STATUS_EMPTY, 'Empty / No Text'),
        (STATUS_ERROR, 'Extraction Error'),
        (STATUS_PENDING, 'Pending'),
    ]

    application = models.OneToOneField(
        Application,
        on_delete=models.CASCADE,
        related_name='resume_extraction'
    )
    extracted_text = models.TextField(blank=True, default='')
    page_count = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    error_message = models.TextField(blank=True, default='')
    extracted_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-extracted_at']

    def __str__(self):
        return f"Extraction for {self.application.applicant.username} - {self.status}"

    @property
    def word_count(self):
        if not self.extracted_text:
            return 0
        return len(self.extracted_text.split())

    @classmethod
    def process_application_cv(cls, application):
        """
        Executes text extraction on an application's CV file, saves the extraction,
        and automatically triggers the NLP screening pipeline.
        """
        if not application.cv:
            extraction, _ = cls.objects.update_or_create(
                application=application,
                defaults={
                    'extracted_text': '',
                    'page_count': 0,
                    'status': cls.STATUS_ERROR,
                    'error_message': 'No CV file attached to this application.',
                }
            )
            ResumeScreening.screen_application(application)
            return extraction

        result = extract_text_from_pdf(application.cv)

        extraction, _ = cls.objects.update_or_create(
            application=application,
            defaults={
                'extracted_text': result.get('text', ''),
                'page_count': result.get('page_count', 0),
                'status': result.get('status', cls.STATUS_ERROR),
                'error_message': result.get('error_message', ''),
            }
        )

        # Trigger NLP matching analysis immediately
        try:
            ResumeScreening.screen_application(application)
        except Exception:
            pass

        return extraction


class ResumeScreening(models.Model):
    """
    Stores AI-assisted NLP screening results between a candidate's CV and the job opening.
    Uses TF-IDF Vectorization, Cosine Similarity, and Explainable Required-Skill Matching.

    ACADEMIC DEFENSE PRINCIPLE:
    - This model stores quantitative decision support metrics.
    - It strictly assists human recruiters and NEVER automates hiring or rejection.
    - Admins maintain full discretionary control over the applicant review lifecycle.
    """
    STATUS_SUCCESS = 'SUCCESS'
    STATUS_ERROR = 'ERROR'
    STATUS_INSUFFICIENT_TEXT = 'INSUFFICIENT_TEXT'
    STATUS_PENDING = 'PENDING'

    STATUS_CHOICES = [
        (STATUS_SUCCESS, 'Success'),
        (STATUS_ERROR, 'Error'),
        (STATUS_INSUFFICIENT_TEXT, 'Insufficient Text'),
        (STATUS_PENDING, 'Pending'),
    ]

    application = models.OneToOneField(
        Application,
        on_delete=models.CASCADE,
        related_name='resume_screening'
    )
    similarity_score = models.FloatField(
        default=0.0,
        help_text="Cosine similarity score in range [0.0, 1.0]"
    )
    match_percentage = models.FloatField(
        default=0.0,
        help_text="Cosine similarity converted to percentage (0.0% to 100.0%)"
    )
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default=STATUS_PENDING)
    error_message = models.TextField(blank=True, default='')

    # Explainable AI JSON payloads: keywords and non-zero TF-IDF vector weights
    matched_keywords_json = models.TextField(blank=True, default='[]')
    job_vector_json = models.TextField(blank=True, default='{}')
    resume_vector_json = models.TextField(blank=True, default='{}')

    # Required skill matching fields
    matched_skills_json = models.TextField(blank=True, default='[]')
    missing_skills_json = models.TextField(blank=True, default='[]')

    # Conservative Qualification and Experience verification
    qualification_match = models.CharField(max_length=50, default='Needs Verification')
    qualification_detail = models.TextField(blank=True, default='')
    experience_match = models.CharField(max_length=50, default='Needs Verification')
    experience_detail = models.TextField(blank=True, default='')

    # Supervised ML Relevance Classifier Fields (Decision-Support)
    ml_predicted_class = models.CharField(max_length=30, blank=True, default='', help_text="Predicted relevance class ('Relevant' or 'Not Relevant')")
    ml_relevance_probability = models.FloatField(null=True, blank=True, help_text="Estimated relevance probability in range [0.0, 1.0]")
    ml_confidence_tier = models.CharField(max_length=20, blank=True, default='', help_text="Inference confidence level ('High', 'Moderate', 'Low')")
    ml_model_version = models.CharField(max_length=50, blank=True, default='', help_text="Model version used for inference")
    ml_prediction_status = models.CharField(max_length=30, default='PENDING', help_text="ML Inference status ('SUCCESS', 'NO_MODEL', 'INSUFFICIENT_TEXT', 'ERROR', 'PENDING')")

    screened_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-match_percentage', '-screened_at']
        verbose_name = 'Resume Screening Result'
        verbose_name_plural = 'Resume Screening Results'

    def __str__(self):
        return f"AI Match for {self.application.applicant.username} - {self.match_percentage}% ({self.status})"

    @property
    def ml_badge_class(self):
        if self.ml_predicted_class == 'Relevant':
            return 'gk-badge-success'
        elif self.ml_predicted_class == 'Not Relevant':
            return 'gk-badge-danger'
        return 'gk-badge-warning'

    @property
    def ml_relevance_percentage(self):
        if self.ml_relevance_probability is not None:
            return round(self.ml_relevance_probability * 100.0, 1)
        return None

    @property
    def matched_keywords(self):
        try:
            return json.loads(self.matched_keywords_json)
        except Exception:
            return []

    @property
    def job_vector(self):
        try:
            return json.loads(self.job_vector_json)
        except Exception:
            return {}

    @property
    def resume_vector(self):
        try:
            return json.loads(self.resume_vector_json)
        except Exception:
            return {}

    @property
    def matched_skills(self):
        try:
            return json.loads(self.matched_skills_json)
        except Exception:
            return []

    @property
    def missing_skills(self):
        try:
            return json.loads(self.missing_skills_json)
        except Exception:
            return []

    @property
    def badge_class(self):
        """
        Returns dynamic Bootstrap/GURUKUL CSS badge class based on match tier.
        For quick visual interpretation by administrators.
        """
        if self.status != self.STATUS_SUCCESS:
            return 'gk-badge-warning'
        if self.match_percentage >= 65.0:
            return 'gk-badge-success'
        elif self.match_percentage >= 35.0:
            return 'gk-badge-primary'
        else:
            return 'gk-badge-danger'

    @property
    def qualification_badge_class(self):
        if self.qualification_match == 'Matched':
            return 'gk-badge-success'
        elif self.qualification_match == 'Not Matched':
            return 'gk-badge-danger'
        return 'gk-badge-warning'

    @property
    def experience_badge_class(self):
        if self.experience_match == 'Matched':
            return 'gk-badge-success'
        elif self.experience_match == 'Not Matched':
            return 'gk-badge-danger'
        return 'gk-badge-warning'

    @classmethod
    def screen_application(cls, application, force=False):
        """
        Executes NLP resume screening for an application against its target job.
        Extracts CV text if not already extracted, then calculates TF-IDF cosine similarity,
        required-skill matching, qualification matching, and experience matching.
        """
        extraction = getattr(application, 'resume_extraction', None)

        job = application.job
        job_description = job.description if job else ""
        required_skills = job.required_skills if job else ""
        job_qualification = job.qualification if job else ""
        job_experience = job.experience if job else ""
        resume_text = extraction.extracted_text if extraction else ""

        # Check extraction statuses first
        if extraction and extraction.status == ResumeExtraction.STATUS_EMPTY:
            result = {
                'status': cls.STATUS_ERROR,
                'match_percentage': 0.0,
                'similarity_score': 0.0,
                'error_message': 'Uploaded CV has no readable text (scanned image or empty document).',
                'matched_keywords': [],
                'job_vector': {},
                'resume_vector': {},
                'matched_skills': [],
                'missing_skills': [s.strip() for s in required_skills.split(',') if s.strip()],
                'qualification_match': 'Needs Verification',
                'qualification_detail': 'Uploaded CV has no readable text.',
                'experience_match': 'Needs Verification',
                'experience_detail': 'Uploaded CV has no readable text.',
            }
        elif extraction and extraction.status == ResumeExtraction.STATUS_ERROR:
            result = {
                'status': cls.STATUS_ERROR,
                'match_percentage': 0.0,
                'similarity_score': 0.0,
                'error_message': f'Resume text extraction failed: {extraction.error_message}',
                'matched_keywords': [],
                'job_vector': {},
                'resume_vector': {},
                'matched_skills': [],
                'missing_skills': [s.strip() for s in required_skills.split(',') if s.strip()],
                'qualification_match': 'Needs Verification',
                'qualification_detail': 'Resume extraction failed.',
                'experience_match': 'Needs Verification',
                'experience_detail': 'Resume extraction failed.',
            }
        else:
            result = calculate_resume_match(
                job_description=job_description,
                required_skills=required_skills,
                resume_text=resume_text,
                job_qualification=job_qualification,
                job_experience=job_experience
            )

        # Supervised ML Relevance Inference
        from .ml_service import ResumeMLService
        try:
            ml_result = ResumeMLService.evaluate_relevance(
                resume_text=resume_text,
                job_description=job_description,
                required_skills=required_skills
            )
        except Exception:
            ml_result = {
                'status': 'ERROR',
                'predicted_class': 'Unavailable',
                'relevance_probability': None,
                'confidence_tier': 'Unavailable',
                'model_version': '',
            }

        screening, _ = cls.objects.update_or_create(
            application=application,
            defaults={
                'similarity_score': result.get('similarity_score', 0.0),
                'match_percentage': result.get('match_percentage', 0.0),
                'status': result.get('status', cls.STATUS_ERROR),
                'error_message': result.get('error_message') or '',
                'matched_keywords_json': json.dumps(result.get('matched_keywords', [])),
                'job_vector_json': json.dumps(result.get('job_vector', {})),
                'resume_vector_json': json.dumps(result.get('resume_vector', {})),
                'matched_skills_json': json.dumps(result.get('matched_skills', [])),
                'missing_skills_json': json.dumps(result.get('missing_skills', [])),
                'qualification_match': result.get('qualification_match', 'Needs Verification'),
                'qualification_detail': result.get('qualification_detail', ''),
                'experience_match': result.get('experience_match', 'Needs Verification'),
                'experience_detail': result.get('experience_detail', ''),
                'ml_predicted_class': ml_result.get('predicted_class', ''),
                'ml_relevance_probability': ml_result.get('relevance_probability'),
                'ml_confidence_tier': ml_result.get('confidence_tier', ''),
                'ml_model_version': ml_result.get('model_version', ''),
                'ml_prediction_status': ml_result.get('status', 'ERROR'),
            }
        )
        return screening


class ResumeAnalysis(models.Model):
    """
    Complete Resume Analysis record containing:
    - application: OneToOne reference to candidate application
    - match_percentage: Overall quantitative TF-IDF cosine similarity fit
    - matched_skills: List of required skills detected in CV
    - missing_skills: List of required skills missing from CV
    - qualification_match: 'Matched', 'Not Matched', or 'Needs Verification'
    - experience_match: 'Matched', 'Not Matched', or 'Needs Verification'
    - explanation: Factual rule-based explanation generated from actual analysis
    - analyzed_at: Timestamp of execution

    Academic Defense Principle:
    Strictly decision support for the administrator. The final hiring decision
    must remain with the administrator.
    """
    application = models.OneToOneField(
        Application,
        on_delete=models.CASCADE,
        related_name='resume_analysis'
    )
    match_percentage = models.FloatField(default=0.0)
    matched_skills = models.JSONField(default=list)
    missing_skills = models.JSONField(default=list)
    qualification_match = models.CharField(max_length=50, default='Needs Verification')
    experience_match = models.CharField(max_length=50, default='Needs Verification')
    explanation = models.TextField(blank=True, default='')

    STATUS_COMPLETED = 'COMPLETED'
    STATUS_FAILED = 'FAILED'
    STATUS_PENDING = 'PENDING'
    STATUS_PROCESSING = 'PROCESSING'

    ANALYSIS_STATUS_CHOICES = [
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_FAILED, 'Failed'),
        (STATUS_PENDING, 'Pending'),
        (STATUS_PROCESSING, 'Processing'),
    ]

    analysis_status = models.CharField(
        max_length=20,
        choices=ANALYSIS_STATUS_CHOICES,
        default=STATUS_COMPLETED,
        help_text="Status of batch or single analysis execution"
    )
    error_message = models.TextField(blank=True, default='', help_text="Reason for failure if analysis_status is FAILED")

    # Supervised ML Relevance Classifier Fields (Decision-Support)
    ml_predicted_class = models.CharField(max_length=30, blank=True, default='', help_text="Predicted relevance class ('Relevant' or 'Not Relevant')")
    ml_relevance_probability = models.FloatField(null=True, blank=True, help_text="Estimated relevance probability in range [0.0, 1.0]")
    ml_confidence_tier = models.CharField(max_length=20, blank=True, default='', help_text="Inference confidence level ('High', 'Moderate', 'Low')")
    ml_model_version = models.CharField(max_length=50, blank=True, default='', help_text="Model version used for inference")
    ml_prediction_status = models.CharField(max_length=30, default='PENDING', help_text="ML Inference status ('SUCCESS', 'NO_MODEL', 'INSUFFICIENT_TEXT', 'ERROR', 'PENDING')")

    analyzed_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-match_percentage', '-analyzed_at']
        verbose_name = 'Resume Analysis'
        verbose_name_plural = 'Resume Analyses'

    def __str__(self):
        return f"Analysis for {self.application.applicant.username} - {self.match_percentage}%"

    @property
    def ml_badge_class(self):
        if self.ml_predicted_class == 'Relevant':
            return 'gk-badge-success'
        elif self.ml_predicted_class == 'Not Relevant':
            return 'gk-badge-danger'
        return 'gk-badge-warning'

    @property
    def ml_relevance_percentage(self):
        if self.ml_relevance_probability is not None:
            return round(self.ml_relevance_probability * 100.0, 1)
        return None

    @property
    def badge_class(self):
        if self.match_percentage >= 65.0:
            return 'gk-badge-success'
        elif self.match_percentage >= 35.0:
            return 'gk-badge-primary'
        else:
            return 'gk-badge-danger'

    @property
    def qualification_badge_class(self):
        if self.qualification_match == 'Matched':
            return 'gk-badge-success'
        elif self.qualification_match == 'Not Matched':
            return 'gk-badge-danger'
        return 'gk-badge-warning'

    @property
    def is_failed(self):
        return self.analysis_status == self.STATUS_FAILED

    @property
    def is_completed(self):
        return self.analysis_status == self.STATUS_COMPLETED

    @property
    def analysis_status_badge_class(self):
        mapping = {
            self.STATUS_COMPLETED: 'gk-badge-success',
            self.STATUS_FAILED: 'gk-badge-danger',
            self.STATUS_PROCESSING: 'gk-badge-warning',
            self.STATUS_PENDING: 'gk-badge-neutral',
        }
        return mapping.get(self.analysis_status, 'gk-badge-neutral')

    @property
    def experience_badge_class(self):
        if self.experience_match == 'Matched':
            return 'gk-badge-success'
        elif self.experience_match == 'Not Matched':
            return 'gk-badge-danger'
        return 'gk-badge-warning'

    @classmethod
    def perform_analysis(cls, application):
        """
        Executes complete pipeline:
        PDF extraction -> text preprocessing -> TF-IDF -> Cosine Similarity -> skill matching -> result storage
        """
        from .service import generate_explanation

        # 1. PDF extraction
        if application.cv:
            extraction = ResumeExtraction.process_application_cv(application)
        else:
            extraction = getattr(application, 'resume_extraction', None)

        job = application.job
        job_description = job.description if job else ""
        required_skills = job.required_skills if job else ""
        job_qualification = job.qualification if job else ""
        job_experience = job.experience if job else ""
        resume_text = extraction.extracted_text if extraction else ""

        # 2-6. Preprocessing, TF-IDF, Cosine Similarity, Skill matching, Qual/Exp evaluation
        result = calculate_resume_match(
            job_description=job_description,
            required_skills=required_skills,
            resume_text=resume_text,
            job_qualification=job_qualification,
            job_experience=job_experience
        )

        matched_skills = result.get('matched_skills', [])
        missing_skills = result.get('missing_skills', [])
        qualification_match = result.get('qualification_match', 'Needs Verification')
        qualification_detail = result.get('qualification_detail', '')
        experience_match = result.get('experience_match', 'Needs Verification')
        experience_detail = result.get('experience_detail', '')
        match_percentage = result.get('match_percentage', 0.0)

        # Check extraction and analysis status
        analysis_status = cls.STATUS_COMPLETED
        analysis_error = ""

        if extraction and extraction.status == ResumeExtraction.STATUS_EMPTY:
            analysis_status = cls.STATUS_FAILED
            analysis_error = "Uploaded CV has no readable text (scanned image or empty document)."
        elif extraction and extraction.status == ResumeExtraction.STATUS_ERROR:
            analysis_status = cls.STATUS_FAILED
            analysis_error = f"Resume text extraction failed: {extraction.error_message}"
        elif not application.cv and not (extraction and extraction.extracted_text):
            analysis_status = cls.STATUS_FAILED
            analysis_error = "No CV file attached to this application."
        elif result.get('status') == 'ERROR':
            analysis_status = cls.STATUS_FAILED
            analysis_error = result.get('error_message') or "NLP analysis error occurred."

        # Supervised ML Relevance Inference
        from .ml_service import ResumeMLService
        try:
            ml_result = ResumeMLService.evaluate_relevance(
                resume_text=resume_text,
                job_description=job_description,
                required_skills=required_skills
            )
        except Exception:
            ml_result = {
                'status': 'ERROR',
                'predicted_class': 'Unavailable',
                'relevance_probability': None,
                'confidence_tier': 'Unavailable',
                'model_version': '',
            }

        # 7. Generate rule-based explanation
        if analysis_status == cls.STATUS_FAILED:
            explanation = f"Analysis Failed: {analysis_error} Please review the candidate's CV document manually."
        else:
            explanation = generate_explanation(
                matched_skills=matched_skills,
                missing_skills=missing_skills,
                qualification_match=qualification_match,
                experience_match=experience_match,
                match_percentage=match_percentage,
                qualification_detail=qualification_detail,
                experience_detail=experience_detail
            )

        # 8. Result storage
        analysis, _ = cls.objects.update_or_create(
            application=application,
            defaults={
                'match_percentage': match_percentage,
                'matched_skills': matched_skills,
                'missing_skills': missing_skills,
                'qualification_match': qualification_match,
                'experience_match': experience_match,
                'explanation': explanation,
                'analysis_status': analysis_status,
                'error_message': analysis_error,
                'ml_predicted_class': ml_result.get('predicted_class', ''),
                'ml_relevance_probability': ml_result.get('relevance_probability'),
                'ml_confidence_tier': ml_result.get('confidence_tier', ''),
                'ml_model_version': ml_result.get('model_version', ''),
                'ml_prediction_status': ml_result.get('status', 'ERROR'),
            }
        )
        return analysis

