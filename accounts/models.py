from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class Profile(models.Model):
    """
    Profile extension for Django User model.
    Differentiates between JOB SEEKER and ADMIN roles.
    Public registration always creates JOB SEEKER profiles.
    """
    ROLE_JOB_SEEKER = 'job_seeker'
    ROLE_ADMIN = 'admin'
    ROLE_CHOICES = [
        (ROLE_JOB_SEEKER, 'Job Seeker'),
        (ROLE_ADMIN, 'Admin'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_JOB_SEEKER)
    phone = models.CharField(max_length=20, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"

    @property
    def is_admin(self):
        return self.role == self.ROLE_ADMIN or self.user.is_staff or self.user.is_superuser

    @property
    def is_job_seeker(self):
        return self.role == self.ROLE_JOB_SEEKER and not (self.user.is_staff or self.user.is_superuser)


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """
    Ensure every User has an associated Profile.
    Superusers and staff are automatically designated ADMIN.
    All other created users default to JOB SEEKER.
    """
    if created:
        role = Profile.ROLE_ADMIN if (instance.is_staff or instance.is_superuser) else Profile.ROLE_JOB_SEEKER
        Profile.objects.create(user=instance, role=role)
    else:
        if hasattr(instance, 'profile'):
            if (instance.is_staff or instance.is_superuser) and instance.profile.role != Profile.ROLE_ADMIN:
                instance.profile.role = Profile.ROLE_ADMIN
            instance.profile.save()
        else:
            role = Profile.ROLE_ADMIN if (instance.is_staff or instance.is_superuser) else Profile.ROLE_JOB_SEEKER
            Profile.objects.create(user=instance, role=role)
