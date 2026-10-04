from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from accounts.models import Profile
from jobs.models import Job
from applications.models import Application
from resume_ai.models import ResumeAnalysis

class AdminApplicantsTests(TestCase):
    def setUp(self):
        self.client = Client()

        self.admin = User.objects.create_user(
            username='admin_applicant_test',
            email='evaluator@gurukul.edu.np',
            password='adminsecretpass'
        )
        self.admin.profile.role = Profile.ROLE_ADMIN
        self.admin.profile.save()

        self.seeker1 = User.objects.create_user(
            username='candidate_one',
            email='cand1@example.com',
            password='secretpassword',
            first_name='Aarav',
            last_name='Sharma'
        )

        self.seeker2 = User.objects.create_user(
            username='candidate_two',
            email='cand2@example.com',
            password='secretpassword',
            first_name='Binita',
            last_name='Adhikari'
        )

        today = timezone.now().date()
        self.job1 = Job.objects.create(
            title='Loksewa Section Officer Mentor',
            department='Loksewa Preparation',
            description='Mentor candidates for Loksewa civil service examination.',
            required_skills='Public Administration, Constitutional Law, Current Affairs',
            qualification="Master's in Public Administration",
            experience='3+ Years',
            job_type='Full Time',
            location='Putalisadak, Kathmandu',
            deadline=today + timedelta(days=25)
        )

        self.job2 = Job.objects.create(
            title='Secondary School English Instructor',
            department='School Education',
            description='Teach English for Class 9 and 10 SEE.',
            required_skills='English, Literature, Grammar',
            qualification="Bachelor's in English",
            experience='2+ Years',
            job_type='Full Time',
            location='Kathmandu',
            deadline=today + timedelta(days=20)
        )

        # Application 1 for Job 1
        self.app1 = Application.objects.create(
            job=self.job1,
            applicant=self.seeker1,
            status=Application.STATUS_APPLIED
        )

        # Analysis for Application 1
        self.analysis1 = ResumeAnalysis.objects.create(
            application=self.app1,
            match_percentage=82.5,
            matched_skills=['Public Administration', 'Constitutional Law'],
            missing_skills=['Current Affairs'],
            qualification_match='Matched',
            experience_match='Needs Verification',
            explanation='Good match with required skills.'
        )

        # Application 2 for Job 2
        self.app2 = Application.objects.create(
            job=self.job2,
            applicant=self.seeker2,
            status=Application.STATUS_UNDER_REVIEW
        )

    def test_admin_applicants_requires_admin(self):
        # Unauthenticated
        response = self.client.get(reverse('applications:admin_applicants'))
        self.assertEqual(response.status_code, 302)

        # Job seeker
        self.client.login(username='candidate_one', password='secretpassword')
        response = self.client.get(reverse('applications:admin_applicants'))
        self.assertEqual(response.status_code, 302)

    def test_admin_applicants_all(self):
        self.client.login(username='admin_applicant_test', password='adminsecretpass')
        response = self.client.get(reverse('applications:admin_applicants'))
        self.assertEqual(response.status_code, 200)

        # Shows both applicants
        self.assertEqual(response.context['filtered_count'], 2)
        content = response.content.decode('utf-8')
        self.assertIn('Aarav Sharma', content)
        self.assertIn('Binita Adhikari', content)
        self.assertIn('82.5%', content)
        self.assertIn('Applied', content)
        self.assertIn('Under Review', content)
        self.assertIn('Confirm Candidate Rejection', content)

    def test_admin_applicants_job_filter(self):
        self.client.login(username='admin_applicant_test', password='adminsecretpass')
        response = self.client.get(reverse('applications:admin_applicants') + f'?job={self.job1.pk}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['filtered_count'], 1)
        applicants = list(response.context['applicants'])
        self.assertIn(self.app1, applicants)
        self.assertNotIn(self.app2, applicants)

    def test_admin_applicants_status_filter(self):
        self.client.login(username='admin_applicant_test', password='adminsecretpass')
        response = self.client.get(reverse('applications:admin_applicants') + '?status=Applied')
        self.assertEqual(response.status_code, 200)
        applicants = list(response.context['applicants'])
        self.assertIn(self.app1, applicants)
        self.assertNotIn(self.app2, applicants)

    def test_quick_shortlist(self):
        self.client.login(username='admin_applicant_test', password='adminsecretpass')
        url = reverse('applications:quick_shortlist', kwargs={'pk': self.app1.pk})
        response = self.client.post(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.app1.refresh_from_db()
        self.assertEqual(self.app1.status, Application.STATUS_SHORTLISTED)

    def test_update_status_to_rejected(self):
        self.client.login(username='admin_applicant_test', password='adminsecretpass')
        url = reverse('applications:update_status', kwargs={'pk': self.app2.pk})
        response = self.client.post(url, {'status': 'Rejected'}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.app2.refresh_from_db()
        self.assertEqual(self.app2.status, Application.STATUS_REJECTED)

    def test_job_applicants_redirect(self):
        self.client.login(username='admin_applicant_test', password='adminsecretpass')
        url = reverse('applications:job_applicants', kwargs={'job_id': self.job1.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(f'job={self.job1.pk}', response.url)

    def test_empty_state_when_no_matching_applicants(self):
        self.client.login(username='admin_applicant_test', password='adminsecretpass')
        # Filter for Shortlisted when none are shortlisted
        response = self.client.get(reverse('applications:admin_applicants') + '?status=Shortlisted')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['filtered_count'], 0)
        content = response.content.decode('utf-8')
        self.assertIn('No \'Shortlisted\' Candidates Found', content)


class MyApplicationsTests(TestCase):
    def setUp(self):
        self.client = Client()

        self.candidate = User.objects.create_user(
            username='anita_seeker',
            email='anita@example.com',
            password='mypassword123',
            first_name='Anita',
            last_name='Poudel'
        )

        self.other_candidate = User.objects.create_user(
            username='other_seeker',
            email='other@example.com',
            password='mypassword123'
        )

        today = timezone.now().date()
        self.job = Job.objects.create(
            title='Loksewa Public Administration Instructor',
            department='Loksewa Preparation',
            description='Civil service instructor.',
            required_skills='Public Admin, Governance',
            qualification="Master's in Public Admin",
            experience='2+ Years',
            deadline=today + timedelta(days=30)
        )

        self.application = Application.objects.create(
            job=self.job,
            applicant=self.candidate,
            status=Application.STATUS_APPLIED
        )

        self.other_application = Application.objects.create(
            job=self.job,
            applicant=self.other_candidate,
            status=Application.STATUS_SHORTLISTED
        )

        # Create AI Analysis for Anita's application
        self.analysis = ResumeAnalysis.objects.create(
            application=self.application,
            match_percentage=88.0,
            matched_skills=['Public Admin', 'Governance'],
            missing_skills=[],
            qualification_match='Matched',
            experience_match='Matched',
            explanation='Top candidate profile.'
        )

    def test_my_applications_requires_login(self):
        response = self.client.get(reverse('applications:my_applications'))
        self.assertEqual(response.status_code, 302)

    def test_my_applications_display_and_privacy(self):
        self.client.login(username='anita_seeker', password='mypassword123')
        response = self.client.get(reverse('applications:my_applications'))
        self.assertEqual(response.status_code, 200)

        # Anita only sees her own applications
        self.assertEqual(response.context['total_count'], 1)
        apps = list(response.context['applications'])
        self.assertIn(self.application, apps)
        self.assertNotIn(self.other_application, apps)

        content = response.content.decode('utf-8')
        # Shows Job, Applied Date, Status, View Application, View Job
        self.assertIn('Loksewa Public Administration Instructor', content)
        self.assertIn('Applied', content)
        self.assertIn('View Application', content)
        self.assertIn('View Job', content)

        # PRIVACY GUARANTEE: Does NOT expose AI analysis or scores to candidate
        self.assertNotIn('88.0%', content)
        self.assertNotIn('Cosine Similarity', content)
        self.assertNotIn('TF-IDF', content)
        self.assertNotIn('matched_skills', content)
        self.assertNotIn('other_seeker', content)

    def test_view_application_privacy_for_seeker(self):
        self.client.login(username='anita_seeker', password='mypassword123')
        url = reverse('applications:view_application', kwargs={'pk': self.application.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        content = response.content.decode('utf-8')
        self.assertIn('Loksewa Public Administration Instructor', content)
        self.assertIn('Application Review Status: Applied', content)

        # STRICT PRIVACY: AI screening and admin status dropdown MUST NOT be visible to seeker
        self.assertNotIn('AI Resume Screening (Decision Support)', content)
        self.assertNotIn('88.0%', content)
        self.assertNotIn('Administrator Evaluation Control', content)

    def test_seeker_cannot_view_others_application(self):
        self.client.login(username='anita_seeker', password='mypassword123')
        url = reverse('applications:view_application', kwargs={'pk': self.other_application.pk})
        response = self.client.get(url)
        # Access denied, redirects to my_applications
        self.assertEqual(response.status_code, 302)
        self.assertIn('/applications/my-applications/', response.url)

