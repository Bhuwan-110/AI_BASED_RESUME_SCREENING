import os
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

from jobs.models import Job
from applications.models import Application
from resume_ai.models import ResumeExtraction, ResumeScreening, ResumeAnalysis
from resume_ai.service import (
    ResumeScreeningService,
    calculate_resume_match,
    clean_text,
    normalize_for_matching,
    match_required_skills,
    evaluate_qualification,
    evaluate_experience,
    generate_explanation
)


class ResumeScreeningNLPTests(TestCase):
    """
    Unit tests for core NLP text cleaning, TF-IDF vectorization, and Cosine Similarity screening.
    Designed for academic validation and defense demonstration.
    """

    def test_clean_text_normalizes_case_and_punctuation(self):
        raw_text = "  Hello, World!! Python 3.10 & Django...  "
        cleaned = clean_text(raw_text)
        self.assertEqual(cleaned, "hello world python 3 10 django")

    def test_clean_text_handles_none_and_empty(self):
        self.assertEqual(clean_text(None), "")
        self.assertEqual(clean_text(""), "")
        self.assertEqual(clean_text("   \n\t  "), "")

    def test_successful_match_calculation(self):
        job_desc = "We need an experienced Loksewa preparation instructor with deep knowledge of Constitution and Public Administration."
        skills = "Loksewa, Constitution, Public Administration, Teaching"
        cv_text = "Educator specializing in Loksewa exam prep, Constitution of Nepal, and Public Administration with 5 years classroom teaching."

        result = calculate_resume_match(job_desc, skills, cv_text)

        self.assertEqual(result['status'], 'SUCCESS')
        self.assertGreater(result['match_percentage'], 20.0)
        self.assertGreater(result['similarity_score'], 0.20)
        self.assertIsInstance(result['job_vector'], dict)
        self.assertIsInstance(result['resume_vector'], dict)
        self.assertIn('loksewa', result['job_vector'])
        self.assertIn('loksewa', result['resume_vector'])
        self.assertTrue(result['is_decision_support_only'])
        self.assertIsNone(result['error_message'])

    def test_zero_match_disjoint_vocabulary(self):
        job_desc = "Quantum physics laboratory researcher studying condensed matter states and superconductivity."
        skills = "Quantum, Cryogenics, Superconductivity"
        cv_text = "Executive pastry chef expert in artisan bread baking, chocolate sculpting, and wedding cake decorations."

        result = calculate_resume_match(job_desc, skills, cv_text)

        self.assertEqual(result['status'], 'SUCCESS')
        self.assertEqual(result['similarity_score'], 0.0)
        self.assertEqual(result['match_percentage'], 0.0)
        self.assertEqual(len(result['matched_keywords']), 0)

    def test_empty_job_description_error(self):
        result = calculate_resume_match(
            job_description="",
            required_skills="Python, Django",
            resume_text="Experienced Python and Django developer."
        )
        self.assertEqual(result['status'], 'ERROR')
        self.assertEqual(result['error_type'], 'EMPTY_JOB_DESCRIPTION')
        self.assertEqual(result['match_percentage'], 0.0)
        self.assertEqual(result['similarity_score'], 0.0)
        self.assertIn('empty or missing', result['error_message'])

    def test_empty_cv_text_error(self):
        result = calculate_resume_match(
            job_description="Loksewa Instructor needed.",
            required_skills="Loksewa, GK",
            resume_text=""
        )
        self.assertEqual(result['status'], 'ERROR')
        self.assertEqual(result['error_type'], 'EMPTY_CV_TEXT')
        self.assertEqual(result['match_percentage'], 0.0)
        self.assertIn('Candidate resume text is empty', result['error_message'])

    def test_insufficient_text_error(self):
        result = calculate_resume_match(
            job_description="Loksewa Instructor needed for comprehensive courses.",
            required_skills="Loksewa, GK",
            resume_text="Hi there"  # only 2 words
        )
        self.assertEqual(result['status'], 'INSUFFICIENT_TEXT')
        self.assertEqual(result['match_percentage'], 0.0)
        self.assertIn('Insufficient resume text content', result['error_message'])

    def test_extraction_failure_detection(self):
        result = calculate_resume_match(
            job_description="Loksewa Instructor needed for comprehensive courses.",
            required_skills="Loksewa, GK",
            resume_text="[EXTRACTION_ERROR] Failed to read PDF streams."
        )
        self.assertEqual(result['status'], 'ERROR')
        self.assertEqual(result['error_type'], 'EXTRACTION_FAILURE')
        self.assertEqual(result['match_percentage'], 0.0)
        self.assertIn('extraction failed', result['error_message'])


