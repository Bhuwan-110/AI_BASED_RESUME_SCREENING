from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from accounts.decorators import admin_required
from .models import Job
from .forms import JobForm

def job_detail(request, pk):
    """
    Public and internal detailed view for a single job opening.
    Displays comprehensive qualifications, skills, and application status.
    Guarantees expired jobs cannot receive applications.
    """
    job = get_object_or_404(Job, pk=pk)
    user_application = None
    if request.user.is_authenticated:
        user_application = job.applications.filter(applicant=request.user).first()

    context = {
        'job': job,
        'is_expired': job.is_expired,
        'is_admin': hasattr(request.user, 'profile') and request.user.profile.is_admin if request.user.is_authenticated else False,
        'user_application': user_application,
        'has_applied': user_application is not None,
    }
    return render(request, 'jobs/job_detail.html', context)


@login_required
@admin_required
def manage_jobs(request):
    """
    Administrator overview listing active and expired jobs with management controls and status filtering.
    """
    today = timezone.now().date()
    status_filter = request.GET.get('status', 'all').lower()

    active_count = Job.objects.filter(deadline__gte=today).count()
    expired_count = Job.objects.filter(deadline__lt=today).count()
    total_count = Job.objects.count()

    if status_filter == 'active':
        jobs_query = Job.objects.filter(deadline__gte=today).order_by('deadline')
    elif status_filter == 'expired':
        jobs_query = Job.objects.filter(deadline__lt=today).order_by('-deadline')
    else:
        status_filter = 'all'
        jobs_query = Job.objects.all().order_by('deadline')

    context = {
        'jobs': jobs_query,
        'total_count': total_count,
        'active_count': active_count,
        'expired_count': expired_count,
        'status_filter': status_filter,
        'active_admin_tab': 'jobs',
    }
    return render(request, 'jobs/manage_jobs.html', context)



@login_required
@admin_required
def create_job(request):
    """
    Administrator view to create a new job position.
    """
    if request.method == 'POST':
        form = JobForm(request.POST)
        if form.is_valid():
            job = form.save()
            messages.success(request, f"Job vacancy '{job.title}' was created successfully.")
            return redirect('jobs:manage_jobs')
        else:
            messages.error(request, 'Please correct the errors in the form.')
    else:
        # Default deadline to 30 days from now
        initial_deadline = timezone.now().date() + timezone.timedelta(days=30)
        form = JobForm(initial={'deadline': initial_deadline})

    return render(request, 'jobs/job_form.html', {'form': form, 'action_title': 'Create New Job Opening'})


@login_required
@admin_required
def edit_job(request, pk):
    """
    Administrator view to update an existing job position.
    """
    job = get_object_or_404(Job, pk=pk)

    if request.method == 'POST':
        form = JobForm(request.POST, instance=job)
        if form.is_valid():
            job = form.save()
            messages.success(request, f"Job vacancy '{job.title}' was updated successfully.")
            return redirect('jobs:manage_jobs')
        else:
            messages.error(request, 'Please correct the errors in the form.')
    else:
        form = JobForm(instance=job)

    context = {
        'form': form,
        'job': job,
        'action_title': f"Edit Job: {job.title}",
    }
    return render(request, 'jobs/job_form.html', context)


@login_required
@admin_required
def delete_job(request, pk):
    """
    Administrator action to delete a job position with safety confirmation.
    """
    job = get_object_or_404(Job, pk=pk)

    if request.method == 'POST':
        title = job.title
        job.delete()
        messages.success(request, f"Job opening '{title}' was permanently deleted.")
        return redirect('jobs:manage_jobs')

    return render(request, 'jobs/job_confirm_delete.html', {'job': job})
