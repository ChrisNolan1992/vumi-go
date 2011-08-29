from django.test import TestCase
from django.test.client import Client
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.conf import settings
from go.conversation.models import Conversation
from go.base.models import ContactGroup, Contact
from go.base.utils import padded_queryset
from datetime import datetime
from os import path


def reload_record(record):
    return record.__class__.objects.get(pk=record.pk)


class ConversationTestCase(TestCase):

    fixtures = ['test_user', 'test_conversation']

    def setUp(self):
        self.client = Client()
        self.client.login(username='username', password='password')

    def tearDown(self):
        pass

    def test_recent_conversations(self):
        """
        Conversation.objects.recent() should return the most recent
        conversations, if given a limit it should return a list of that
        exact size padded with the value of `padding`.
        """
        conversations = padded_queryset(Conversation.objects.all(), size=10,
            padding='')
        self.assertEqual(len(conversations), 10)
        self.assertEqual(len(filter(lambda v: v is not '', conversations)), 1)

    def test_new_conversation(self):
        """test the creation of a new conversation"""
        # render the form
        self.assertEqual(Conversation.objects.count(), 1)
        response = self.client.get(reverse('conversations:new'))
        self.assertEqual(response.status_code, 200)
        # post the form
        response = self.client.post(reverse('conversations:new'), {
            'subject': 'the subject',
            'message': 'the message',
            'start_date': datetime.utcnow().strftime('%Y-%m-%d'),
            'start_time': datetime.utcnow().strftime('%H:%M'),
        })
        self.assertEqual(Conversation.objects.count(), 2)


class ContactGroupForm(TestCase):

    fixtures = ['test_user', 'test_conversation', 'test_group', 'test_contact']

    def setUp(self):
        self.user = User.objects.get(username='username')
        self.conversation = self.user.conversation_set.latest()
        self.client = Client()
        self.client.login(username=self.user.username, password='password')
        self.csv_file = open(path.join(settings.PROJECT_ROOT, 'base',
            'fixtures', 'sample-contacts.csv'))

    def tearDown(self):
        pass

    def test_group_selection(self):
        """Select an existing group and use that as the group for the
        conversation"""
        response = self.client.post(reverse('conversations:participants',
            kwargs={'conversation_pk': self.conversation.pk}), {
            'groups': [grp.pk for grp in ContactGroup.objects.all()]
        })
        self.assertRedirects(response, reverse('conversations:send', kwargs={
            'conversation_pk': self.conversation.pk}))

    def test_index(self):
        """Display all conversations"""
        response = self.client.get(reverse('conversations:index'))
        self.assertContains(response, self.conversation.subject)

    def test_index_search(self):
        """Filter conversations based on query string"""
        response = self.client.get(reverse('conversations:index'), {
            'q': 'something that does not exist in the fixtures'})
        self.assertNotContains(response, self.conversation.subject)

    def test_group_creation(self):
        """test creation of a new contact group when starting a conversation"""
        self.assertEqual(ContactGroup.objects.count(), 1)
        response = self.client.post(reverse('conversations:participants',
            kwargs={'conversation_pk': self.conversation.pk}))
        self.assertEqual(ContactGroup.objects.count(), 1)
        response = self.client.post(reverse('conversations:participants',
            kwargs={'conversation_pk': self.conversation.pk}), {
                'name': 'Test Group'
            })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ContactGroup.objects.count(), 2)
        self.assertEqual(ContactGroup.objects.latest().name, 'Test Group')

    def test_contacts_upload(self):
        """test uploading of contacts via CSV file"""
        response = self.client.post(reverse('conversations:participants',
            kwargs={'conversation_pk': self.conversation.pk}), {
            'name': 'Test Group',
            'file': self.csv_file,
        })
        self.assertRedirects(response, reverse('conversations:send',
            kwargs={'conversation_pk': self.conversation.pk}))
        group = ContactGroup.objects.latest()
        self.assertEquals(group.name, 'Test Group')
        contacts = Contact.objects.filter(groups=group)
        self.assertEquals(contacts.count(), 3)
        for idx, contact in enumerate(contacts, start=1):
            self.assertTrue(contact.name, 'Name %s' % idx)
            self.assertTrue(contact.surname, 'Surname %s' % idx)
            self.assertTrue(contact.msisdn.startswith('+2776123456%s' % idx))
            self.assertIn(contact, group.contact_set.all())
        self.assertIn(group, self.conversation.groups.all())

    def test_priority_of_select_over_group_creation(self):
        """Selected existing groups takes priority over creating
        new groups"""
        group = ContactGroup.objects.create(user=self.user, name='Test Group')
        response = self.client.post(reverse('conversations:participants',
            kwargs={'conversation_pk': self.conversation.pk}), {
            'name': 'Should be ignored',
            'contact_group': group.pk,
            'file': self.csv_file,
        })
        self.assertRedirects(response, reverse('conversations:send', kwargs={
            'conversation_pk': self.conversation.pk}))
        self.assertEqual(ContactGroup.objects.latest(), group)
        self.assertEqual(ContactGroup.objects.count(), 2)
        contacts = Contact.objects.filter(groups=group)
        self.assertEqual(contacts.count(), 3)
        self.assertIn(group, self.conversation.groups.all())

    def test_sending_preview(self):
        """test sending of conversation to a selected set of preview
        contacts"""
        response = self.client.post(reverse('conversations:send', kwargs={
            'conversation_pk': self.conversation.pk
        }), {
            'contact': [c.pk for c in Contact.objects.all()]
        })
        self.assertRedirects(response, reverse('conversations:start', kwargs={
            'conversation_pk': self.conversation.pk}))

    def test_start(self):
        """
        Test the start conversation view
        """
        response = self.client.post(reverse('conversations:start', kwargs={
            'conversation_pk': self.conversation.pk}))
        self.assertRedirects(response, reverse('conversations:show', kwargs={
            'conversation_pk': self.conversation.pk}))