from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .models import Profile

class JobSeekerRegistrationForm(forms.Form):
    """
    Public registration form for Job Seekers.
    New public users strictly become JOB SEEKER users.
    """
    full_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. Bibek Shrestha',
            'autocomplete': 'name',
            'id': 'regFullName'
        }),
        label='Full Name'
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'name@example.com',
            'autocomplete': 'email',
            'id': 'regEmail'
        }),
        label='Email Address'
    )
    username = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Choose a unique username',
            'autocomplete': 'username',
            'id': 'regUsername'
        }),
        label='Username'
    )
    password = forms.CharField(
        required=True,
        min_length=8,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Minimum 8 characters',
            'autocomplete': 'new-password',
            'id': 'regPassword'
        }),
        label='Password',
        help_text='Must be at least 8 characters long.'
    )
    confirm_password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Re-enter your password',
            'autocomplete': 'new-password',
            'id': 'regConfirmPassword'
        }),
        label='Confirm Password'
    )

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError('This username is already taken. Please choose another.')
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError('An account with this email address already exists.')
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', 'Passwords do not match. Please verify both entries.')
        return cleaned_data

    def save(self):
        data = self.cleaned_data
        full_name = data['full_name'].strip()
        name_parts = full_name.split(' ', 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ''

        # Use standard Django user creation with hashing
        user = User.objects.create_user(
            username=data['username'],
            email=data['email'],
            password=data['password'],
            first_name=first_name,
            last_name=last_name
        )
        # Ensure role is explicitly Job Seeker
        if hasattr(user, 'profile'):
            user.profile.role = Profile.ROLE_JOB_SEEKER
            user.profile.save()
        return user


class LoginForm(forms.Form):
    """
    Standard authentication form supporting login via username or email.
    """
    username_or_email = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your username or email',
            'autocomplete': 'username',
            'id': 'loginIdentifier'
        }),
        label='Username or Email'
    )
    password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your password',
            'autocomplete': 'current-password',
            'id': 'loginPassword'
        }),
        label='Password'
    )


class ProfileUpdateForm(forms.ModelForm):
    """
    Form allowing users to update their personal information and phone.
    """
    phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. +977-98XXXXXXXX',
            'id': 'profilePhone'
        }),
        label='Phone Number'
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'id': 'profileFirstName'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'id': 'profileLastName'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'id': 'profileEmail'}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise ValidationError('This email address is already in use by another account.')
        return email