class RequiredSkillMatchingTests(TestCase):
    """
    Unit tests for simple, explainable required-skill matching.
    """

    def test_exact_user_prompt_example(self):
        required = "Python, Django, HTML, CSS, MySQL, Git"
        resume = "Python, Django, HTML, CSS, MySQL"

        result = match_required_skills(required, resume)

        self.assertEqual(result['matched_skills'], ['Python', 'Django', 'HTML', 'CSS', 'MySQL'])
        self.assertEqual(result['missing_skills'], ['Git'])
        self.assertEqual(result['matched_count'], 5)
        self.assertEqual(result['missing_count'], 1)
        self.assertEqual(result['total_skills'], 6)

    def test_skill_normalization_and_punctuation(self):
        # Case differences, whitespace, and punctuation in resume
        required = "Python, Django, PostgreSQL"
        resume = "Hands-on experience with python,   DJANGO  and postgresql."

        result = match_required_skills(required, resume)

        self.assertEqual(result['matched_skills'], ['Python', 'Django', 'PostgreSQL'])
        self.assertEqual(result['missing_skills'], [])

    def test_word_boundary_prevents_false_partial_matches(self):
        # 'Git' should not match inside 'digital' or 'digit'
        required = "Git, Java"
        resume = "Worked in a digital agency building JavaScript web applications."

        result = match_required_skills(required, resume)

        # 'Git' should be missing because 'digital' is not 'git'
        self.assertIn('Git', result['missing_skills'])
        # 'Java' should be missing because 'JavaScript' is not 'java'
        self.assertIn('Java', result['missing_skills'])

    def test_multi_word_skill_matching(self):
        required = "Public Administration, Database Management, Git"
        resume = "Educator with strong background in public administration and database management."

        result = match_required_skills(required, resume)

        self.assertIn('Public Administration', result['matched_skills'])
        self.assertIn('Database Management', result['matched_skills'])
        self.assertIn('Git', result['missing_skills'])


class QualificationAndExperienceVerificationTests(TestCase):
    """
    Unit tests for conservative qualification and experience verification.
    Principle: If information cannot be reasonably detected, returns 'Needs Verification'
    rather than inventing a result.
    """

    def test_qualification_matched_equal_or_higher(self):
        job_qual = "Master's in Public Administration"
        resume_text = "Holds Master in Public Administration and Bachelor in Arts."

        res = evaluate_qualification(job_qual, resume_text)
        self.assertEqual(res['status'], 'Matched')

    def test_qualification_not_matched_when_lower(self):
        job_qual = "Master's in Mathematics"
        resume_text = "Completed Bachelor of Science in Mathematics."

        res = evaluate_qualification(job_qual, resume_text)
        self.assertEqual(res['status'], 'Not Matched')

    def test_qualification_needs_verification_when_unclear(self):
        job_qual = "Master's in Mathematics"
        resume_text = "Passionate educator who studied at Kathmandu Academy."

        res = evaluate_qualification(job_qual, resume_text)
        self.assertEqual(res['status'], 'Needs Verification')

    def test_experience_matched_meets_requirement(self):
        job_exp = "2+ Years teaching experience"
        resume_text = "I have 4 years experience teaching Loksewa General Knowledge."

        res = evaluate_experience(job_exp, resume_text)
        self.assertEqual(res['status'], 'Matched')

    def test_experience_not_matched_below_requirement(self):
        job_exp = "3+ Years teaching experience"
        resume_text = "I have 1 year experience as a student teacher."

        res = evaluate_experience(job_exp, resume_text)
        self.assertEqual(res['status'], 'Not Matched')

    def test_experience_fresher_eligible(self):
        job_exp = "Freshers eligible to apply"
        resume_text = "Recent graduate eager to begin teaching."

        res = evaluate_experience(job_exp, resume_text)
        self.assertEqual(res['status'], 'Matched')

    def test_experience_needs_verification_when_duration_unclear(self):
        job_exp = "2+ Years teaching experience"
        resume_text = "Experienced tutor with high student satisfaction ratings."

        res = evaluate_experience(job_exp, resume_text)
        self.assertEqual(res['status'], 'Needs Verification')


