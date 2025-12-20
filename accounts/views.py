from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.csrf import csrf_protect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.views import PasswordResetView, PasswordResetDoneView, PasswordResetConfirmView, PasswordResetCompleteView
from django.urls import reverse_lazy
from django.utils import timezone
from datetime import timedelta
from .models import Company
from .forms import (
    DreamBizUserCreationForm, DreamBizPasswordResetForm, DreamBizSetPasswordForm, 
    UserProfileForm, UserProfileDetailForm, UserPreferencesForm, 
    PasswordChangeForm, NotificationPreferencesForm
)
from common.email_utils import send_welcome_email
import logging

logger = logging.getLogger(__name__)


@csrf_protect
def login_view(request):
    """
    Modern login view with enhanced UX
    Better than QuickBooks' basic auth
    """
    if request.user.is_authenticated:
        return redirect('dashboard:home')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.get_full_name()}!')
            return redirect(request.GET.get('next', 'dashboard:home'))
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'accounts/login.html')


@csrf_protect
def register_view(request):
    """
    User registration with company setup
    Enhanced beyond QuickBooks' basic registration
    """
    if request.user.is_authenticated:
        return redirect('dashboard:home')
    
    if request.method == 'POST':
        form = DreamBizUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            
            messages.success(request, f'Welcome to DreamBiz, {user.get_full_name()}! Your account is ready.')
            
            # Send welcome email
            try:
                send_welcome_email(user, request)
                logger.info(f"Welcome email sent to {user.email}")
            except Exception as e:
                logger.error(f"Failed to send welcome email to {user.email}: {str(e)}")
            
            return redirect('dashboard:home')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = DreamBizUserCreationForm()
    
    return render(request, 'accounts/register.html', {'form': form})


@login_required
def logout_view(request):
    """
    Logout view with confirmation
    """
    logout(request)
    messages.info(request, 'You have been successfully logged out.')
    return redirect('accounts:login')


@login_required
def profile_view(request):
    """
    User profile management
    Enhanced compared to QuickBooks' limited profile options
    """
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('accounts:profile')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = UserProfileForm(instance=request.user)
    
    return render(request, 'accounts/profile.html', {'form': form})


@login_required
@require_http_methods(["GET"])
def user_companies(request):
    """
    API endpoint to get user's companies
    """
    companies = Company.objects.filter(usercompany__user=request.user)
    data = [{
        'id': company.id,
        'name': company.name,
        'role': company.usercompany_set.get(user=request.user).role
    } for company in companies]
    
    return JsonResponse({'companies': data})


# Password Reset Views
class DreamBizPasswordResetView(PasswordResetView):
    """
    Custom password reset view with enhanced error handling and HTML email support
    """
    template_name = 'accounts/password_reset.html'
    form_class = DreamBizPasswordResetForm
    success_url = reverse_lazy('accounts:password_reset_done')
    email_template_name = 'accounts/password_reset_email.txt'  # Plain text version
    subject_template_name = 'accounts/password_reset_subject.txt'
    html_email_template_name = 'accounts/password_reset_email.html'  # HTML version

    def form_valid(self, form):
        import logging
        logger = logging.getLogger(__name__)

        try:
            # Call the parent form_valid which sends the email
            response = super().form_valid(form)
            messages.success(self.request, 'Password reset email has been sent to your email address.')
            logger.info(f"Password reset email sent successfully to {form.cleaned_data.get('email')}")
            return response
        except Exception as e:
            logger.error(f"Failed to send password reset email: {str(e)}")
            messages.error(
                self.request,
                'There was an error sending the password reset email. Please contact support or try again later.'
            )
            return self.form_invalid(form)


class DreamBizPasswordResetDoneView(PasswordResetDoneView):
    """
    Password reset done view
    """
    template_name = 'accounts/password_reset_done.html'


class DreamBizPasswordResetConfirmView(PasswordResetConfirmView):
    """
    Password reset confirm view
    """
    template_name = 'accounts/password_reset_confirm.html'
    form_class = DreamBizSetPasswordForm
    success_url = reverse_lazy('accounts:password_reset_complete')

    def form_valid(self, form):
        messages.success(self.request, 'Your password has been reset successfully!')
        return super().form_valid(form)


class DreamBizPasswordResetCompleteView(PasswordResetCompleteView):
    """
    Password reset complete view
    """
    template_name = 'accounts/password_reset_complete.html'


# User Profile Management Views
@login_required
def profile_view(request):
    """
    User profile overview
    """
    context = {
        'user': request.user,
        'notification_prefs': request.user.notification_preferences or {},
    }
    return render(request, 'accounts/profile.html', context)


@login_required
def profile_edit(request):
    """
    Edit user profile information
    """
    if request.method == 'POST':
        form = UserProfileDetailForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated successfully!')
            return redirect('accounts:profile')
    else:
        form = UserProfileDetailForm(instance=request.user)
    
    context = {
        'form': form,
    }
    return render(request, 'accounts/profile_edit.html', context)


@login_required
def change_password(request):
    """
    Change user password
    """
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            update_session_auth_hash(request, request.user)  # Keep user logged in
            messages.success(request, 'Your password has been changed successfully!')
            return redirect('accounts:profile')
    else:
        form = PasswordChangeForm(request.user)
    
    context = {
        'form': form,
    }
    return render(request, 'accounts/change_password.html', context)


@login_required
def notification_preferences(request):
    """
    Manage notification preferences
    """
    if request.method == 'POST':
        form = NotificationPreferencesForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your notification preferences have been updated!')
            return redirect('accounts:profile')
    else:
        form = NotificationPreferencesForm(request.user)
    
    context = {
        'form': form,
    }
    return render(request, 'accounts/notification_preferences.html', context)


@login_required
def user_preferences(request):
    """
    Manage user preferences
    """
    if request.method == 'POST':
        form = UserPreferencesForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your preferences have been updated!')
            return redirect('accounts:profile')
    else:
        form = UserPreferencesForm(instance=request.user)
    
    context = {
        'form': form,
    }
    return render(request, 'accounts/user_preferences.html', context)


@login_required
def delete_avatar(request):
    """
    Delete user avatar
    """
    if request.method == 'POST':
        if request.user.avatar:
            request.user.avatar.delete()
            request.user.save()
            messages.success(request, 'Your avatar has been deleted.')
        return redirect('accounts:profile_edit')
    return redirect('accounts:profile')


@login_required
@require_http_methods(["GET"])
def profile_activity(request):
    """
    View user activity log
    """
    # This would integrate with an activity logging system
    context = {
        'activities': [],  # Placeholder for activity log
    }
    return render(request, 'accounts/profile_activity.html', context)

