from django.contrib import admin

from .models import Choice, Poll, Vote


class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 2


@admin.register(Poll)
class PollAdmin(admin.ModelAdmin):
    list_display = ('question', 'owner', 'created_at', 'is_closed')
    list_filter = ('is_closed', 'created_at')
    search_fields = ('question', 'owner__username')
    inlines = [ChoiceInline]


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ('poll', 'choice', 'user', 'created_at')
    list_filter = ('poll',)
