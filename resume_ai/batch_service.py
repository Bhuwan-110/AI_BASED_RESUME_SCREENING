"""
GURUKUL AI Batch Resume Screening Service
=========================================
Academic Project Service:
Provides robust, safe, sequential batch resume screening for job vacancies.
Reuses existing PDF extraction, TF-IDF vectorization, Cosine Similarity,
Supervised ML relevance inference, and ResumeAnalysis models.

KEY ARCHITECTURAL GUARANTEES:
1. One-Click Batch Analysis: Administrators can process all submitted candidate CVs
   for a target vacancy with a single action.
2. Single-Job Criteria Caching: Job title, duties, required skills, qualification,
   and experience requirements are loaded once from the database and reused consistently
   across all applicant evaluations.
3. Fault Isolation: One corrupted, password-protected, or unreadable PDF document
   will NEVER crash the batch pipeline. Failed applications are flagged with explicit
   error diagnostics (e.g., 'No readable text', 'Empty document', 'Extraction error')
   while processing continues for all remaining candidates.
4. Non-Destructive Update-or-Create: Existing records are safely updated without
   creating orphaned or duplicate records.
5. Decision-Support Only: The batch engine computes ranking and match percentages.
   It NEVER automatically hires or rejects candidates.
"""

import logging
from typing import Dict, Any, List, Optional
from django.db import transaction
from jobs.models import Job
from applications.models import Application
from .models import ResumeExtraction, ResumeScreening, ResumeAnalysis

logger = logging.getLogger(__name__)


class BatchResumeScreeningService:
    """
    High-performance, fault-tolerant batch screening service.
    """

    @classmethod
    def process_single_application(
        cls,
        application: Application,
        job: Optional[Job] = None,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Processes AI screening for an individual candidate application.

        Parameters:
        - application: Application instance to evaluate.
        - job: Optional pre-loaded Job instance (avoids redundant DB queries).
        - force: If True, re-analyzes even if already completed.

        Returns:
        Structured result dictionary with success flag, match score, and status.
        """
        if job is None:
            job = application.job

        candidate_name = application.applicant.get_full_name() or application.applicant.username

        # Check if already completed and force is False
        existing_analysis = getattr(application, 'resume_analysis', None)
        if not force and existing_analysis and existing_analysis.is_completed:
            return {
                'success': True,
                'application_id': application.id,
                'candidate_name': candidate_name,
                'status': existing_analysis.analysis_status,
                'match_percentage': existing_analysis.match_percentage,
                'matched_skills': existing_analysis.matched_skills,
                'missing_skills': existing_analysis.missing_skills,
                'error_message': '',
                'skipped': True,
            }

        try:
            # Execute full pipeline (PDF extraction -> TF-IDF -> Cosine Sim -> ML Model -> Result Storage)
            analysis = ResumeAnalysis.perform_analysis(application)

            is_success = (analysis.analysis_status == ResumeAnalysis.STATUS_COMPLETED)
            return {
                'success': is_success,
                'application_id': application.id,
                'candidate_name': candidate_name,
                'status': analysis.analysis_status,
                'match_percentage': analysis.match_percentage,
                'matched_skills': analysis.matched_skills,
                'missing_skills': analysis.missing_skills,
                'error_message': analysis.error_message if not is_success else '',
                'skipped': False,
            }

        except Exception as ex:
            logger.error(f"Error during batch screening of application #{application.id}: {ex}", exc_info=True)
            error_str = str(ex)

            # Record failure state safely in database
            try:
                analysis, _ = ResumeAnalysis.objects.update_or_create(
                    application=application,
                    defaults={
                        'match_percentage': 0.0,
                        'matched_skills': [],
                        'missing_skills': job.skills_list if job else [],
                        'qualification_match': 'Needs Verification',
                        'experience_match': 'Needs Verification',
                        'explanation': f"Analysis Failed: {error_str}",
                        'analysis_status': ResumeAnalysis.STATUS_FAILED,
                        'error_message': error_str,
                    }
                )
            except Exception:
                pass

            return {
                'success': False,
                'application_id': application.id,
                'candidate_name': candidate_name,
                'status': ResumeAnalysis.STATUS_FAILED,
                'match_percentage': 0.0,
                'matched_skills': [],
                'missing_skills': job.skills_list if job else [],
                'error_message': error_str,
                'skipped': False,
            }

    @classmethod
    def batch_process_job_applications(
        cls,
        job_id: int,
        mode: str = 'all'
    ) -> Dict[str, Any]:
        """
        Executes sequential batch screening across all candidate submissions for a vacancy.

        Parameters:
        - job_id: Primary key of target Job.
        - mode: 'all' (analyzes/re-analyzes all applications) or
                'pending' (analyzes only unanalyzed or failed applications).

        Returns:
        Structured batch execution summary with totals, success/failure counts,
        and statistical summary metrics (highest, lowest, average match).
        """
        try:
            job = Job.objects.get(pk=job_id)
        except Job.DoesNotExist:
            return {
                'success': False,
                'error': f"Job vacancy with ID {job_id} not found."
            }

        applications = Application.objects.filter(job=job).select_related(
            'applicant', 'applicant__profile',
            'resume_analysis', 'resume_screening', 'resume_extraction'
        ).order_by('-applied_at')

        force = (mode == 'all')
        results: List[Dict[str, Any]] = []

        total_count = applications.count()
        success_count = 0
        failed_count = 0
        matches: List[float] = []

        for app in applications:
            # In 'pending' mode, skip already successfully completed applications
            if not force and hasattr(app, 'resume_analysis') and app.resume_analysis.is_completed:
                success_count += 1
                matches.append(app.resume_analysis.match_percentage)
                results.append({
                    'success': True,
                    'application_id': app.id,
                    'candidate_name': app.applicant.get_full_name() or app.applicant.username,
                    'status': app.resume_analysis.analysis_status,
                    'match_percentage': app.resume_analysis.match_percentage,
                    'error_message': '',
                    'skipped': True,
                })
                continue

            res = cls.process_single_application(application=app, job=job, force=force)
            results.append(res)

            if res['success']:
                success_count += 1
                matches.append(res['match_percentage'])
            else:
                failed_count += 1

        highest_match = round(max(matches), 1) if matches else 0.0
        lowest_match = round(min(matches), 1) if matches else 0.0
        average_match = round(sum(matches) / len(matches), 1) if matches else 0.0

        return {
            'success': True,
            'job_id': job.id,
            'job_title': job.title,
            'total_applicants': total_count,
            'processed_count': len(results),
            'success_count': success_count,
            'failed_count': failed_count,
            'highest_match': highest_match,
            'lowest_match': lowest_match,
            'average_match': average_match,
            'results': results,
        }
