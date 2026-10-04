from django.shortcuts import render, redirect
from django.contrib import messages

def home(request):
    """
    Public Homepage for GURUKUL.
    Includes Hero, About GURUKUL, What We Provide, Our Team, Completed Works, and Career CTA.
    """
    what_we_provide = [
        {
            'icon': 'bi-camera-video',
            'title': 'Interactive Live Preparation',
            'description': 'Real-time lectures and problem-solving workshops led by experienced educators and civil service officers.'
        },
        {
            'icon': 'bi-journal-check',
            'title': 'Curated Syllabus Material',
            'description': 'Topic-wise study modules, comprehensive lecture notes, and structured question banks aligned with current curricula.'
        },
        {
            'icon': 'bi-file-earmark-bar-graph',
            'title': 'Mock Tests & Feedback',
            'description': 'Regular weekly mock tests, objective answer evaluations, and personalized performance feedback for students.'
        },
        {
            'icon': 'bi-people',
            'title': 'Academic Mentorship',
            'description': 'Direct guidance from senior faculty, subject specialists, and mentors for study strategy and exam confidence.'
        }
    ]

    team_members = [
        {
            'name': 'Prof. Narayan Prasad Sharma',
            'position': 'Academic Advisor & Loksewa Lead',
            'description': 'Over 15 years guiding civil service aspirants in Governance, Public Administration, and Constitution.'
        },
        {
            'name': 'Sunita Adhikari',
            'position': 'Senior Faculty - School Mathematics',
            'description': 'Specialist in foundational secondary mathematics (SEE) and conceptual STEM curriculum design.'
        },
        {
            'name': 'Bikash Karki',
            'position': 'Faculty - Higher Secondary Science (+2)',
            'description': 'Dedicated educator in Physics and Entrance Coaching, focusing on concept clarity and analytical problem solving.'
        },
        {
            'name': 'Pooja Thapa',
            'position': 'Student Mentorship & Career Guidance Coordinator',
            'description': 'Coordinates student orientation, faculty feedback loops, and individual mentoring schedules.'
        }
    ]

    completed_works = [
        {
            'title': 'Loksewa Section Officer Model Exam Series',
            'category': 'Civil Service Preparation',
            'description': 'Conducted structured mock exam series covering General Studies, English, and Governance papers with detailed solution discussions.'
        },
        {
            'title': 'SEE Mathematics & Science Foundation Program',
            'category': 'School Level Education',
            'description': 'Delivered comprehensive conceptual revision modules and solved past exam papers for secondary students.'
        },
        {
            'title': '+2 Science & Management Concept Refresher',
            'category': 'College Curriculum',
            'description': 'Held focused problem-solving tutorials and bridge guidance for board exam preparations.'
        },
        {
            'title': 'Civil Service Interview Orientation Workshop',
            'category': 'Mentorship & Advisory',
            'description': 'Arranged simulated mock interview sessions and feedback panels for written-exam qualified candidates.'
        }
    ]

    context = {
        'what_we_provide': what_we_provide,
        'team_members': team_members,
        'completed_works': completed_works,
    }
    return render(request, 'core/home.html', context)


def about(request):
    """
    Public About Page for GURUKUL.
    Presents organization background, mission, values, and educational pillars.
    """
    return render(request, 'core/about.html')


def contact(request):
    """
    Public Contact Page for GURUKUL.
    Provides contact info and processes inquiry messages with validation and feedback.
    """
    if request.method == 'POST':
        full_name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        subject = request.POST.get('subject', '').strip()
        message = request.POST.get('message', '').strip()

        if not full_name or not email or not subject or not message:
            messages.error(request, 'Please complete all required fields before submitting your message.')
        elif '@' not in email or '.' not in email:
            messages.error(request, 'Please provide a valid email address.')
        else:
            messages.success(request, f'Thank you, {full_name}! Your message has been received. Our academic team will respond soon.')
            return redirect('core:contact')

    return render(request, 'core/contact.html')


from django.utils import timezone
from jobs.models import Job

def career(request):
    """
    Public Career Page for GURUKUL.
    Displays ACTIVE JOBS and EXPIRED JOBS dynamically queried from the database.
    Auto-seeds vacancies if no active openings exist (e.g. on fresh Render deployment).
    """
    today = timezone.now().date()
    import sys
    if 'test' not in sys.argv and not Job.objects.filter(deadline__gte=today).exists():
        try:
            from populate_all_jobs_and_applicants import seed_database
            seed_database()
        except Exception:
            pass

    active_jobs = Job.objects.filter(deadline__gte=today).order_by('deadline')
    expired_jobs = Job.objects.filter(deadline__lt=today).order_by('-deadline')

    context = {
        'active_jobs': active_jobs,
        'expired_jobs': expired_jobs,
        'today': today,
    }
    return render(request, 'core/career.html', context)


def design_system(request):
    """
    Interactive Design System Showcase.
    Demonstrates typography, color tokens, buttons, cards, forms,
    alerts, badges, tables, modals, loading states, and empty states.
    """
    return render(request, 'core/design_system.html')