class ResumeScreeningModelIntegrationTests(TestCase):
    """
    Integration tests verifying database persistence of screening scores, skills, and admin decision support.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username='candidate_nlp',
            email='candidate@gurukul.edu.np',
            password='Password123!'
        )
        self.job = Job.objects.create(
            title="School Education Science Educator",
            department="School Education",
            description="Teach physics and chemistry to secondary school students preparing for SEE examinations.",
            required_skills="Physics, Chemistry, SEE Preparation, Pedagogy, Git",
            qualification="Bachelor's in Physics or Chemistry",
            experience="2+ years",
            deadline=timezone.now().date() + timedelta(days=15)
        )
        self.application = Application.objects.create(
            job=self.job,
            applicant=self.user
        )

    def test_screen_application_with_valid_text(self):
        ResumeExtraction.objects.create(
            application=self.application,
            extracted_text="B.Sc. Physics graduate with 3 years teaching physics and chemistry for SEE preparation. Experienced in modern pedagogy.",
            page_count=1,
            status=ResumeExtraction.STATUS_SUCCESS
        )

        screening = ResumeScreening.screen_application(self.application)
        self.assertIsNotNone(screening)
        self.assertEqual(screening.status, ResumeScreening.STATUS_SUCCESS)
        self.assertGreater(screening.match_percentage, 10.0)

        # Check matched and missing skills
        self.assertIn('Physics', screening.matched_skills)
        self.assertIn('Chemistry', screening.matched_skills)
        self.assertIn('Git', screening.missing_skills)

        # Check qualification and experience
        self.assertEqual(screening.qualification_match, 'Matched')
        self.assertEqual(screening.experience_match, 'Matched')

    def test_screen_application_handles_missing_cv_gracefully(self):
        # Application has no CV attached
        screening = ResumeScreening.screen_application(self.application)
        self.assertEqual(screening.status, ResumeScreening.STATUS_ERROR)
        self.assertEqual(screening.match_percentage, 0.0)
        self.assertEqual(screening.qualification_match, 'Needs Verification')
        self.assertEqual(screening.experience_match, 'Needs Verification')


class ResumeAnalysisFeatureTests(TestCase):
    """
    Tests for the complete Resume Analysis feature:
    ResumeAnalysis model, rule-based explanation generation, and admin analysis view.
    """

    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='admin_analyzer',
            email='admin@gurukul.edu.np',
            password='AdminPassword123!'
        )
        self.candidate = User.objects.create_user(
            username='candidate_ram',
            email='ram@gurukul.edu.np',
            password='CandidatePass123!'
        )
        self.job = Job.objects.create(
            title="Loksewa Computer Science Instructor",
            department="Loksewa Preparation",
            description="Teach programming and databases for computer engineering Loksewa exams.",
            required_skills="Python, Django, HTML, CSS, MySQL, Git",
            qualification="Bachelor's in Computer Engineering",
            experience="2+ years",
            deadline=timezone.now().date() + timedelta(days=20)
        )
        self.application = Application.objects.create(
            job=self.job,
            applicant=self.candidate
        )
        ResumeExtraction.objects.create(
            application=self.application,
            extracted_text="B.Sc Computer Engineering graduate with Python, Django, HTML, CSS, MySQL skills and 3 years experience teaching programming.",
            page_count=1,
            status=ResumeExtraction.STATUS_SUCCESS
        )

    def test_generate_explanation_exact_format(self):
        matched = ['Python', 'Django', 'HTML', 'MySQL']
        missing = ['Git']
        qual = 'Needs Verification'
        exp = 'Needs Verification'

        explanation = generate_explanation(matched, missing, qual, exp)

        self.assertIn("Python, Django, HTML and MySQL", explanation)
        self.assertIn("The skill Git was not identified in the uploaded resume.", explanation)
        self.assertIn("The qualification and experience information should be verified by the administrator.", explanation)

    def test_perform_analysis_stores_all_required_fields(self):
        from resume_ai.models import ResumeAnalysis

        analysis = ResumeAnalysis.perform_analysis(self.application)

        self.assertIsNotNone(analysis)
        self.assertEqual(analysis.application, self.application)
        self.assertGreater(analysis.match_percentage, 0.0)
        self.assertIn('Python', analysis.matched_skills)
        self.assertIn('Django', analysis.matched_skills)
        self.assertIn('Git', analysis.missing_skills)
        self.assertIn("Python", analysis.explanation)
        self.assertIsNotNone(analysis.analyzed_at)

    def test_admin_analysis_view_renders_correctly(self):
        self.client.force_login(self.admin)
        response = self.client.get(f'/resume-ai/analysis/{self.application.id}/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Resume Analysis Report")
        self.assertContains(response, "Candidate Information")
        self.assertContains(response, "Job Information")
        self.assertContains(response, "Overall Candidate Match")
        self.assertContains(response, "Matched Skills")
        self.assertContains(response, "Missing Skills")
        self.assertContains(response, "Shortlist")

    def test_admin_shortlist_action(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            f'/resume-ai/analysis/{self.application.id}/',
            {'action': 'shortlist'}
        )

        self.assertEqual(response.status_code, 302)
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, Application.STATUS_SHORTLISTED)

    def test_admin_update_status_action(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            f'/resume-ai/analysis/{self.application.id}/',
            {'action': 'update_status', 'status': Application.STATUS_UNDER_REVIEW}
        )

        self.assertEqual(response.status_code, 302)
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, Application.STATUS_UNDER_REVIEW)

    def test_non_admin_cannot_access_analysis_view(self):
        self.client.force_login(self.candidate)
        response = self.client.get(f'/resume-ai/analysis/{self.application.id}/')

        # Should redirect or reject non-admin
        self.assertNotEqual(response.status_code, 200)


class MLDatasetValidationTests(TestCase):
    """
    Unit tests verifying dataset schema validation, missing value filtering,
    binary label enforcement, and class distribution checks.
    """

    def test_valid_dataframe_validation(self):
        import pandas as pd
        from resume_ai.ml_model import validate_dataset

        df = pd.DataFrame({
            'resume_text': [f"Candidate resume content number {i} with distinct technical skills" for i in range(12)],
            'job_description': [f"Job description requirements specification {i}" for i in range(12)],
            'relevant': [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0]
        })

        clean_df, stats = validate_dataset(df)
        self.assertEqual(len(clean_df), 12)
        self.assertEqual(stats['valid_rows'], 12)
        self.assertEqual(stats['class_distribution']['relevant_1'], 6)
        self.assertEqual(stats['class_distribution']['non_relevant_0'], 6)

    def test_missing_columns_raises_error(self):
        import pandas as pd
        from resume_ai.ml_model import validate_dataset, DatasetValidationError

        df = pd.DataFrame({
            'wrong_column': ["data"],
            'relevant': [1]
        })

        with self.assertRaises(DatasetValidationError) as ctx:
            validate_dataset(df)
        self.assertIn("missing required columns", str(ctx.exception))

    def test_empty_dataset_raises_error(self):
        import pandas as pd
        from resume_ai.ml_model import validate_dataset, DatasetValidationError

        df = pd.DataFrame(columns=['resume_text', 'job_description', 'relevant'])
        with self.assertRaises(DatasetValidationError):
            validate_dataset(df)

    def test_non_binary_labels_raises_error(self):
        import pandas as pd
        from resume_ai.ml_model import validate_dataset, DatasetValidationError

        df = pd.DataFrame({
            'resume_text': [f"Candidate content {i} with extensive skills" for i in range(12)],
            'job_description': [f"Job description specification {i}" for i in range(12)],
            'relevant': [1, 2, 3, 0, 1, 0, 1, 0, 1, 0, 1, 0]  # Contains 2 and 3
        })

        with self.assertRaises(DatasetValidationError) as ctx:
            validate_dataset(df)
        self.assertIn("invalid labels", str(ctx.exception))

    def test_single_class_raises_error(self):
        import pandas as pd
        from resume_ai.ml_model import validate_dataset, DatasetValidationError

        df = pd.DataFrame({
            'resume_text': [f"Candidate content {i} with extensive skills" for i in range(12)],
            'job_description': [f"Job description specification {i}" for i in range(12)],
            'relevant': [1] * 12  # Only class 1
        })

        with self.assertRaises(DatasetValidationError) as ctx:
            validate_dataset(df)
        self.assertIn("must contain both positive", str(ctx.exception))


class MLModelTrainingAndInferenceTests(TestCase):
    """
    Tests ML pipeline training, evaluation against baseline, serialization,
    and inference services.
    """

    def setUp(self):
        import tempfile
        self.temp_dir = tempfile.mkdtemp()
        self.model_path = os.path.join(self.temp_dir, 'test_classifier.joblib')
        self.metadata_path = os.path.join(self.temp_dir, 'test_metadata.json')

    def tearDown(self):
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_training_and_evaluation_pipeline(self):
        import pandas as pd
        from resume_ai.ml_model import train_resume_model

        # Create balanced dataset fixture
        resumes = [
            "Senior Python Django developer with 5 years experience in building RESTful APIs PostgreSQL Celery Redis Docker and Git.",
            "Experienced frontend engineer specializing in React Next.js TypeScript Tailwind CSS Redux and modern web development.",
            "Secondary school Mathematics teacher with 7 years teaching Compulsory and Optional Mathematics for SEE students.",
            "Physics Lecturer coaching science students for board examinations and IOE engineering entrance tests.",
            "Executive pastry chef with 10 years experience in artisan bread baking chocolate sculpting and kitchen management.",
            "Commercial airline pilot with flight hours on Boeing aircraft instrument rating and aviation flight safety certification.",
            "Licensed real estate agent specializing in residential property appraisals commercial leasing and client negotiation.",
            "Automotive mechanic experienced in diesel engine repair brake overhauls vehicle diagnostics and transmission systems.",
            "Senior Python backend engineer with Django REST framework MySQL Linux server management and API integration.",
            "Secondary school Calculus teacher preparing students for board examinations and mathematics competitions.",
            "Professional landscaper and horticulturist skilled in lawn maintenance tree trimming and garden design.",
            "Fashion designer specializing in pattern cutting fabric selection apparel stitching and runway show planning."
        ]
        jobs = [
            "We are hiring a Senior Software Developer with expertise in Python Django REST APIs PostgreSQL and Git.",
            "Looking for a Frontend Developer with React TypeScript Next.js and component-driven UI architecture.",
            "We need a Secondary Mathematics Faculty for Classes 9 and 10 to teach Compulsory Math and Optional Math.",
            "Senior Physics Mentor for Science and Engineering entrance exam preparation.",
            "We are hiring a Senior Software Developer with expertise in Python Django REST APIs PostgreSQL and Git.",
            "We need a Secondary Mathematics Faculty for Classes 9 and 10 to teach Compulsory Math and Optional Math.",
            "Looking for a Frontend Developer with React TypeScript Next.js and component-driven UI architecture.",
            "Senior Physics Mentor for Science and Engineering entrance exam preparation.",
            "We are hiring a Senior Software Developer with expertise in Python Django REST APIs PostgreSQL and Git.",
            "We need a Secondary Mathematics Faculty for Classes 9 and 10 to teach Compulsory Math and Optional Math.",
            "We are hiring a Senior Software Developer with expertise in Python Django REST APIs PostgreSQL and Git.",
            "Senior Physics Mentor for Science and Engineering entrance exam preparation."
        ]
        labels = [1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 0, 0]

        df = pd.DataFrame({'resume_text': resumes, 'job_description': jobs, 'relevant': labels})

        report = train_resume_model(
            dataset_path_or_df=df,
            test_size=0.25,
            random_state=42,
            save_model=True,
            model_path=self.model_path,
            metadata_path=self.metadata_path
        )

        self.assertIn('ml_model_evaluation', report)
        self.assertIn('baseline_comparison', report)
        self.assertIn('performance_delta', report)
        self.assertTrue(os.path.exists(self.model_path))
        self.assertTrue(os.path.exists(self.metadata_path))

        ml_eval = report['ml_model_evaluation']
        self.assertGreaterEqual(ml_eval['accuracy'], 0.0)
        self.assertGreaterEqual(ml_eval['f1_score'], 0.0)
        self.assertEqual(len(ml_eval['confusion_matrix']), 2)

    def test_predict_relevance_with_trained_model(self):
        import pandas as pd
        from resume_ai.ml_model import train_resume_model, predict_relevance

        # Quick small training run
        df = pd.DataFrame({
            'resume_text': [
                "Python developer with Django and PostgreSQL experience",
                "Secondary school math teacher algebra geometry",
                "Pastry chef artisan bread baking",
                "Airline pilot Boeing flight operations",
            ] * 3,
            'job_description': [
                "Senior Python Developer Django PostgreSQL required",
                "Mathematics teacher for secondary school algebra",
                "Senior Python Developer Django PostgreSQL required",
                "Mathematics teacher for secondary school algebra",
            ] * 3,
            'relevant': [1, 1, 0, 0] * 3
        })

        train_resume_model(
            dataset_path_or_df=df,
            test_size=0.25,
            random_state=42,
            save_model=True,
            model_path=self.model_path,
            metadata_path=self.metadata_path
        )

        # Relevant prediction test
        pred = predict_relevance(
            resume_text="Senior Python developer with Django and database experience",
            job_description="Hiring Python Django developer",
            model_path=self.model_path,
            metadata_path=self.metadata_path
        )
        self.assertTrue(pred['is_available'])
        self.assertEqual(pred['status'], 'SUCCESS')
        self.assertIn(pred['predicted_class'], ['Relevant', 'Not Relevant'])
        self.assertIsNotNone(pred['relevance_probability'])
        self.assertTrue(pred['is_decision_support_only'])

    def test_predict_relevance_missing_model_graceful(self):
        from resume_ai.ml_model import predict_relevance

        pred = predict_relevance(
            resume_text="Some candidate resume",
            job_description="Some job description",
            model_path=os.path.join(self.temp_dir, 'non_existent.joblib'),
            metadata_path=os.path.join(self.temp_dir, 'non_existent.json')
        )
        self.assertFalse(pred['is_available'])
        self.assertEqual(pred['status'], 'NO_MODEL')
        self.assertEqual(pred['predicted_class'], 'Unavailable')
        self.assertIsNone(pred['relevance_probability'])

    def test_predict_relevance_empty_inputs_graceful(self):
        from resume_ai.ml_model import predict_relevance

        pred = predict_relevance("", "Some job description")
        self.assertFalse(pred['is_available'])
        self.assertEqual(pred['status'], 'INSUFFICIENT_TEXT')

        pred2 = predict_relevance("Some resume text", "")
        self.assertFalse(pred2['is_available'])
        self.assertEqual(pred2['status'], 'INSUFFICIENT_TEXT')


class ResumeScreeningMLIntegrationTests(TestCase):
    """
    Tests integration of ML inference into Django models:
    ResumeScreening and ResumeAnalysis.
    """

    def setUp(self):
        today = timezone.now().date()
        self.job = Job.objects.create(
            title="Senior Django Developer",
            department="Loksewa Preparation",
            description="Looking for an experienced Python and Django developer with PostgreSQL.",
            required_skills="Python, Django, PostgreSQL, Git",
            qualification="Bachelor's in Computer Science",
            experience="2+ Years",
            job_type="Full Time",
            location="Kathmandu",
            deadline=today + timedelta(days=20)
        )
        self.candidate = User.objects.create_user(
            username='mlcandidate',
            email='mlcandidate@example.com',
            password='secretpassword123'
        )
        self.application = Application.objects.create(
            job=self.job,
            applicant=self.candidate,
            status=Application.STATUS_APPLIED
        )
        self.extraction = ResumeExtraction.objects.create(
            application=self.application,
            extracted_text="Senior Python and Django developer with 4 years experience in building web apps with PostgreSQL.",
            page_count=1,
            status=ResumeExtraction.STATUS_SUCCESS
        )

    def test_screen_application_populates_ml_fields(self):
        screening = ResumeScreening.screen_application(self.application)
        self.assertIsNotNone(screening)
        self.assertEqual(screening.status, ResumeScreening.STATUS_SUCCESS)
        self.assertIn(screening.ml_prediction_status, ['SUCCESS', 'NO_MODEL', 'INSUFFICIENT_TEXT', 'ERROR'])
        self.assertIn(screening.ml_badge_class, ['gk-badge-success', 'gk-badge-danger', 'gk-badge-warning'])

    def test_perform_analysis_populates_ml_fields(self):
        analysis = ResumeAnalysis.perform_analysis(self.application)
        self.assertIsNotNone(analysis)
        self.assertIn(analysis.ml_prediction_status, ['SUCCESS', 'NO_MODEL', 'INSUFFICIENT_TEXT', 'ERROR'])
        self.assertIn(analysis.ml_badge_class, ['gk-badge-success', 'gk-badge-danger', 'gk-badge-warning'])


class TrainResumeModelManagementCommandTests(TestCase):
    """
    Tests execution of Django management command: train_resume_model.
    """

    def test_command_runs_successfully_on_bundled_dataset(self):
        from django.core.management import call_command
        from io import StringIO

        out = StringIO()
        call_command('train_resume_model', stdout=out)
        output = out.getvalue()

        self.assertIn("GURUKUL-CV", output)
        self.assertIn("Dataset Validated Successfully", output)
        self.assertIn("HELD-OUT TEST SET EVALUATION", output)
        self.assertIn("Accuracy", output)
        self.assertIn("F1-Score", output)
        self.assertIn("Confusion Matrix", output)


class BatchResumeScreeningTests(TestCase):
    """
    Comprehensive Unit & Integration Test Suite for Batch Resume Screening.
    Validates:
    1. Multi-candidate batch analysis for a specific job vacancy.
    2. Fault-isolation: A bad/corrupted/empty PDF never halts the batch.
    3. Calculation of highest, lowest, and average match metrics.
    4. Sorting and ranking candidates by AI match percentage descending.
    5. Skip logic in pending mode.
    6. Batch shortlisting of selected candidates.
    7. API endpoint for real-time progress.
    8. Backward compatibility: Existing single-CV analysis remains unbroken.
    """

    def setUp(self):
        from accounts.models import Profile
        today = timezone.now().date()
        self.job = Job.objects.create(
            title="Senior Python Web Developer",
            department="Loksewa IT Department",
            description="Developing web applications with Python, Django, REST API and PostgreSQL databases.",
            required_skills="Python, Django, PostgreSQL, REST API, Git",
            qualification="Bachelor's in Computer Science",
            experience="3+ Years",
            job_type="Full Time",
            location="Kathmandu",
            deadline=today + timedelta(days=30)
        )

        self.admin_user = User.objects.create_user(
            username='batchadmin',
            email='batchadmin@gurukul.edu.np',
            password='adminpassword123'
        )
        self.admin_user.profile.role = Profile.ROLE_ADMIN
        self.admin_user.profile.save()

        # Create 5 sample candidate applications with varying skill match profiles
        self.candidates = []
        self.applications = []

        candidate_data = [
            ("candidate_perfect", "Expert Python Django developer with 5 years experience building scalable REST API backends with PostgreSQL and Git."),
            ("candidate_high", "Python developer with Django and PostgreSQL knowledge. Experienced with Git version control."),
            ("candidate_mid", "Web developer skilled in Python and SQL databases with 2 years experience."),
            ("candidate_low", "HTML, CSS and JavaScript front-end designer with basic Python exposure."),
            ("candidate_corrupted", ""),  # Corrupted/empty CV to test fault isolation
        ]

        for i, (uname, text) in enumerate(candidate_data):
            cand = User.objects.create_user(
                username=uname,
                email=f"{uname}@example.com",
                password="password123"
            )
            app = Application.objects.create(
                job=self.job,
                applicant=cand,
                status=Application.STATUS_APPLIED
            )
            # Create extraction record
            if text:
                ResumeExtraction.objects.create(
                    application=app,
                    extracted_text=text,
                    page_count=1,
                    status=ResumeExtraction.STATUS_SUCCESS
                )
            else:
                ResumeExtraction.objects.create(
                    application=app,
                    extracted_text="",
                    page_count=1,
                    status=ResumeExtraction.STATUS_EMPTY,
                    error_message="Uploaded CV has no readable text."
                )

            self.candidates.append(cand)
            self.applications.append(app)

    def test_batch_process_job_applications_analyzes_all(self):
        """Verify that batch processing analyzes all 5 applications without crashing on the empty CV."""
        from resume_ai.batch_service import BatchResumeScreeningService

        summary = BatchResumeScreeningService.batch_process_job_applications(self.job.id, mode='all')

        self.assertTrue(summary['success'])
        self.assertEqual(summary['total_applicants'], 5)
        self.assertEqual(summary['processed_count'], 5)
        # 4 should succeed, 1 should fail
        self.assertEqual(summary['success_count'], 4)
        self.assertEqual(summary['failed_count'], 1)

        # Statistical metrics should be populated
        self.assertGreater(summary['highest_match'], 0.0)
        self.assertGreater(summary['average_match'], 0.0)
        self.assertGreaterEqual(summary['lowest_match'], 0.0)
        self.assertGreaterEqual(summary['highest_match'], summary['lowest_match'])

        # Check that ResumeAnalysis records were saved in DB
        analyses = ResumeAnalysis.objects.filter(application__job=self.job)
        self.assertEqual(analyses.count(), 5)

        # Verify fault isolation: candidate_corrupted has STATUS_FAILED and error message
        corrupted_analysis = ResumeAnalysis.objects.get(application__applicant__username='candidate_corrupted')
        self.assertEqual(corrupted_analysis.analysis_status, ResumeAnalysis.STATUS_FAILED)
        self.assertIn("no readable text", corrupted_analysis.error_message.lower())

        # Verify candidate_perfect has high match and matched skills
        perfect_analysis = ResumeAnalysis.objects.get(application__applicant__username='candidate_perfect')
        self.assertEqual(perfect_analysis.analysis_status, ResumeAnalysis.STATUS_COMPLETED)
        self.assertGreater(perfect_analysis.match_percentage, 40.0)
        self.assertIn('Python', perfect_analysis.matched_skills)
        self.assertIn('Django', perfect_analysis.matched_skills)

    def test_batch_pending_mode_skips_completed(self):
        """Verify that mode='pending' does not re-analyze already completed applications."""
        from resume_ai.batch_service import BatchResumeScreeningService

        # Run first batch
        summary1 = BatchResumeScreeningService.batch_process_job_applications(self.job.id, mode='all')
        self.assertEqual(summary1['success_count'], 4)

        # Run second batch in pending mode
        summary2 = BatchResumeScreeningService.batch_process_job_applications(self.job.id, mode='pending')
        # All 4 completed should have been skipped, only the 1 failed was re-checked
        self.assertTrue(summary2['success'])
        skipped_results = [r for r in summary2['results'] if r.get('skipped') is True]
        self.assertEqual(len(skipped_results), 4)

    def test_batch_shortlist_candidates_action(self):
        """Verify that batch shortlist updates only the selected candidates."""
        from django.test import Client
        from django.urls import reverse

        client = Client()
        client.force_login(self.admin_user)

        target_ids = [self.applications[0].id, self.applications[1].id]
        response = client.post(
            reverse('resume_ai:batch_shortlist_candidates', args=[self.job.id]),
            {'selected_applications': target_ids}
        )

        self.assertEqual(response.status_code, 302)

        # Refresh from DB
        self.applications[0].refresh_from_db()
        self.applications[1].refresh_from_db()
        self.applications[2].refresh_from_db()

        self.assertEqual(self.applications[0].status, Application.STATUS_SHORTLISTED)
        self.assertEqual(self.applications[1].status, Application.STATUS_SHORTLISTED)
        self.assertEqual(self.applications[2].status, Application.STATUS_APPLIED)

    def test_api_batch_analyze_item_endpoint(self):
        """Verify JSON API endpoint for frontend real-time progress modal."""
        from django.test import Client
        from django.urls import reverse

        client = Client()
        client.force_login(self.admin_user)

        target_app = self.applications[0]
        url = reverse('resume_ai:api_batch_analyze_item', args=[target_app.id])
        response = client.post(url, {'force': 'true'})

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['application_id'], target_app.id)
        self.assertIn('match_percentage', data)
        self.assertIn('matched_skills', data)

    def test_single_cv_analysis_view_remains_unbroken(self):
        """Verify existing single-CV analysis view (/resume-ai/analyze/<id>/) still renders completely."""
        from django.test import Client
        from django.urls import reverse

        client = Client()
        client.force_login(self.admin_user)

        target_app = self.applications[0]
        url = reverse('resume_ai:analyze_resume', args=[target_app.id])
        response = client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Senior Python Web Developer")
        self.assertContains(response, target_app.applicant.username)
        self.assertContains(response, "Overall Candidate Match")



