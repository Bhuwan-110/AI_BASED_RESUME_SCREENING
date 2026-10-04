from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages

def admin_required(view_func):
    """
    Decorator requiring the logged-in user to hold the ADMIN role or staff privileges.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.info(request, 'Please log in to access the Administrator Portal.')
            return redirect('accounts:login')
        
        is_admin = (
            request.user.is_staff or 
            request.user.is_superuser or 
            (hasattr(request.user, 'profile') and request.user.profile.role == 'admin')
        )
        if not is_admin:
            messages.error(request, 'Access denied. Administrator privileges are required to view that area.')
            return redirect('accounts:dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def job_seeker_required(view_func):
    """
    Decorator requiring user to be authenticated.
    Redirects admins to the Admin Dashboard if they navigate here.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.info(request, 'Please log in to access your Job Seeker Dashboard.')
            return redirect('accounts:login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view
