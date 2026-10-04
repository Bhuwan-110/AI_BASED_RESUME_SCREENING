import os
from django import forms
from django.core.exceptions import ValidationError
from .models import Application

MAX_CV_SIZE_MB = 5
MAX_CV_SIZE_BYTES = MAX_CV_SIZE_MB * 1024 * 1024

class JobApplicationForm(forms.ModelForm):
    """
    Candidate application form.
    Validates PDF format and 5MB file size limit.
    """
    cv = forms.FileField(
        required=True,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.pdf,application/pdf',
            'id': 'applicantCV'
        }),
        label='Curriculum Vitae / Resume (PDF)',
        help_text=f'Upload your resume in PDF format only. Maximum file size: {MAX_CV_SIZE_MB}MB.'
    )

    class Meta:
        model = Application
        fields = ['cv']

    def clean_cv(self):
        cv = self.cleaned_data.get('cv')
        if not cv:
            raise ValidationError('A valid resume file is required.')

        # 1. Validate file extension
        ext = os.path.splitext(cv.name)[1].lower()
        if ext != '.pdf':
            raise ValidationError('Invalid file format. Please upload your resume strictly as a PDF (.pdf) file.')

        # 2. Validate file size
        if cv.size > MAX_CV_SIZE_BYTES:
            size_in_mb = round(cv.size / (1024 * 1024), 2)
            raise ValidationError(
                f'The uploaded file size ({size_in_mb}MB) exceeds the maximum allowed limit of {MAX_CV_SIZE_MB}MB.'
            )

        return cv


class ApplicationStatusUpdateForm(forms.ModelForm):
    """
    Administrator form to update application evaluation status.
    """
    status = forms.ChoiceField(
        choices=Application.STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select form-select-sm', 'id': 'statusSelect'})
    )

    class Meta:
        model = Application
        fields = ['status']
