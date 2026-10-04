from django.db import models
from django.utils import timezone

class Job(models.Model):
    """
    Job model representing academic, mentorship, and administrative vacancies.
    Active/Expired status is dynamically evaluated against the application deadline.
    """
    DEPARTMENT_CHOICES = [
        ('Loksewa Preparation', 'Loksewa Preparation'),
        ('School Education', 'School Education (SEE)'),
        ('College Education', 'College Education (+2)'),
        ('Academic Mentorship', 'Academic Mentorship'),
        ('Curriculum & Content', 'Curriculum & Content Development'),
    ]

    JOB_TYPE_CHOICES = [
        ('Full Time', 'Full Time'),
        ('Part Time', 'Part Time'),
        ('Contract', 'Contract'),
        ('Hybrid / Remote', 'Hybrid / Remote'),
    ]

    title = models.CharField(max_length=200, help_text="e.g. Loksewa General Knowledge Lead Instructor")
    department = models.CharField(max_length=100, choices=DEPARTMENT_CHOICES, default='Loksewa Preparation')
    description = models.TextField(help_text="Detailed overview of responsibilities and expectations.")
    required_skills = models.TextField(help_text="Key skills and competencies (comma-separated or listed).")
    qualification = models.CharField(max_length=200, help_text="e.g. Master's in Public Administration, Bachelor's in Mathematics")
    experience = models.CharField(max_length=100, help_text="e.g. 2+ Years teaching experience, Freshers eligible")
    job_type = models.CharField(max_length=50, choices=JOB_TYPE_CHOICES, default='Full Time')
    location = models.CharField(max_length=150, default='Kathmandu / Online', help_text="e.g. Kathmandu (Putalisadak), Online, Hybrid")
    deadline = models.DateField(help_text="Last date for candidate submissions.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['deadline', '-created_at']

    def __str__(self):
        return f"{self.title} ({self.department})"

    @property
    def is_expired(self):
        """Returns True if application deadline has strictly passed."""
        return self.deadline < timezone.now().date()

    @property
    def is_active(self):
        """Returns True if deadline has not passed."""
        return not self.is_expired

    @property
    def status(self):
        return 'EXPIRED' if self.is_expired else 'ACTIVE'

    @property
    def skills_list(self):
        """Returns list of skills parsed by commas or newlines for template display."""
        if not self.required_skills:
            return []
        # Support either comma or newline separation
        raw = self.required_skills.replace('\n', ',')
        return [s.strip() for s in raw.split(',') if s.strip()]

    @property
    def applicant_count(self):
        """Returns the number of candidate applications submitted for this job."""
        if hasattr(self, 'applications'):
            return self.applications.count()
        return 0
