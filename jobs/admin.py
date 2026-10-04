from django.contrib import admin
from .models import Job

@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ('title', 'department', 'job_type', 'location', 'deadline', 'status_badge', 'created_at')
    list_filter = ('department', 'job_type', 'deadline')
    search_fields = ('title', 'department', 'description', 'required_skills', 'qualification')
    date_hierarchy = 'deadline'

    def status_badge(self, obj):
        return obj.status
    status_badge.short_description = 'Status'
