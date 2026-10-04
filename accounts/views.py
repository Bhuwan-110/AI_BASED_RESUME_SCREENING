from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .forms import JobSeekerRegistrationForm, LoginForm, ProfileUpdateForm
from .decorators import admin_required, job_seeker_required
from .models import Profile

def register_view(request):
    """
    Public registration endpoint.
    Strictly registers users with the JOB SEEKER role.
    """
    if request.user.is_authenticated:
        if hasattr(request.user, 'profile') and request.user.profile.is_admin:
            return redirect('accounts:admin_dashboard')
        return redirect('accounts:dashboard')

    if request.method == 'POST':
        form = JobSeekerRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Log in the new user immediately
            login(request, user)
            display_name = user.first_name if user.first_name else user.username
            messages.success(request, f'Welcome to GURUKUL, {display_name}! Your Job Seeker account was created successfully.')
            return redirect('accounts:dashboard')
        else:
            messages.error(request, 'Please correct the highlighted errors below.')
    else:
        form = JobSeekerRegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    """
    Authentication endpoint supporting username or email login.
    Routes users automatically based on role:
      - Admin -> Admin Dashboard
      - Job Seeker -> Job Seeker Dashboard
    """
    if request.user.is_authenticated:
        if hasattr(request.user, 'profile') and request.user.profile.is_admin:
            return redirect('accounts:admin_dashboard')
        return redirect('accounts:dashboard')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            identifier = form.cleaned_data['username_or_email'].strip()
            password = form.cleaned_data['password']

            # Check if identifier is email
            username_to_auth = identifier
            if '@' in identifier:
                user_match = User.objects.filter(email__iexact=identifier).first()
                if user_match:
                    username_to_auth = user_match.username

            user = authenticate(request, username=username_to_auth, password=password)

            if user is not None:
                if user.is_active:
                    login(request, user)
                    display_name = user.first_name if user.first_name else user.username
                    messages.success(request, f'Welcome back, {display_name}!')

                    # Check next parameter safely
                    next_url = request.GET.get('next')
                    if next_url and next_url.startswith('/'):
                        return redirect(next_url)

                    # Role-based dashboard routing
                    if hasattr(user, 'profile') and user.profile.is_admin:
                        return redirect('accounts:admin_dashboard')
                    return redirect('accounts:dashboard')
                else:
                    messages.error(request, 'This account is currently disabled. Please contact the administrator.')
            else:
                messages.error(request, 'Invalid username/email or password. Please check your credentials.')
        else:
            messages.error(request, 'Please provide both username/email and password.')
    else:
        form = LoginForm()

    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    """
    Logout view that safely terminates session and confirms feedback.
    """
    if request.user.is_authenticated:
        logout(request)
        messages.success(request, 'You have been logged out successfully.')
    return redirect('accounts:login')


@login_required
@job_seeker_required
def job_seeker_dashboard(request):
    """
    Candidate Dashboard for Job Seekers.
    Displays application metrics (Total Applications, Under Review, Shortlisted, Rejected),
    recent candidate submissions, and direct access to career openings.
    """
    # If an admin navigates to the job seeker dashboard, route them to admin dashboard
    if hasattr(request.user, 'profile') and request.user.profile.is_admin:
        return redirect('accounts:admin_dashboard')

    from applications.models import Application

    user_apps = request.user.applications.select_related('job')
    total_applications = user_apps.count()
    under_review_count = user_apps.filter(status=Application.STATUS_UNDER_REVIEW).count()
    shortlisted_count = user_apps.filter(status=Application.STATUS_SHORTLISTED).count()
    rejected_count = user_apps.filter(status=Application.STATUS_REJECTED).count()
    applied_count = user_apps.filter(status=Application.STATUS_APPLIED).count()

    recent_applications = user_apps.order_by('-applied_at')[:6]

    context = {
        'user': request.user,
        'profile': request.user.profile,
        'total_applications': total_applications,
        'under_review_count': under_review_count,
        'shortlisted_count': shortlisted_count,
        'rejected_count': rejected_count,
        'applied_count': applied_count,
        'recent_applications': recent_applications,
        'active_seeker_tab': 'dashboard',
    }
    return render(request, 'accounts/job_seeker_dashboard.html', context)



@login_required
@admin_required
def admin_dashboard(request):
    """
    Administrative Dashboard for GURUKUL evaluators.
    Provides real-time recruitment metrics, candidate pipeline overview,
    and direct access to jobs and AI screening results.
    """
    from jobs.models import Job
    from applications.models import Application

    today = timezone.now().date()

    # Core Dashboard Statistics (Required by spec)
    total_jobs = Job.objects.count()
    active_jobs = Job.objects.filter(deadline__gte=today).count()
    expired_jobs = Job.objects.filter(deadline__lt=today).count()
    total_applications = Application.objects.count()
    shortlisted_candidates = Application.objects.filter(status=Application.STATUS_SHORTLISTED).count()

    # Additional user context
    total_users = User.objects.count()
    job_seekers_count = Profile.objects.filter(role=Profile.ROLE_JOB_SEEKER).count()

    # Recent applications with optimized queries
    recent_applications = Application.objects.select_related(
        'job', 'applicant', 'applicant__profile', 'resume_analysis', 'resume_screening'
    ).order_by('-applied_at')[:8]

    # Recent jobs
    recent_jobs = Job.objects.all().order_by('-created_at')[:5]

    context = {
        'total_jobs': total_jobs,
        'active_jobs': active_jobs,
        'expired_jobs': expired_jobs,
        'total_applications': total_applications,
        'shortlisted_candidates': shortlisted_candidates,
        'total_users': total_users,
        'job_seekers_count': job_seekers_count,
        'recent_applications': recent_applications,
        'recent_jobs': recent_jobs,
        'active_admin_tab': 'dashboard',
    }
    return render(request, 'accounts/admin_dashboard.html', context)



@login_required
def profile_view(request):
    """
    View and update personal profile details.
    """
    user = request.user
    profile = user.profile

    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            # Save phone in profile
            phone = form.cleaned_data.get('phone', '').strip()
            profile.phone = phone
            profile.save()

            messages.success(request, 'Your profile details have been updated successfully.')
            return redirect('accounts:profile')
        else:
            messages.error(request, 'Please correct the errors in the profile form.')
    else:
        initial_data = {
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'phone': profile.phone or '',
        }
        form = ProfileUpdateForm(instance=user, initial=initial_data)

    context = {
        'form': form,
        'profile': profile,
    }
    return render(request, 'accounts/profile.html', context)
