import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import F, Q, Avg, Max, Min
from accounts.decorators import admin_required
from jobs.models import Job
from .models import Application
from .forms import JobApplicationForm, ApplicationStatusUpdateForm

@login_required
def apply_job(request, job_id):
    """
    Candidate application submission view.
    Ensures job is active, prevents duplicate submissions, and validates PDF CV.
    """
    job = get_object_or_404(Job, pk=job_id)

    # 1. Prevent applications to expired jobs
    if job.is_expired:
        messages.error(
            request,
            f"Applications for '{job.title}' are closed because the deadline ({job.deadline.strftime('%b %d, %Y')}) has passed."
        )
        return redirect('jobs:job_detail', pk=job.pk)

    # 2. Prevent duplicate applications
    existing_application = Application.objects.filter(job=job, applicant=request.user).first()
    if existing_application:
        messages.warning(
            request,
            f"You have already applied for '{job.title}' on {existing_application.applied_at.strftime('%b %d, %Y')}. You can review your submission in My Applications."
        )
        return redirect('applications:my_applications')

    if request.method == 'POST':
        form = JobApplicationForm(request.POST, request.FILES)
        if form.is_valid():
            application = form.save(commit=False)
            application.job = job
            application.applicant = request.user
            application.status = Application.STATUS_APPLIED
            application.save()

            # Automatically extract text from PDF for the AI module
            try:
                from resume_ai.models import ResumeExtraction
                ResumeExtraction.process_application_cv(application)
            except Exception as extraction_err:
                # Extraction error handled gracefully without breaking application submission
                pass

            messages.success(
                request,
                f"Your application for '{job.title}' has been submitted successfully! You can track its evaluation status here."
            )
            return redirect('applications:my_applications')
        else:
            messages.error(request, "Please review and correct the errors below before submitting your resume.")
    else:
        form = JobApplicationForm()

    context = {
        'job': job,
        'form': form,
    }
    return render(request, 'applications/apply_job.html', context)


@login_required
def my_applications(request):
    """
    Candidate's personal applications page.
    Shows all jobs applied for, submission dates, evaluation status, and CV file links.
    Strictly safeguards privacy: no AI scores or internal evaluation data is exposed.
    """
    status_filter = request.GET.get('status', '').strip()
    user_apps = Application.objects.filter(applicant=request.user).select_related('job').order_by('-applied_at')

    total_count = user_apps.count()
    applied_count = user_apps.filter(status=Application.STATUS_APPLIED).count()
    under_review_count = user_apps.filter(status=Application.STATUS_UNDER_REVIEW).count()
    shortlisted_count = user_apps.filter(status=Application.STATUS_SHORTLISTED).count()
    rejected_count = user_apps.filter(status=Application.STATUS_REJECTED).count()

    if status_filter and status_filter in dict(Application.STATUS_CHOICES):
        filtered_apps = user_apps.filter(status=status_filter)
    else:
        status_filter = ''
        filtered_apps = user_apps

    context = {
        'applications': filtered_apps,
        'status_filter': status_filter,
        'total_count': total_count,
        'applied_count': applied_count,
        'under_review_count': under_review_count,
        'shortlisted_count': shortlisted_count,
        'rejected_count': rejected_count,
        'active_seeker_tab': 'applications',
    }
    return render(request, 'applications/my_applications.html', context)



@login_required
def view_application(request, pk):
    """
    Detailed view of an individual job application.
    Accessible only to the applicant who submitted it or an administrator.
    """
    application = get_object_or_404(
        Application.objects.select_related('job', 'applicant', 'applicant__profile', 'resume_screening'),
        pk=pk
    )

    # Security check: must be applicant or admin
    is_admin = hasattr(request.user, 'profile') and request.user.profile.is_admin
    if application.applicant != request.user and not is_admin:
        messages.error(request, "Access denied. You do not have permission to view that application.")
        return redirect('applications:my_applications')

    # Ensure AI screening is calculated if admin is inspecting
    if is_admin and not hasattr(application, 'resume_screening'):
        try:
            from resume_ai.models import ResumeScreening
            ResumeScreening.screen_application(application)
            application.refresh_from_db()
        except Exception:
            pass

    status_form = ApplicationStatusUpdateForm(instance=application) if is_admin else None

    context = {
        'application': application,
        'job': application.job,
        'is_admin': is_admin,
        'status_form': status_form,
    }
    return render(request, 'applications/application_detail.html', context)


