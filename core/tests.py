from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from jobs.models import Job

class CorePagesTests(TestCase):
    def setUp(self):
        self.client = Client()
        today = timezone.now().date()
        self.active_job = Job.objects.create(
            title='Loksewa Nepali Instructor',
            department='Loksewa Preparation',
            description='Teach Loksewa Nepali syllabus.',
            required_skills='Nepali, Teaching, Grammar',
            qualification="Master's in Nepali",
            experience='2+ Years',
            job_type='Full Time',
            location='Putalisadak, Kathmandu',
            deadline=today + timedelta(days=15)
        )
        self.expired_job = Job.objects.create(
            title='Secondary Science Teacher',
            department='School Education',
            description='Teach secondary science.',
            required_skills='Science, Physics, Chemistry',
            qualification="Bachelor's in Science",
            experience='1+ Year',
            job_type='Part Time',
            location='Online',
            deadline=today - timedelta(days=5)
        )

    def test_home_page(self):
        response = self.client.get(reverse('core:home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/home.html')
        self.assertIn('what_we_provide', response.context)
        self.assertIn('team_members', response.context)
        self.assertIn('completed_works', response.context)
        content = response.content.decode('utf-8')
        self.assertIn('Empowering Learners Through Quality Education', content)

    def test_about_page(self):
        response = self.client.get(reverse('core:about'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/about.html')
        content = response.content.decode('utf-8')
        self.assertIn('About GURUKUL', content)

    def test_contact_page_get(self):
        response = self.client.get(reverse('core:contact'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/contact.html')

    def test_contact_page_post_empty_fields_error(self):
        response = self.client.post(reverse('core:contact'), {
            'name': '',
            'email': '',
            'subject': '',
            'message': ''
        })
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn('Please complete all required fields', content)

    def test_contact_page_post_invalid_email_error(self):
        response = self.client.post(reverse('core:contact'), {
            'name': 'Bikash',
            'email': 'not-an-email',
            'subject': 'Inquiry',
            'message': 'Hello there'
        })
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn('Please provide a valid email address', content)

    def test_contact_page_post_success(self):
        response = self.client.post(reverse('core:contact'), {
            'name': 'Bikash Karki',
            'email': 'bikash@example.com',
            'subject': 'Batch timing inquiry',
            'message': 'When does the new batch start?'
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn('Thank you, Bikash Karki!', content)

    def test_career_page_displays_active_and_expired(self):
        response = self.client.get(reverse('core:career'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/career.html')

        active_jobs = list(response.context['active_jobs'])
        expired_jobs = list(response.context['expired_jobs'])
        self.assertIn(self.active_job, active_jobs)
        self.assertNotIn(self.expired_job, active_jobs)
        self.assertIn(self.expired_job, expired_jobs)
        self.assertNotIn(self.active_job, expired_jobs)

        content = response.content.decode('utf-8')
        self.assertIn('ACTIVE JOBS', content)
        self.assertIn('EXPIRED JOBS', content)
        self.assertIn('Loksewa Nepali Instructor', content)
        self.assertIn('Secondary Science Teacher', content)

    def test_design_system_page(self):
        response = self.client.get(reverse('core:design_system'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/design_system.html')
