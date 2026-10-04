from django.urls import path
from . import views

app_name = 'resume_ai'

urlpatterns = [
    path('analysis/<int:application_id>/', views.analyze_resume, name='analyze_resume'),
    path('extract/<int:application_id>/', views.view_extracted_text, name='view_extracted_text'),
    path('batch-analyze/<int:job_id>/', views.batch_analyze_job, name='batch_analyze_job'),
    path('api/batch-analyze-item/<int:application_id>/', views.api_batch_analyze_item, name='api_batch_analyze_item'),
    path('batch-shortlist/<int:job_id>/', views.batch_shortlist_candidates, name='batch_shortlist_candidates'),
]