@login_required
@admin_required
def admin_applicants(request):
    """
    Centralized administrative applicants management portal.
    Allows admin to select a specific job vacancy or view candidates across all openings.
    Supports filtering by application status, quick shortlisting, and viewing AI screening results.
    """
    job_id = request.GET.get('job', '').strip()
    status_filter = request.GET.get('status', '').strip()

    ai_status = request.GET.get('ai_status', '').strip()
    min_match = request.GET.get('min_match', '').strip()

    all_jobs = Job.objects.all().order_by('title')
    applicants_query = Application.objects.select_related(
        'job', 'applicant', 'applicant__profile',
        'resume_analysis', 'resume_screening', 'resume_extraction'
    ).order_by('-applied_at')

    selected_job = None
    if job_id:
        try:
            selected_job = Job.objects.get(pk=job_id)
            applicants_query = applicants_query.filter(job=selected_job)
        except (Job.DoesNotExist, ValueError):
            job_id = ''

    # Base query for counts before status and AI filtering
    base_count_query = applicants_query

    # Status filter (Applied, Under Review, Shortlisted, Rejected)
    if status_filter and status_filter in dict(Application.STATUS_CHOICES):
        applicants_query = applicants_query.filter(status=status_filter)

    # Compute status breakdown for the active job selection
    applied_count = base_count_query.filter(status=Application.STATUS_APPLIED).count()
    under_review_count = base_count_query.filter(status=Application.STATUS_UNDER_REVIEW).count()
    shortlisted_count = base_count_query.filter(status=Application.STATUS_SHORTLISTED).count()
    rejected_count = base_count_query.filter(status=Application.STATUS_REJECTED).count()
    total_count = base_count_query.count()

    # Batch AI metrics
    analyzed_count = 0
    failed_count = 0
    pending_count = 0
    highest_match = None
    lowest_match = None
    average_match = None
    all_app_ids = []
    pending_app_ids = []

    if selected_job:
        # Default ranking: Order candidates by AI match percentage descending (nulls last)
        applicants_query = applicants_query.order_by(
            F('resume_analysis__match_percentage').desc(nulls_last=True),
            '-applied_at'
        )

        completed_apps = base_count_query.filter(resume_analysis__analysis_status='COMPLETED')
        analyzed_count = completed_apps.count()
        failed_count = base_count_query.filter(resume_analysis__analysis_status='FAILED').count()
        pending_count = max(0, total_count - analyzed_count - failed_count)

        if analyzed_count > 0:
            stats = completed_apps.aggregate(
                max_score=Max('resume_analysis__match_percentage'),
                min_score=Min('resume_analysis__match_percentage'),
                avg_score=Avg('resume_analysis__match_percentage')
            )
            highest_match = round(stats['max_score'] or 0.0, 1)
            lowest_match = round(stats['min_score'] or 0.0, 1)
            average_match = round(stats['avg_score'] or 0.0, 1)

        all_app_ids = list(base_count_query.values_list('id', flat=True))
        pending_app_ids = list(
            base_count_query.filter(
                Q(resume_analysis__isnull=True) | ~Q(resume_analysis__analysis_status='COMPLETED')
            ).values_list('id', flat=True)
        )

        # Apply AI status filter if requested
        if ai_status == 'analyzed':
            applicants_query = applicants_query.filter(resume_analysis__analysis_status='COMPLETED')
        elif ai_status == 'failed':
            applicants_query = applicants_query.filter(resume_analysis__analysis_status='FAILED')
        elif ai_status == 'pending':
            applicants_query = applicants_query.filter(
                Q(resume_analysis__isnull=True) | ~Q(resume_analysis__analysis_status='COMPLETED')
            )

        # Apply min_match filter if requested (e.g. 80, 70, 60)
        if min_match:
            try:
                threshold_val = float(min_match)
                applicants_query = applicants_query.filter(
                    resume_analysis__analysis_status='COMPLETED',
                    resume_analysis__match_percentage__gte=threshold_val
                )
            except ValueError:
                min_match = ''

    # Retrieve flash session batch summary if present
    batch_summary = request.session.pop('batch_analysis_summary', None)

    context = {
        'jobs': all_jobs,
        'selected_job': selected_job,
        'selected_job_id': job_id,
        'status_filter': status_filter,
        'ai_status': ai_status,
        'min_match': min_match,
        'applicants': applicants_query,
        'total_count': total_count,
        'filtered_count': applicants_query.count(),
        'applied_count': applied_count,
        'under_review_count': under_review_count,
        'shortlisted_count': shortlisted_count,
        'rejected_count': rejected_count,
        'analyzed_count': analyzed_count,
        'failed_count': failed_count,
        'pending_count': pending_count,
        'highest_match': highest_match,
        'lowest_match': lowest_match,
        'average_match': average_match,
        'batch_summary': batch_summary,
        'all_app_ids_json': json.dumps(all_app_ids),
        'pending_app_ids_json': json.dumps(pending_app_ids),
        'status_choices': Application.STATUS_CHOICES,
        'active_admin_tab': 'applicants',
    }
    return render(request, 'applications/admin_applicants.html', context)


@login_required
@admin_required
def job_applicants(request, job_id):
    """
    Backward-compatible route redirecting directly to the centralized admin applicants page
    with the selected job opening pre-filtered.
    """
    from django.urls import reverse
    return redirect(f"{reverse('applications:admin_applicants')}?job={job_id}")


@login_required
@admin_required
def quick_shortlist(request, pk):
    """
    Fast one-click action for administrators to mark a candidate as Shortlisted.
    """
    application = get_object_or_404(Application, pk=pk)
    if request.method == 'POST':
        application.status = Application.STATUS_SHORTLISTED
        application.save()
        display_name = application.applicant.get_full_name() or application.applicant.username
        messages.success(
            request,
            f"Candidate '{display_name}' has been Shortlisted for '{application.job.title}'."
        )

    # Safely redirect back to referring page or applicants list
    redirect_url = request.POST.get('next') or request.META.get('HTTP_REFERER')
    if redirect_url and redirect_url.startswith('/'):
        return redirect(redirect_url)
    return redirect(f"{redirect('applications:admin_applicants').url}?job={application.job.pk}")


@login_required
@admin_required
def update_status(request, pk):
    """
    Administrator action to update candidate review status with audit messaging.
    """
    application = get_object_or_404(Application, pk=pk)
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(Application.STATUS_CHOICES):
            old_status = application.status
            application.status = new_status
            application.save()
            display_name = application.applicant.get_full_name() or application.applicant.username
            messages.success(
                request,
                f"Candidate '{display_name}' status updated from '{old_status}' to '{new_status}'."
            )
        else:
            messages.error(request, "Invalid status choice selected.")

    # Redirect back safely preserving context
    redirect_url = request.POST.get('next') or request.META.get('HTTP_REFERER')
    if redirect_url and redirect_url.startswith('/'):
        return redirect(redirect_url)
    return redirect('applications:admin_applicants')

