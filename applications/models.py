from django.db import models
from django.contrib.auth.models import User
from jobs.models import Job

class Application(models.Model):
    """
    Candidate job application model.
    Stores the link between an applicant, the target vacancy, their PDF CV, and application status.
    Duplicate submissions by the same applicant for the same job are strictly prevented.
    """
    STATUS_APPLIED = 'Applied'
    STATUS_UNDER_REVIEW = 'Under Review'
    STATUS_SHORTLISTED = 'Shortlisted'
    STATUS_REJECTED = 'Rejected'

    STATUS_CHOICES = [
        (STATUS_APPLIED, 'Applied'),
        (STATUS_UNDER_REVIEW, 'Under Review'),
        (STATUS_SHORTLISTED, 'Shortlisted'),
        (STATUS_REJECTED, 'Rejected'),
    ]

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='applications')
    applicant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='applications')
    cv = models.FileField(upload_to='resumes/%Y/%m/', help_text="Candidate CV/Resume in PDF format.")
    applied_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default=STATUS_APPLIED)

    class Meta:
        ordering = ['-applied_at']
        constraints = [
            models.UniqueConstraint(fields=['job', 'applicant'], name='unique_job_applicant_application')
        ]

    def __str__(self):
        return f"{self.applicant.username} - {self.job.title} ({self.status})"

    @property
    def status_badge_class(self):
        """Returns the design system badge class for this status."""
        mapping = {
            self.STATUS_APPLIED: 'gk-badge-primary',
            self.STATUS_UNDER_REVIEW: 'gk-badge-warning',
            self.STATUS_SHORTLISTED: 'gk-badge-success',
            self.STATUS_REJECTED: 'gk-badge-danger',
        }
        return mapping.get(self.status, 'gk-badge-neutral')
