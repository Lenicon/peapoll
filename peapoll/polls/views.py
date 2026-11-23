from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Count, Q, Subquery
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import PollForm
from .models import Choice, Poll, Vote


import re


def _format_sql(sql: str) -> str:
    """Break major SQL clauses onto separate lines for easier console reading."""
    formatted = re.sub(
        r'\s+(SELECT|FROM|INNER JOIN|LEFT OUTER JOIN|WHERE|AND|OR|GROUP BY|ORDER BY|LIMIT)\s+',
        r'\n\1 ',
        sql.strip(),
        flags=re.IGNORECASE,
    )
    return formatted


def _log_sql(label: str, queryset) -> None:
    sql_str = str(queryset.query)
    print(f"\n========== {label} ==========")
    print(_format_sql(sql_str))
    print("=" * (len(label) + 22) + "\n")



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

    _log_sql("poll_list JOIN SQL", polls)

    page = Paginator(polls, 10).get_page(request.GET.get('page'))
    return render(request, 'polls/poll_list.html', {
        'page': page,
        'query': query,
        'sort': sort,
    })


def _voter_filter(request):
    """Return the Vote filter that identifies the current visitor."""
    if request.user.is_authenticated:
        return {'user': request.user}
    if not request.session.session_key:
        return None
    return {'user': None, 'session_key': request.session.session_key}


def _has_voted(request, poll):
    voter = _voter_filter(request)
    return bool(voter) and poll.votes.filter(**voter).exists()


def poll_detail(request, pk):
    """
    Public poll page. Shows the voting form to people who can still vote,
    and the live results to everyone else (already voted, closed, or ?results=1).
    """
    poll = get_object_or_404(Poll.objects.select_related('owner'), pk=pk)
    voter = _voter_filter(request)
    user_vote = (
        poll.votes.filter(**voter).select_related('choice').first()
        if voter else None
    )
    has_voted = _has_voted(request, poll)
    show_results = has_voted or not poll.is_open or request.GET.get('results') == '1'

    results = []
    if show_results:
        total = poll.votes.count()
        choices = poll.choices.annotate(vote_count=Count('votes'))
        for choice in choices:
            percent = round(choice.vote_count * 100 / total) if total else 0
            results.append({'choice': choice, 'votes': choice.vote_count, 'percent': percent})

    return render(request, 'polls/poll_detail.html', {
        'poll': poll,
        'choices': poll.choices.all(),
        'has_voted': has_voted,
        'user_choice_id': user_vote.choice_id if user_vote else None,
        'picked_choice': user_vote.choice if user_vote else None,
        'show_results': show_results,
        'results': results,
        'total_votes': poll.votes.count(),
        'is_owner': request.user.is_authenticated and poll.owner_id == request.user.id,
    })


@require_POST
def poll_vote(request, pk):
    """Record one vote. Logged-in users are tracked by account, guests by session."""
    poll = get_object_or_404(Poll, pk=pk)

    if not poll.is_open:
        messages.error(request, 'This poll is closed.')
        return redirect(poll)

    try:
        choice = poll.choices.get(pk=request.POST.get('choice'))
    except (Choice.DoesNotExist, ValueError):
        messages.error(request, 'Please select one of the choices.')
        return redirect(poll)

    if _has_voted(request, poll):
        messages.error(request, 'You have already voted in this poll.')
        return redirect(poll)

    if request.user.is_authenticated:
        voter = {'user': request.user}
    else:
        if not request.session.session_key:
            request.session.create()
        voter = {'session_key': request.session.session_key}

    try:
        with transaction.atomic():
            Vote.objects.create(poll=poll, choice=choice, **voter)
    except IntegrityError:
        messages.error(request, 'You have already voted in this poll.')
    else:
        messages.success(request, 'Thanks for voting!')
    return redirect(poll)


@login_required
def poll_create(request):
    """Create a new public poll (registered users only)."""
    form = PollForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        poll = form.save(owner=request.user)
        messages.success(request, 'Your poll is live!')
        return redirect(poll)
    return render(request, 'polls/poll_form.html', {'form': form})


@login_required
def my_polls(request):
    """Polls created by the logged-in user, with management actions."""
    polls = (
        Poll.objects.filter(owner=request.user)
        .annotate(vote_count=Count('votes'))
        .order_by('-created_at')
    )
    return render(request, 'polls/my_polls.html', {'polls': polls})


def _get_owned_poll(request, pk):
    """Fetch a poll only if the current user owns it, otherwise 404."""
    return get_object_or_404(Poll, pk=pk, owner=request.user)


@login_required
@require_POST
def poll_toggle(request, pk):
    """Close an open poll or reopen a closed one."""
    poll = _get_owned_poll(request, pk)
    poll.is_closed = not poll.is_closed
    poll.save(update_fields=['is_closed'])
    messages.success(request, 'Poll closed.' if poll.is_closed else 'Poll reopened.')
    return redirect('polls:mine')


@login_required
@require_POST
def poll_delete(request, pk):
    poll = _get_owned_poll(request, pk)
    poll.delete()
    messages.success(request, 'Poll deleted.')
    return redirect('polls:mine')


def my_voted_polls(request):
    voter = _voter_filter(request)
    if voter:
        base_votes = Vote.objects.filter(**voter)
        voted_poll_ids = base_votes.values('poll_id')
        voted_polls_qs = Poll.objects.filter(id__in=Subquery(voted_poll_ids)).order_by('-created_at')
        _log_sql("my_voted_polls Subquery SQL", voted_polls_qs)
        votes = (
            base_votes
            .select_related('poll', 'poll__owner', 'choice')
            .order_by('-created_at')
        )
    else:
        _log_sql("my_voted_polls Subquery SQL (empty)", Poll.objects.none())
        votes = Vote.objects.none()


    return render(request, 'polls/my_voted_polls.html', {
        'votes': votes,
    })