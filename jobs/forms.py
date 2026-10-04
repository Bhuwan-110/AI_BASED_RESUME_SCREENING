from django import forms
from .models import Job

class JobForm(forms.ModelForm):
    """
    Form for creating and editing Job vacancies.
    Features clear grouping, accessible labels, date picker, and validation.
    """
    class Meta:
        model = Job
        fields = [
            'title',
            'department',
            'job_type',
            'location',
            'qualification',
            'experience',
            'deadline',
            'required_skills',
            'description',
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Loksewa General Knowledge Lead Instructor',
                'id': 'jobTitle'
            }),
            'department': forms.Select(attrs={
                'class': 'form-select',
                'id': 'jobDepartment'
            }),
            'job_type': forms.Select(attrs={
                'class': 'form-select',
                'id': 'jobType'
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Kathmandu (Putalisadak) / Hybrid / Online',
                'id': 'jobLocation'
            }),
            'qualification': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Master’s degree in Public Administration, Political Science or related discipline',
                'id': 'jobQualification'
            }),
            'experience': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. 2+ Years classroom teaching or Loksewa coaching experience',
                'id': 'jobExperience'
            }),
            'deadline': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'id': 'jobDeadline'
            }),
            'required_skills': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'e.g. Loksewa Syllabus, Current Affairs Research, Presentation, Nepali & English Fluency (comma-separated)',
                'id': 'jobSkills'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Describe duties, lecture expectations, student mentoring responsibilities, and curriculum objectives...',
                'id': 'jobDescription'
            }),
        }
        labels = {
            'title': 'Job Title',
            'department': 'Department / Program',
            'job_type': 'Job Type',
            'location': 'Work Location',
            'qualification': 'Minimum Qualification',
            'experience': 'Required Experience',
            'deadline': 'Application Deadline',
            'required_skills': 'Required Skills & Competencies',
            'description': 'Job Description & Responsibilities',
        }
        help_texts = {
            'required_skills': 'Separate skills with commas (e.g. Mathematics, Lesson Planning, SEE Syllabus). These are indexed by the AI matching engine.',
            'deadline': 'After this date, the job automatically transitions to EXPIRED status.',
        }
