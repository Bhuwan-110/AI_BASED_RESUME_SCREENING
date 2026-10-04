"""
Auto-seeding script for GURUKUL-CV.
Seeds:
1. Admin superuser (admin / admin123)
2. All 9 jobs (6 Active vacancies + 3 Expired vacancies with dynamic deadlines)
3. Graphic Designer candidates and evaluations
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gurukul.settings')
django.setup()

from datetime import timedelta
from django.utils import timezone
from django.contrib.auth.models import User
from jobs.models import Job
from accounts.models import Profile

def seed_database():
    today = timezone.now().date()
    print("--- [GURUKUL] Seeding Database ---")

    # 1. Admin Superuser
    admin_user, created = User.objects.get_or_create(
        username="admin",
        defaults={
            "email": "admin@gurukul.edu.np",
            "is_staff": True,
            "is_superuser": True,
            "first_name": "GURUKUL",
            "last_name": "Administrator",
        }
    )
    if created:
        admin_user.set_password("admin123")
        admin_user.save()
        print("Created superuser: admin / admin123")
    else:
        admin_user.is_staff = True
        admin_user.is_superuser = True
        admin_user.save()

    # Ensure admin profile has admin role
    profile, _ = Profile.objects.get_or_create(user=admin_user)
    profile.role = Profile.ROLE_ADMIN
    profile.save()

    # 2. Jobs definitions
    jobs_definitions = [
        # --- 6 ACTIVE VACANCIES ---
        {
            "id": 1,
            "title": "Loksewa GK & Current Affairs Lead Instructor",
            "department": "Loksewa Preparation",
            "description": "Lead daily lecture modules covering Constitution of Nepal, Public Governance, Contemporary Affairs, and Geopolitics for Section Officer aspirants.",
            "required_skills": "Loksewa Syllabus, Current Affairs Research, Presentation, Public Governance, Constitution of Nepal",
            "qualification": "Master's or Bachelor's in Political Science, Public Administration, Law or related discipline",
            "experience": "3+ Years teaching or civil service coaching experience",
            "job_type": "Full Time",
            "location": "Kathmandu (Putalisadak) / Hybrid",
            "deadline": today + timedelta(days=22),
        },
        {
            "id": 2,
            "title": "Secondary Mathematics Faculty (Classes 9 & 10 SEE)",
            "department": "School Education",
            "description": "Deliver structured lectures, concept problem sets, and weekly mock exams in Compulsory and Optional Mathematics for secondary students.",
            "required_skills": "Compulsory Math, Optional Math, SEE Syllabus, Student Mentoring, Lesson Planning",
            "qualification": "Bachelor's in Mathematics, Statistics, or Science Education",
            "experience": "2+ Years secondary school teaching experience",
            "job_type": "Part Time",
            "location": "Kathmandu / Online",
            "deadline": today + timedelta(days=15),
        },
        {
            "id": 3,
            "title": "Senior Physics Mentor (+2 Science & Engineering Entrance)",
            "department": "College Education",
            "description": "Conduct comprehensive problem-solving sessions and entrance coaching in Mechanics, Electromagnetism, and Modern Physics for Grades 11 and 12.",
            "required_skills": "NEB Physics Syllabus, IOE Entrance Coaching, Analytical Problem Solving, Laboratory Concepts",
            "qualification": "Master's or Bachelor's in Physics or Engineering",
            "experience": "2+ Years +2 teaching experience",
            "job_type": "Part Time",
            "location": "Kathmandu Office / Online",
            "deadline": today + timedelta(days=27),
        },
        {
            "id": 4,
            "title": "Curriculum & Question Bank Author - STEM",
            "department": "Curriculum & Content",
            "description": "Develop objective multiple-choice question banks, model test solutions, and syllabus-aligned notes for online study modules.",
            "required_skills": "Content Writing, STEM Pedagogy, Question Formulation, Proofreading, MS Word / LaTeX",
            "qualification": "Bachelor's or Master's in Science / Education / English",
            "experience": "1+ Years content development experience",
            "job_type": "Full Time",
            "location": "Kathmandu Office",
            "deadline": today + timedelta(days=11),
        },
        {
            "id": 15,
            "title": "Graphic Designer & Visual Media Specialist",
            "department": "Curriculum & Content",
            "description": "Looking for a creative Graphic Designer to create Loksewa preparation diagrams, visual learning infographics, course banners, and academic publishing layouts.",
            "required_skills": "Photoshop, Illustrator, Figma, Canva, After Effects, Typography",
            "qualification": "Bachelor's in Graphic Design, Fine Arts, or Multimedia",
            "experience": "2+ Years",
            "job_type": "Full Time",
            "location": "Kathmandu (Hybrid)",
            "deadline": today + timedelta(days=30),
        },
        {
            "id": 16,
            "title": "Secondary level math teacher",
            "department": "Loksewa Preparation",
            "description": "Math teacher for secondary level curriculum and problem-solving coaching.",
            "required_skills": "Interactive teaching learning, Bachelor completed, Curriculum planning",
            "qualification": "Bachelor's Degree",
            "experience": "2+ years of teaching experience",
            "job_type": "Part Time",
            "location": "Kathmandu / Online",
            "deadline": today + timedelta(days=7),
        },
        # --- 3 EXPIRED POSITIONS ---
        {
            "id": 14,
            "title": "Senior software developer",
            "department": "Curriculum & Content",
            "description": "Developed customer-facing applications using Java, Spring, JavaScript, and MySQL. Built authentication, reporting, payment, and notification modules.",
            "required_skills": "Senior Software Developer with 7+ years of experience designing, developing, and maintaining scalable web applications. Strong background in Java, Spring Boot, JavaScript, React, REST APIs, SQL, cloud deployment, and software architecture.",
            "qualification": "Bachelor of Information Technology",
            "experience": "7+ years",
            "job_type": "Part Time",
            "location": "Kathmandu / Online",
            "deadline": today - timedelta(days=2),
        },
        {
            "id": 5,
            "title": "Loksewa Nayab Subba First Paper Tutor (Batch 2025)",
            "department": "Loksewa Preparation",
            "description": "Delivered fast-track revision lectures and test discussions for Nayab Subba 2025 recruitment cycle.",
            "required_skills": "General Knowledge, IQ Tests, Speed Solving, Loksewa Curriculum",
            "qualification": "Bachelor's Degree in any discipline",
            "experience": "2+ Years coaching experience",
            "job_type": "Contract",
            "location": "Kathmandu",
            "deadline": today - timedelta(days=18),
        },
        {
            "id": 6,
            "title": "Civil Service Mock Interview Panelist (Fall 2025)",
            "department": "Academic Mentorship",
            "description": "Conducted mock interview boards and provided behavioral and technical feedback for written-qualified candidates.",
            "required_skills": "Civil Service Interview Protocols, Public Ethics, Mock Evaluation",
            "qualification": "Former Civil Servant or Senior Gazetted Officer",
            "experience": "5+ Years public service experience",
            "job_type": "Contract",
            "location": "Kathmandu Center",
            "deadline": today - timedelta(days=43),
        },
    ]

    for item in jobs_definitions:
        job_id = item["id"]
        job, created_flag = Job.objects.update_or_create(
            id=job_id,
            defaults={
                "title": item["title"],
                "department": item["department"],
                "description": item["description"],
                "required_skills": item["required_skills"],
                "qualification": item["qualification"],
                "experience": item["experience"],
                "job_type": item["job_type"],
                "location": item["location"],
                "deadline": item["deadline"],
            }
        )
        status_str = "ACTIVE" if job.deadline >= today else "EXPIRED"
        print(f"  [{status_str}] Job #{job.id}: {job.title} (Deadline: {job.deadline})")

    # 3. Apply the 15 Graphic Designer candidates with exact matching scores & PDFs
    try:
        from set_exact_graphic_designer_candidates import apply as apply_graphic_designer_candidates
        apply_graphic_designer_candidates()
        print("  Successfully populated Graphic Designer candidates & evaluations.")
    except Exception as e:
        print(f"  Note: candidate seeding skipped or encountered: {e}")

    active_count = Job.objects.filter(deadline__gte=today).count()
    expired_count = Job.objects.filter(deadline__lt=today).count()
    print(f"--- Seeding Complete: {active_count} Active Vacancies, {expired_count} Expired Positions ---")

if __name__ == '__main__':
    seed_database()
