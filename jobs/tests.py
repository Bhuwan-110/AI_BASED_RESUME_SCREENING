from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from accounts.models import Profile
from jobs.models import Job

class JobsManagementTests(TestCase):
    def setUp(self):
        self.client = Client()

        self.admin = User.objects.create_user(
            username='admin_test',
            email='admin_jobs@gurukul.edu.np',
            password='pass123admin'
        )
        self.admin.profile.role = Profile.ROLE_ADMIN
        self.admin.profile.save()

        self.seeker = User.objects.create_user(
            username='seeker_test',
            email='seeker_jobs@gurukul.edu.np',
            password='pass123seeker'
        )

        today = timezone.now().date()
        self.active_job = Job.objects.create(
            title='Physics Teacher (+2)',
            department='College Education',
            description='Teach higher secondary physics.',
            required_skills='Physics, Mechanics, Optics',
            qualification="Master's in Physics",
            experience='3+ Years',
            job_type='Full Time',
            location='Lalitpur',
            deadline=today + timedelta(days=20)
        )
        self.expired_job = Job.objects.create(
            title='Chemistry Instructor',
            department='College Education',
            description='Teach organic chemistry.',
            required_skills='Chemistry, Lab Work',
            qualification="Master's in Chemistry",
            experience='2+ Years',
            job_type='Part Time',
            location='Online',
            deadline=today - timedelta(days=10)
        )

    def test_manage_jobs_active_filter(self):
        self.client.login(username='admin_test', password='pass123admin')
        response = self.client.get(reverse('jobs:manage_jobs') + '?status=active')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['active_count'], 1)
        self.assertEqual(response.context['expired_count'], 1)
        self.assertEqual(response.context['total_count'], 2)
        jobs = list(response.context['jobs'])
        self.assertIn(self.active_job, jobs)
        self.assertNotIn(self.expired_job, jobs)

    def test_manage_jobs_expired_filter(self):
        self.client.login(username='admin_test', password='pass123admin')
        response = self.client.get(reverse('jobs:manage_jobs') + '?status=expired')
        self.assertEqual(response.status_code, 200)
        jobs = list(response.context['jobs'])
        self.assertIn(self.expired_job, jobs)
        self.assertNotIn(self.active_job, jobs)

    def test_manage_jobs_all(self):
        self.client.login(username='admin_test', password='pass123admin')
        response = self.client.get(reverse('jobs:manage_jobs') + '?status=all')
        self.assertEqual(response.status_code, 200)
        jobs = list(response.context['jobs'])
        self.assertEqual(len(jobs), 2)
        content = response.content.decode('utf-8')
        self.assertIn('Create Job', content)

    def test_job_detail_active(self):
        response = self.client.get(reverse('jobs:job_detail', kwargs={'pk': self.active_job.pk}))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn('ACTIVE', content)
        self.assertIn('Physics Teacher (+2)', content)

    def test_job_detail_expired(self):
        response = self.client.get(reverse('jobs:job_detail', kwargs={'pk': self.expired_job.pk}))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn('EXPIRED', content)
        self.assertIn('Application Closed', content)

    def test_create_job(self):
        self.client.login(username='admin_test', password='pass123admin')
        today = timezone.now().date()
        response = self.client.post(reverse('jobs:create_job'), {
            'title': 'Mathematics Lead Faculty',
            'department': 'School Education',
            'job_type': 'Full Time',
            'location': 'Kathmandu',
            'qualification': "Master's in Mathematics",
            'experience': '3+ Years',
            'deadline': (today + timedelta(days=30)).strftime('%Y-%m-%d'),
            'required_skills': 'Math, Algebra, Geometry',
            'description': 'Lead mathematics curriculum and mentoring.'
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        created = Job.objects.filter(title='Mathematics Lead Faculty').first()
        self.assertIsNotNone(created)

    def test_edit_job(self):
        self.client.login(username='admin_test', password='pass123admin')
        today = timezone.now().date()
        response = self.client.post(reverse('jobs:edit_job', kwargs={'pk': self.active_job.pk}), {
            'title': 'Physics Teacher (+2) - Updated',
            'department': 'College Education',
            'job_type': 'Part Time',
            'location': 'Kathmandu Online',
            'qualification': "Master's in Physics",
            'experience': '4+ Years',
            'deadline': (today + timedelta(days=40)).strftime('%Y-%m-%d'),
            'required_skills': 'Physics, Quantum, Optics',
            'description': 'Updated physics duties.'
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.active_job.refresh_from_db()
        self.assertEqual(self.active_job.title, 'Physics Teacher (+2) - Updated')
        self.assertEqual(self.active_job.job_type, 'Part Time')

    def test_delete_job(self):
        self.client.login(username='admin_test', password='pass123admin')
        url = reverse('jobs:delete_job', kwargs={'pk': self.expired_job.pk})
        get_resp = self.client.get(url)
        self.assertEqual(get_resp.status_code, 200)
        post_resp = self.client.post(url, follow=True)
        self.assertEqual(post_resp.status_code, 200)
        self.assertFalse(Job.objects.filter(pk=self.expired_job.pk).exists())

    def test_non_admin_cannot_access_manage_jobs(self):
        self.client.login(username='seeker_test', password='pass123seeker')
        response = self.client.get(reverse('jobs:manage_jobs'))
        self.assertEqual(response.status_code, 302)
