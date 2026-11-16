from django import forms
from django.db import transaction
from django.utils import timezone

from .models import Choice, Poll

MIN_CHOICES = 2
MAX_CHOICES = 10


class PollForm(forms.ModelForm):
    """
    Create-a-poll form. Choices are typed one per line in a single textarea,
    which keeps the page simple and works without JavaScript.
    """
    choices_text = forms.CharField(
        label='Choices',
        help_text=f'One choice per line ({MIN_CHOICES}-{MAX_CHOICES} choices).',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'placeholder': 'Pizza\nBurgers\nTacos',
        }),
    )

    class Meta:
        model = Poll
        fields = ['question', 'description', 'closes_at']
        labels = {'closes_at': 'Closing date (optional)'}
        widgets = {
            'question': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'What do you want to ask?',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Add some context (optional)',
            }),
            'closes_at': forms.DateTimeInput(
                attrs={'class': 'form-control', 'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M',
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['closes_at'].input_formats = ['%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M:%S']

    def clean_closes_at(self):
        closes_at = self.cleaned_data.get('closes_at')
        if closes_at and closes_at <= timezone.now():
            raise forms.ValidationError('The closing date must be in the future.')
        return closes_at

    def clean_choices_text(self):
        lines = [line.strip() for line in self.cleaned_data['choices_text'].splitlines()]
        lines = [line for line in lines if line]

        if len(lines) < MIN_CHOICES:
            raise forms.ValidationError(f'Please enter at least {MIN_CHOICES} choices.')
        if len(lines) > MAX_CHOICES:
            raise forms.ValidationError(f'You can add at most {MAX_CHOICES} choices.')
        if any(len(line) > 100 for line in lines):
            raise forms.ValidationError('Each choice must be 100 characters or fewer.')
        if len({line.lower() for line in lines}) != len(lines):
            raise forms.ValidationError('Choices must be different from each other.')
        return lines

    @transaction.atomic
    def save(self, owner):
        poll = super().save(commit=False)
        poll.owner = owner
        poll.save()
        Choice.objects.bulk_create(
            Choice(poll=poll, text=text) for text in self.cleaned_data['choices_text']
        )
        return poll
