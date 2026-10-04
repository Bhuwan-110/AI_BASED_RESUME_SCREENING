from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from jobs.models import Job
from applications.models import Application
from resume_ai.models import ResumeExtraction, ResumeAnalysis
from accounts.models import Profile


class Command(BaseCommand):
    help = "Populates 5 diverse sample candidate applications for testing Batch Resume Screening."

    def handle(self, *args, **options):
        today = timezone.now().date()
        job, created = Job.objects.get_or_create(
            title="Graphic Designer & Visual Media Specialist",
            defaults={
                'department': 'Media & Digital Learning',
                'description': 'Looking for a creative Graphic Designer to create Loksewa preparation diagrams, visual learning infographics, course banners, and academic publishing layouts.',
                'required_skills': 'Photoshop, Illustrator, Figma, Canva, After Effects, Typography',
                'qualification': "Bachelor's in Graphic Design, Fine Arts, or Multimedia",
                'experience': '2+ Years',
                'job_type': 'Full Time',
                'location': 'Kathmandu (Hybrid)',
                'deadline': today + timedelta(days=45),
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f"Created sample vacancy: '{job.title}' (ID #{job.id})"))
        else:
            self.stdout.write(f"Using existing vacancy: '{job.title}' (ID #{job.id})")

        sample_candidates = [
            {
                'username': 'candidate_anita_designer',
                'full_name': 'Anita Maharjan',
                'email': 'anita.designer@example.com',
                'text': 'Creative Graphic Designer with 4 years experience in digital educational media. Expert in Adobe Photoshop, Adobe Illustrator, Figma UI design, Canva quick layouts, and typography for printed test prep books.',
                'status': ResumeExtraction.STATUS_SUCCESS,
                'err': ''
            },
            {
                'username': 'candidate_bikram_ui',
                'full_name': 'Bikram Thapa',
                'email': 'bikram.ui@example.com',
                'text': 'Visual Designer with strong background in Photoshop, Illustrator, and Figma wireframing. Experience producing academic slides and social media graphics.',
                'status': ResumeExtraction.STATUS_SUCCESS,
                'err': ''
            },
            {
                'username': 'candidate_chandra_art',
                'full_name': 'Chandra Gurung',
                'email': 'chandra.art@example.com',
                'text': 'Junior designer proficient in Canva and Adobe Photoshop with keen eye for digital illustration and visual aesthetics. 1 year agency internship experience.',
                'status': ResumeExtraction.STATUS_SUCCESS,
                'err': ''
            },
            {
                'username': 'candidate_deepa_web',
                'full_name': 'Deepa Shrestha',
                'email': 'deepa.web@example.com',
                'text': 'Front-end web developer with HTML, CSS, JavaScript, and basic Canva skills for creating web assets.',
                'status': ResumeExtraction.STATUS_SUCCESS,
                'err': ''
            },
            {
                'username': 'candidate_elena_scanned',
                'full_name': 'Elena Karki',
                'email': 'elena.karki@example.com',
                'text': '',
                'status': ResumeExtraction.STATUS_EMPTY,
                'err': 'Uploaded CV has no readable text (scanned image or empty document).'
            },
        ]

        count = 0
        for data in sample_candidates:
            user, _ = User.objects.get_or_create(
                username=data['username'],
                defaults={
                    'email': data['email'],
                    'first_name': data['full_name'].split()[0],
                    'last_name': ' '.join(data['full_name'].split()[1:]),
                }
            )
            user.set_password('password123')
            user.save()
            if hasattr(user, 'profile'):
                user.profile.role = Profile.ROLE_JOB_SEEKER
                user.profile.save()

            app, app_created = Application.objects.get_or_create(
                job=job,
                applicant=user,
                defaults={
                    'status': Application.STATUS_APPLIED,
                }
            )

            # Create or update extraction record
            ResumeExtraction.objects.update_or_create(
                application=app,
                defaults={
                    'extracted_text': data['text'],
                    'page_count': 1 if data['text'] else 0,
                    'status': data['status'],
                    'error_message': data['err'],
                }
            )
            count += 1

        self.stdout.write(self.style.SUCCESS(
            f"Successfully seeded {count} sample candidates for Job #{job.id} ('{job.title}').\n"
            f"Navigate to Admin Dashboard -> Applicants -> Select '{job.title}' to test [ Analyze All CVs ]!"
        ))
