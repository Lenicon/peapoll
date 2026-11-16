from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, render

from .models import Poll


def poll_list(request):
    """Public list of all polls, with search and sorting. No login needed."""
    query = request.GET.get('q', '').strip()
    sort = request.GET.get('sort', 'new')

    polls = Poll.objects.select_related('owner').annotate(vote_count=Count('votes'))
    if query:
        polls = polls.filter(
            Q(question__icontains=query) | Q(description__icontains=query)
        )
    if sort == 'popular':
        polls = polls.order_by('-vote_count', '-created_at')
    else:
        sort = 'new'
        polls = polls.order_by('-created_at')

    page = Paginator(polls, 10).get_page(request.GET.get('page'))
    return render(request, 'polls/poll_list.html', {
        'page': page,
        'query': query,
        'sort': sort,
    })


def poll_detail(request, pk):
    """Public poll page."""
    poll = get_object_or_404(Poll.objects.select_related('owner'), pk=pk)
    return render(request, 'polls/poll_detail.html', {
        'poll': poll,
        'choices': poll.choices.all(),
    })
