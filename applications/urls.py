from django.urls import path
from . import views

app_name = 'applications'

urlpatterns = [
    path('my-applications/', views.my_applications, name='my_applications'),
    path('apply/<int:job_id>/', views.apply_job, name='apply_job'),
    path('<int:pk>/', views.view_application, name='view_application'),
    path('admin/applicants/', views.admin_applicants, name='admin_applicants'),
    path('job/<int:job_id>/applicants/', views.job_applicants, name='job_applicants'),
    path('<int:pk>/status/', views.update_status, name='update_status'),
    path('<int:pk>/shortlist/', views.quick_shortlist, name='quick_shortlist'),
]

