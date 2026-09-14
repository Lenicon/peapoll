from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import LoginForm, ProfileUpdateForm, RegisterForm, StyledPasswordChangeForm


def login_view(request):
    """
    Handles the Login screen.
    GET  -> displays the login form.
    POST -> validates credentials and logs the user in.
    """
    # If the user is already logged in, send them straight to Home.
    if request.user.is_authenticated:
        return redirect('home:home')

    form = LoginForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        username = form.cleaned_data['username']
        password = form.cleaned_data['password']
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('home:home')
        else:
            messages.error(request, 'Invalid username or password. Please try again.')

    return render(request, 'accounts/login.html', {'form': form})


def register_view(request):
    """
    Handles the Register screen.
    GET  -> displays the registration form.
    POST -> creates a new user account, then redirects to Login.
    """
    if request.user.is_authenticated:
        return redirect('home:home')

    form = RegisterForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Account created successfully! You may now log in.')
        return redirect('accounts:login')

    return render(request, 'accounts/register.html', {'form': form})


@login_required
def logout_view(request):
    """
    Logs the current user out and returns them to the Login screen.
    """
    logout(request)
    return redirect('accounts:login')


@login_required
def profile_view(request):
    """
    Read-only Profile screen: shows the logged-in user's username
    and email. Editing happens on the Settings screen.
    """
    return render(request, 'accounts/profile.html')


@login_required
def settings_view(request):
    """
    Settings screen. Handles two independent forms on one page:
      - profile_form: change username / email
      - password_form: change password (via Django's PasswordChangeForm)
    Each form has its own submit button, distinguished by the
    'update_profile' / 'change_password' name in POST data.
    """
    profile_form = ProfileUpdateForm(instance=request.user)
    password_form = StyledPasswordChangeForm(user=request.user)

    if request.method == 'POST':
        if 'update_profile' in request.POST:
            profile_form = ProfileUpdateForm(request.POST, instance=request.user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, 'Your profile was updated successfully.')
                return redirect('accounts:settings')

        elif 'change_password' in request.POST:
            password_form = StyledPasswordChangeForm(user=request.user, data=request.POST)
            if password_form.is_valid():
                user = password_form.save()
                # Keep the user logged in after their password hash changes.
                update_session_auth_hash(request, user)
                messages.success(request, 'Your password was changed successfully.')
                return redirect('accounts:settings')

    return render(request, 'accounts/settings.html', {
        'profile_form': profile_form,
        'password_form': password_form,
    })