from django.urls import path
from . import views

app_name = 'jobs'

urlpatterns = [
    path('<int:pk>/', views.job_detail, name='job_detail'),
    path('manage/', views.manage_jobs, name='manage_jobs'),
    path('create/', views.create_job, name='create_job'),
    path('<int:pk>/edit/', views.edit_job, name='edit_job'),
    path('<int:pk>/delete/', views.delete_job, name='delete_job'),
]
