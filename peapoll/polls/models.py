from django.conf import settings
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone


class Poll(models.Model):
    """A public poll created by a registered user."""
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='polls',
    )
    question = models.CharField(max_length=200)
    description = models.TextField(blank=True, max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)
    closes_at = models.DateTimeField(null=True, blank=True)
    is_closed = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.question

    def get_absolute_url(self):
        return reverse('polls:detail', args=[self.pk])

    @property
    def is_open(self):
        """Open means not manually closed and not past its closing date."""
        if self.is_closed:
            return False
        if self.closes_at and self.closes_at <= timezone.now():
            return False
        return True

    @property
    def total_votes(self):
        return self.votes.count()


class Choice(models.Model):
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name='choices')
    text = models.CharField(max_length=100)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return self.text


class Vote(models.Model):
    """
    One vote per poll per voter. Logged-in users are identified by account,
    anonymous visitors by their session key, so public polls can be answered
    without signing up.
    """
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name='votes')
    choice = models.ForeignKey(Choice, on_delete=models.CASCADE, related_name='votes')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='votes',
    )
    session_key = models.CharField(max_length=40, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['poll', 'user'],
                condition=Q(user__isnull=False),
                name='unique_vote_per_user',
            ),
            models.UniqueConstraint(
                fields=['poll', 'session_key'],
                condition=~Q(session_key=''),
                name='unique_vote_per_session',
            ),
        ]

    def __str__(self):
        return f'{self.poll_id}: {self.choice}'
