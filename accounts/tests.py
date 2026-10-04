from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from accounts.models import Profile
from jobs.models import Job
from applications.models import Application
import tempfile

class AdminDashboardTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Create Admin user
        self.admin_user = User.objects.create_user(
            username='adminuser',
            email='admin@gurukul.edu.np',
            password='secretpassword123',
            first_name='Admin',
            last_name='Evaluator'
        )
        self.admin_profile = self.admin_user.profile
        self.admin_profile.role = Profile.ROLE_ADMIN
        self.admin_profile.save()

        # Create Job Seeker user
        self.seeker_user = User.objects.create_user(
            username='seekeruser',
            email='seeker@example.com',
            password='secretpassword123',
            first_name='Seeker',
            last_name='Candidate'
        )

        today = timezone.now().date()

        # Create 1 Active Job
        self.active_job = Job.objects.create(
            title='Loksewa Nepali Lecturer',
            department='Loksewa Preparation',
            description='Teach Loksewa candidates Nepali literature and grammar.',
            required_skills='Nepali, Teaching, Grammar',
            qualification="Master's in Nepali",
            experience='2+ Years',
            job_type='Full Time',
            location='Kathmandu',
            deadline=today + timedelta(days=15)
        )

        # Create 1 Expired Job
        self.expired_job = Job.objects.create(
            title='SEE Mathematics Tutor',
            department='School Education',
            description='Guide SEE students in mathematics.',
            required_skills='Math, Algebra, Geometry',
            qualification="Bachelor's in Mathematics",
            experience='1+ Year',
            job_type='Part Time',
            location='Online',
            deadline=today - timedelta(days=5)
        )

        # Create 1 Application (Applied)
        self.app_applied = Application.objects.create(
            job=self.active_job,
            applicant=self.seeker_user,
            status=Application.STATUS_APPLIED
        )

        # Create 2nd Job Seeker for a shortlisted application
        self.seeker2 = User.objects.create_user(
            username='seeker2',
            email='seeker2@example.com',
            password='secretpassword123',
            first_name='Shortlisted',
            last_name='Applicant'
        )
        self.app_shortlisted = Application.objects.create(
            job=self.active_job,
            applicant=self.seeker2,
            status=Application.STATUS_SHORTLISTED
        )

    def test_admin_dashboard_requires_login(self):
        url = reverse('accounts:admin_dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_job_seeker_cannot_access_admin_dashboard(self):
        self.client.login(username='seekeruser', password='secretpassword123')
        url = reverse('accounts:admin_dashboard')
        response = self.client.get(url)
        # admin_required decorator redirects non-admins
        self.assertEqual(response.status_code, 302)

    def test_admin_dashboard_metrics(self):
        self.client.login(username='adminuser', password='secretpassword123')
        url = reverse('accounts:admin_dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # Verify context metrics
        self.assertEqual(response.context['total_jobs'], 2)
        self.assertEqual(response.context['active_jobs'], 1)
        self.assertEqual(response.context['expired_jobs'], 1)
        self.assertEqual(response.context['total_applications'], 2)
        self.assertEqual(response.context['shortlisted_candidates'], 1)

        # Verify content contains visual cards labels
        content = response.content.decode('utf-8')
        self.assertIn('Total Jobs', content)
        self.assertIn('Active Jobs', content)
        self.assertIn('Expired Jobs', content)
        self.assertIn('Total Applications', content)
        self.assertIn('Shortlisted Candidates', content)

        # Verify admin navigation links
        self.assertIn('Dashboard', content)
        self.assertIn('Jobs', content)
        self.assertIn('Applicants', content)
        self.assertIn('Profile', content)
        self.assertIn('Logout', content)


class JobSeekerDashboardTests(TestCase):
    def setUp(self):
        self.client = Client()

        self.seeker = User.objects.create_user(
            username='ram_seeker',
            email='ram@gurukul.edu.np',
            password='password123',
            first_name='Ram',
            last_name='Bahadur'
        )

        self.admin = User.objects.create_user(
            username='admin_staff',
            email='admin@gurukul.edu.np',
            password='password123'
        )
        self.admin.profile.role = Profile.ROLE_ADMIN
        self.admin.profile.save()

        today = timezone.now().date()
        self.job1 = Job.objects.create(
            title='Nepali Teacher',
            department='School Education',
            description='Nepali language instructor.',
            required_skills='Nepali, Teaching',
            qualification="Bachelor's in Nepali",
            experience='1+ Year',
            deadline=today + timedelta(days=20)
        )
        self.job2 = Job.objects.create(
            title='Science Teacher',
            department='School Education',
            description='Science instructor.',
            required_skills='Physics, Chemistry',
            qualification="Bachelor's in Science",
            experience='2+ Years',
            deadline=today + timedelta(days=20)
        )

        # Create applications with various statuses
        self.app1 = Application.objects.create(
            job=self.job1,
            applicant=self.seeker,
            status=Application.STATUS_UNDER_REVIEW
        )
        self.app2 = Application.objects.create(
            job=self.job2,
            applicant=self.seeker,
            status=Application.STATUS_SHORTLISTED
        )

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse('accounts:dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_admin_redirected_to_admin_dashboard(self):
        self.client.login(username='admin_staff', password='password123')
        response = self.client.get(reverse('accounts:dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/admin-dashboard/', response.url)

    def test_seeker_dashboard_metrics_and_content(self):
        self.client.login(username='ram_seeker', password='password123')
        response = self.client.get(reverse('accounts:dashboard'))
        self.assertEqual(response.status_code, 200)

        # Verify metrics
        self.assertEqual(response.context['total_applications'], 2)
        self.assertEqual(response.context['under_review_count'], 1)
        self.assertEqual(response.context['shortlisted_count'], 1)
        self.assertEqual(response.context['rejected_count'], 0)

        content = response.content.decode('utf-8')
        # Verify 4 visual cards
        self.assertIn('Total Applications', content)
        self.assertIn('Under Review', content)
        self.assertIn('Shortlisted', content)
        self.assertIn('Rejected', content)

        # Verify navigation
        self.assertIn('Dashboard', content)
        self.assertIn('Career', content)
        self.assertIn('My Applications', content)
        self.assertIn('Profile', content)
        self.assertIn('Logout', content)

        # Verify recent applications listed
        self.assertIn('Nepali Teacher', content)
        self.assertIn('Science Teacher', content)

        # Verify NO internal AI analysis / scores exposed to job seeker
        self.assertNotIn('Cosine Similarity', content)
        self.assertNotIn('TF-IDF', content)
        self.assertNotIn('match_percentage', content)
        self.assertNotIn('Analyze CV', content)

