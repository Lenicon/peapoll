from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Choice, Poll, Vote


def make_poll(owner, question='Favorite food?', choices=('Pizza', 'Burgers'), **kwargs):
    poll = Poll.objects.create(owner=owner, question=question, **kwargs)
    for text in choices:
        Choice.objects.create(poll=poll, text=text)
    return poll


class PollModelTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user('owner', 'o@example.com', 'pass12345!')

    def test_open_by_default(self):
        self.assertTrue(make_poll(self.owner).is_open)

    def test_manually_closed(self):
        self.assertFalse(make_poll(self.owner, is_closed=True).is_open)

    def test_past_closing_date_is_closed(self):
        poll = make_poll(self.owner, closes_at=timezone.now() - timedelta(minutes=1))
        self.assertFalse(poll.is_open)


class PublicPollTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user('owner', 'o@example.com', 'pass12345!')
        self.poll = make_poll(self.owner)

    def test_anonymous_can_view_home_list_and_detail(self):
        for url in (reverse('home:home'), reverse('polls:list'), self.poll.get_absolute_url()):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'Favorite food?')

    def test_search_filters_polls(self):
        make_poll(self.owner, question='Best pet?')
        response = self.client.get(reverse('polls:list'), {'q': 'pet'})
        self.assertContains(response, 'Best pet?')
        self.assertNotContains(response, 'Favorite food?')

    def test_sort_by_popular_puts_most_voted_first(self):
        popular = make_poll(self.owner, question='Popular one')
        Vote.objects.create(poll=popular, choice=popular.choices.first(), session_key='abc')
        response = self.client.get(reverse('polls:list'), {'sort': 'popular'})
        polls = [p.question for p in response.context['page']]
        self.assertEqual(polls[0], 'Popular one')


class CreatePollTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('maker', 'm@example.com', 'pass12345!')
        self.url = reverse('polls:create')

    def test_requires_login(self):
        response = self.client.get(self.url)
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={self.url}")

    def test_create_poll(self):
        self.client.login(username='maker', password='pass12345!')
        response = self.client.post(self.url, {
            'question': 'Tea or coffee?',
            'description': '',
            'choices_text': 'Tea\nCoffee\n\n  Water  ',
        })
        poll = Poll.objects.get(question='Tea or coffee?')
        self.assertRedirects(response, poll.get_absolute_url())
        self.assertEqual(poll.owner, self.user)
        self.assertEqual([c.text for c in poll.choices.all()], ['Tea', 'Coffee', 'Water'])

    def test_needs_two_choices(self):
        self.client.login(username='maker', password='pass12345!')
        response = self.client.post(self.url, {'question': 'Q?', 'choices_text': 'Only one'})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Poll.objects.exists())

    def test_rejects_duplicate_choices(self):
        self.client.login(username='maker', password='pass12345!')
        response = self.client.post(self.url, {'question': 'Q?', 'choices_text': 'A\na'})
        self.assertFalse(Poll.objects.exists())
        self.assertContains(response, 'must be different')

    def test_rejects_past_closing_date(self):
        self.client.login(username='maker', password='pass12345!')
        response = self.client.post(self.url, {
            'question': 'Q?', 'choices_text': 'A\nB', 'closes_at': '2000-01-01T10:00',
        })
        self.assertFalse(Poll.objects.exists())
        self.assertContains(response, 'must be in the future')


class VotingTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user('owner', 'o@example.com', 'pass12345!')
        self.voter = User.objects.create_user('voter', 'v@example.com', 'pass12345!')
        self.poll = make_poll(self.owner)
        self.choice = self.poll.choices.first()
        self.url = reverse('polls:vote', args=[self.poll.pk])

    def test_anonymous_can_vote_once(self):
        self.client.post(self.url, {'choice': self.choice.pk})
        self.assertEqual(Vote.objects.count(), 1)
        self.assertIsNone(Vote.objects.get().user)

        self.client.post(self.url, {'choice': self.choice.pk})
        self.assertEqual(Vote.objects.count(), 1)

    def test_logged_in_user_can_vote_once(self):
        self.client.login(username='voter', password='pass12345!')
        self.client.post(self.url, {'choice': self.choice.pk})
        self.client.post(self.url, {'choice': self.poll.choices.last().pk})
        self.assertEqual(Vote.objects.filter(user=self.voter).count(), 1)

    def test_cannot_vote_on_closed_poll(self):
        self.poll.is_closed = True
        self.poll.save()
        self.client.post(self.url, {'choice': self.choice.pk})
        self.assertEqual(Vote.objects.count(), 0)

    def test_choice_from_other_poll_is_rejected(self):
        other = make_poll(self.owner, question='Other?')
        self.client.post(self.url, {'choice': other.choices.first().pk})
        self.assertEqual(Vote.objects.count(), 0)

    def test_invalid_choice_value_is_rejected(self):
        self.client.post(self.url, {'choice': 'abc'})
        self.assertEqual(Vote.objects.count(), 0)

    def test_get_not_allowed(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_results_shown_after_voting_with_percentages(self):
        Vote.objects.create(poll=self.poll, choice=self.choice, session_key='other1')
        self.client.post(self.url, {'choice': self.choice.pk})
        response = self.client.get(self.poll.get_absolute_url())
        self.assertTrue(response.context['show_results'])
        self.assertEqual(response.context['total_votes'], 2)
        self.assertEqual(response.context['results'][0]['percent'], 100)

    def test_voting_form_shown_before_voting(self):
        response = self.client.get(self.poll.get_absolute_url())
        self.assertFalse(response.context['show_results'])
        self.assertContains(response, 'name="choice"')


class ManagePollTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user('owner', 'o@example.com', 'pass12345!')
        self.other = User.objects.create_user('other', 'x@example.com', 'pass12345!')
        self.poll = make_poll(self.owner)

    def test_my_polls_requires_login(self):
        self.assertEqual(self.client.get(reverse('polls:mine')).status_code, 302)

    def test_owner_can_close_and_reopen(self):
        self.client.login(username='owner', password='pass12345!')
        url = reverse('polls:toggle', args=[self.poll.pk])
        self.client.post(url)
        self.poll.refresh_from_db()
        self.assertTrue(self.poll.is_closed)
        self.client.post(url)
        self.poll.refresh_from_db()
        self.assertFalse(self.poll.is_closed)

    def test_owner_can_delete(self):
        self.client.login(username='owner', password='pass12345!')
        self.client.post(reverse('polls:delete', args=[self.poll.pk]))
        self.assertFalse(Poll.objects.exists())

    def test_non_owner_cannot_modify(self):
        self.client.login(username='other', password='pass12345!')
        self.assertEqual(self.client.post(reverse('polls:toggle', args=[self.poll.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse('polls:delete', args=[self.poll.pk])).status_code, 404)
        self.assertTrue(Poll.objects.exists())

    def test_my_polls_only_lists_own(self):
        make_poll(self.other, question='Not mine')
        self.client.login(username='owner', password='pass12345!')
        response = self.client.get(reverse('polls:mine'))
        self.assertContains(response, 'Favorite food?')
        self.assertNotContains(response, 'Not mine')
