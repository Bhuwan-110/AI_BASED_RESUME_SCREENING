from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.decorators import admin_required
from applications.models import Application
from .models import ResumeExtraction, ResumeScreening, ResumeAnalysis


@login_required
@admin_required
def analyze_resume(request, application_id):
    """
    Complete Resume Analysis View triggered when an admin clicks "Analyze CV".
    Executes the full pipeline:
    PDF extraction -> text preprocessing -> TF-IDF -> Cosine Similarity -> skill matching -> result storage
    
    Renders an attractive administrative dashboard presenting:
    - Candidate Information
    - Job Information
    - Match Percentage (with visual meter)
    - Matched Skills & Missing Skills
    - Qualification & Experience Verification
    - Rule-based explanation
    - Actions: [View CV], [Analyze Again], [Shortlist], [Update Status]
    """
    application = get_object_or_404(
        Application.objects.select_related('job', 'applicant', 'applicant__profile'),
        pk=application_id
    )

    # Handle quick administrative actions
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'shortlist':
            application.status = Application.STATUS_SHORTLISTED
            application.save()
            messages.success(
                request,
                f"Applicant '{application.applicant.get_full_name() or application.applicant.username}' has been successfully Shortlisted!"
            )
            return redirect('resume_ai:analyze_resume', application_id=application.id)
        elif action == 'update_status':
            new_status = request.POST.get('status')
            if new_status in dict(Application.STATUS_CHOICES):
                application.status = new_status
                application.save()
                messages.success(
                    request,
                    f"Candidate review status updated to '{new_status}'."
                )
            else:
                messages.error(request, "Invalid status choice selected.")
            return redirect('resume_ai:analyze_resume', application_id=application.id)

    # Perform or retrieve analysis
    if 're_analyze' in request.GET or not hasattr(application, 'resume_analysis'):
        analysis = ResumeAnalysis.perform_analysis(application)
        messages.success(
            request,
            f"Resume analysis generated ({analysis.match_percentage}% match score)."
        )
    else:
        analysis = application.resume_analysis

    context = {
        'application': application,
        'job': application.job,
        'analysis': analysis,
        'matched_skills': analysis.matched_skills,
        'missing_skills': analysis.missing_skills,
        'status_choices': Application.STATUS_CHOICES,
    }
    return render(request, 'resume_ai/analysis.html', context)


@login_required
@admin_required
def view_extracted_text(request, application_id):
    """
    Administrator AI Diagnostic and Screening Inspection View.
    Strictly restricted to administrators — raw extracted text and vectors are never exposed to the public.
    """
    application = get_object_or_404(
        Application.objects.select_related('job', 'applicant', 'applicant__profile'),
        pk=application_id
    )

    # 1. Handle re-extraction on demand (?re_extract=true)
    if 're_extract' in request.GET or not hasattr(application, 'resume_extraction'):
        extraction = ResumeExtraction.process_application_cv(application)
        if extraction.status == ResumeExtraction.STATUS_SUCCESS:
            messages.success(request, f"Resume text extracted successfully ({extraction.page_count} page(s), {extraction.word_count} words).")
        elif extraction.status == ResumeExtraction.STATUS_EMPTY:
            messages.warning(request, f"Extraction Notice: {extraction.error_message}")
        else:
            messages.error(request, f"Extraction Alert: {extraction.error_message}")
    else:
        extraction = application.resume_extraction

    # 2. Handle AI re-screening on demand (?re_screen=true) or initial run
    if 're_screen' in request.GET or 're_extract' in request.GET or not hasattr(application, 'resume_screening'):
        screening = ResumeScreening.screen_application(application, force=True)
        if screening.status == ResumeScreening.STATUS_SUCCESS:
            messages.success(request, f"AI NLP Screening updated: {screening.match_percentage}% Match Score computed.")
        elif screening.status == ResumeScreening.STATUS_INSUFFICIENT_TEXT:
            messages.warning(request, f"NLP Screening Notice: {screening.error_message}")
        else:
            messages.error(request, f"NLP Screening Alert: {screening.error_message}")
    else:
        screening = application.resume_screening

    context = {
        'application': application,
        'job': application.job,
        'extraction': extraction,
        'screening': screening,
        'matched_keywords': screening.matched_keywords,
        'matched_skills': screening.matched_skills,
        'missing_skills': screening.missing_skills,
        'job_vector': screening.job_vector,
        'resume_vector': screening.resume_vector,
    }
    return render(request, 'resume_ai/extracted_text_test.html', context)


@login_required
@admin_required
def batch_analyze_job(request, job_id):
    """
    Executes one-click batch resume screening for all applicants of a specific job.
    Supports mode='all' (full re-analysis) or mode='pending' (unscreened candidates only).
    """
    from django.urls import reverse
    from .batch_service import BatchResumeScreeningService
    from jobs.models import Job

    job = get_object_or_404(Job, pk=job_id)

    if request.method == 'POST':
        mode = request.POST.get('mode', 'all')
        summary = BatchResumeScreeningService.batch_process_job_applications(job_id=job.id, mode=mode)

        # Store summary in session for display on the applicants page
        request.session['batch_analysis_summary'] = summary

        if summary.get('success'):
            messages.success(
                request,
                f"Batch analysis completed for '{job.title}': {summary['success_count']} analyzed successfully, "
                f"{summary['failed_count']} failed. (Avg Match: {summary['average_match']}%)"
            )
        else:
            messages.error(request, f"Batch analysis error: {summary.get('error', 'Unknown error')}")

        return redirect(f"{reverse('applications:admin_applicants')}?job={job.id}&batch_completed=1")

    # If GET request, redirect to job applicants
    return redirect(f"{reverse('applications:admin_applicants')}?job={job.id}")


@login_required
@admin_required
def api_batch_analyze_item(request, application_id):
    """
    JSON API endpoint for real-time frontend progress reporting.
    Processes a single candidate application within a batch loop.
    """
    from django.http import JsonResponse
    from .batch_service import BatchResumeScreeningService

    application = get_object_or_404(
        Application.objects.select_related('job', 'applicant', 'applicant__profile'),
        pk=application_id
    )

    val = request.POST.get('force') if request.method == 'POST' else request.GET.get('force')
    if val is None:
        val = 'true'
    force = str(val).lower() in ['true', '1', 'yes']
    result = BatchResumeScreeningService.process_single_application(application=application, force=force)

    return JsonResponse(result)


@login_required
@admin_required
def batch_shortlist_candidates(request, job_id):
    """
    Batch administrative action to shortlist multiple selected candidate applications at once.
    """
    from django.urls import reverse
    from jobs.models import Job

    job = get_object_or_404(Job, pk=job_id)

    if request.method == 'POST':
        selected_ids = request.POST.getlist('selected_applications')
        if not selected_ids:
            messages.warning(request, "No candidates were selected for shortlisting.")
            return redirect(f"{reverse('applications:admin_applicants')}?job={job.id}")

        updated_count = Application.objects.filter(
            job=job,
            id__in=selected_ids
        ).exclude(
            status=Application.STATUS_SHORTLISTED
        ).update(status=Application.STATUS_SHORTLISTED)

        messages.success(
            request,
            f"Successfully shortlisted {updated_count} candidate(s) for '{job.title}'."
        )

    return redirect(f"{reverse('applications:admin_applicants')}?job={job.id}")

