from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def home_view(request):
    """
    Handles the Home screen.
    Only accessible to logged-in users (redirects to Login otherwise,
    handled automatically by the @login_required decorator).
    """
    return render(request, 'home/home.html')
