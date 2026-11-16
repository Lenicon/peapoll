from django.db.models import Count
from django.shortcuts import render

from polls.models import Poll


def home_view(request):
    """
    Public Home screen: landing banner plus the latest polls.
    Anyone can see it; logging in is only needed to create polls.
    """
    latest = (
        Poll.objects.select_related('owner')
        .annotate(vote_count=Count('votes'))
        .order_by('-created_at')[:5]
    )
    return render(request, 'home/home.html', {'latest_polls': latest})
