from django.contrib import admin
from .models import Application

@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('applicant', 'job', 'status', 'applied_at', 'cv')
    list_filter = ('status', 'applied_at', 'job__department')
    search_fields = ('applicant__username', 'applicant__email', 'applicant__first_name', 'applicant__last_name', 'job__title')
    readonly_fields = ('applied_at',)
