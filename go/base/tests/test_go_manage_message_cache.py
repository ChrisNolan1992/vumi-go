from tempfile import NamedTemporaryFile

from go.base.management.commands import go_manage_message_cache
from go.base.tests.helpers import GoCommandTestCase


def make_batch_keys_file(batch_keys):
    batch_keys_file = NamedTemporaryFile()
    batch_keys_file.write('\n'.join(batch_keys))
    batch_keys_file.flush()
    return batch_keys_file


class TestGoManageMessageCache(GoCommandTestCase):

    def setUp(self):
        self.setup_command(go_manage_message_cache.Command)

    def clear_batches(self, batches):
        """
        Clear the message cache so that all batches need reconciliation.
        """
        vumi_api = self.vumi_helper.get_vumi_api()
        for batch_id in batches:
            vumi_api.mdb.cache.clear_batch(batch_id)
        self.assert_batches_cleared(batches)

    def assert_batches_cleared(self, batches):
        vumi_api = self.vumi_helper.get_vumi_api()
        for batch_id in batches:
            self.assertFalse(vumi_api.mdb.cache.batch_exists(batch_id))

    def _assert_batches_recon_state(self, batches, recon_required):
        vumi_api = self.vumi_helper.get_vumi_api()
        needs_recon = vumi_api.mdb.needs_reconciliation
        self.assertEqual(
            [(batch_id, needs_recon(batch_id)) for batch_id in batches],
            [(batch_id, recon_required) for batch_id in batches])

    def assert_batches_reconciled(self, batches):
        self._assert_batches_recon_state(batches, False)

    def uses_counters(self, batch_id):
        vumi_api = self.vumi_helper.get_vumi_api()
        return vumi_api.mdb.cache.uses_counters(batch_id)

    def test_reconcile_conversation(self):
        conv = self.user_helper.create_conversation(u"http_api")
        self.clear_batches([conv.batch.key])
        expected_output = "\n".join([
            u'Processing account Test User'
            u' <user@domain.com> [test-0-user] ...',
            u'  Performing reconcile on'
            u' batch %s ...' % conv.batch.key,
            u'done.',
            u''
        ])
        self.assert_command_output(
            expected_output, 'reconcile',
            email_address=self.user_email, conversation_key=conv.key)
        self.assert_batches_reconciled([conv.batch.key])

    def test_reconcile_active_conversations_in_account(self):
        conv1 = self.user_helper.create_conversation(u"http_api")
        conv2 = self.user_helper.create_conversation(u"http_api")
        batch_ids = sorted([conv1.batch.key, conv2.batch.key])
        self.clear_batches(batch_ids)
        expected_output = "\n".join([
            u'Processing account Test User'
            u' <user@domain.com> [test-0-user] ...',
            u'  Performing reconcile on'
            u' batch %s ...' % batch_ids[0],
            u'  Performing reconcile on'
            u' batch %s ...' % batch_ids[1],
            u'done.',
            u''
        ])
        self.assert_command_output(
            expected_output, 'reconcile',
            email_address=self.user_email, active_conversations=True)
        self.assert_batches_reconciled(batch_ids)

    def test_reconcile_active_conversations_in_all_accounts(self):
        user1 = self.vumi_helper.make_django_user("user1")
        user2 = self.vumi_helper.make_django_user("user2")
        conv1 = user1.create_conversation(u"http_api")
        conv2 = user2.create_conversation(u"http_api")
        batch_ids = [conv1.batch.key, conv2.batch.key]
        self.clear_batches(batch_ids)
        expected_output = "\n".join([
            u'Processing account Test User <user1> [test-1-user] ...',
            u'  Performing reconcile on'
            u' batch %s ...' % conv1.batch.key,
            u'done.',
            u'Processing account Test User <user2> [test-2-user] ...',
            u'  Performing reconcile on'
            u' batch %s ...' % conv2.batch.key,
            u'done.',
            u''
        ])
        self.assert_command_output(
            expected_output, 'reconcile',
            active_conversations=True)
        self.assert_batches_reconciled(batch_ids)

    def test_reconcile_archived_conversations_in_all_accounts(self):
        user1 = self.vumi_helper.make_django_user("user1")
        user2 = self.vumi_helper.make_django_user("user2")
        conv1 = user1.create_conversation(u"http_api")
        conv1.set_status_finished()
        conv1.save()
        conv2 = user2.create_conversation(u"http_api")
        conv2.set_status_finished()
        conv2.save()
        batch_ids = [conv1.batch.key, conv2.batch.key]
        self.clear_batches(batch_ids)
        expected_output = "\n".join([
            u'Processing account Test User <user1> [test-1-user] ...',
            u'  Performing reconcile on'
            u' batch %s ...' % conv1.batch.key,
            u'done.',
            u'Processing account Test User <user2> [test-2-user] ...',
            u'  Performing reconcile on'
            u' batch %s ...' % conv2.batch.key,
            u'done.',
            u''
        ])
        self.assert_command_output(
            expected_output, 'reconcile',
            archived_conversations=True)
        self.assert_batches_reconciled(batch_ids)

    def test_reconcile_router(self):
        rtr = self.user_helper.create_router(u"dummy")
        self.clear_batches([rtr.batch.key])
        expected_output = "\n".join([
            u'Processing account Test User'
            u' <user@domain.com> [test-0-user] ...',
            u'  Performing reconcile on'
            u' batch %s ...' % rtr.batch.key,
            u'done.',
            u''
        ])
        self.assert_command_output(
            expected_output, 'reconcile',
            email_address=self.user_email, router_key=rtr.key)
        self.assert_batches_reconciled([rtr.batch.key])

    def test_reconcile_active_routers_in_account(self):
        rtr1 = self.user_helper.create_router(u"dummy")
        rtr2 = self.user_helper.create_router(u"dummy")
        batch_ids = sorted([rtr1.batch.key, rtr2.batch.key])
        self.clear_batches(batch_ids)
        expected_output = "\n".join([
            u'Processing account Test User'
            u' <user@domain.com> [test-0-user] ...',
            u'  Performing reconcile on'
            u' batch %s ...' % batch_ids[0],
            u'  Performing reconcile on'
            u' batch %s ...' % batch_ids[1],
            u'done.',
            u''
        ])
        self.assert_command_output(
            expected_output, 'reconcile',
            email_address=self.user_email, active_routers=True)
        self.assert_batches_reconciled(batch_ids)

    def test_reconcile_active_routers_in_all_accounts(self):
        user1 = self.vumi_helper.make_django_user("user1")
        user2 = self.vumi_helper.make_django_user("user2")
        rtr1 = user1.create_router(u"dummy")
        rtr2 = user2.create_router(u"dummy")
        batch_ids = [rtr1.batch.key, rtr2.batch.key]
        self.clear_batches(batch_ids)
        expected_output = "\n".join([
            u'Processing account Test User <user1> [test-1-user] ...',
            u'  Performing reconcile on'
            u' batch %s ...' % rtr1.batch.key,
            u'done.',
            u'Processing account Test User <user2> [test-2-user] ...',
            u'  Performing reconcile on'
            u' batch %s ...' % rtr2.batch.key,
            u'done.',
            u''
        ])
        self.assert_command_output(
            expected_output, 'reconcile',
            active_routers=True)
        self.assert_batches_reconciled(batch_ids)

    def test_reconcile_archived_routers_in_all_accounts(self):
        user1 = self.vumi_helper.make_django_user("user1")
        user2 = self.vumi_helper.make_django_user("user2")
        rtr1 = user1.create_router(u"dummy")
        rtr1.set_status_finished()
        rtr1.save()
        rtr2 = user2.create_router(u"dummy")
        rtr2.set_status_finished()
        rtr2.save()
        batch_ids = [rtr1.batch.key, rtr2.batch.key]
        self.clear_batches(batch_ids)
        expected_output = "\n".join([
            u'Processing account Test User <user1> [test-1-user] ...',
            u'  Performing reconcile on'
            u' batch %s ...' % rtr1.batch.key,
            u'done.',
            u'Processing account Test User <user2> [test-2-user] ...',
            u'  Performing reconcile on'
            u' batch %s ...' % rtr2.batch.key,
            u'done.',
            u''
        ])
        self.assert_command_output(
            expected_output, 'reconcile',
            archived_routers=True)
        self.assert_batches_reconciled(batch_ids)

    def test_reconcile_batches_from_file(self):
        conv = self.user_helper.create_conversation(u"http_api")
        self.clear_batches([conv.batch.key])
        batch_keys_file = make_batch_keys_file([conv.batch.key])
        expected_output = "\n".join([
            u'Processing file %s ...' % (batch_keys_file.name,),
            u'  Performing reconcile on'
            u' batch %s ...' % conv.batch.key,
            u'done.',
            u''
        ])
        self.assert_command_output(
            expected_output, 'reconcile', batch_keys_file=batch_keys_file.name)
        self.assert_batches_reconciled([conv.batch.key])

    def test_reconcile_batches_from_file_and_conversations_in_account(self):
        conv1 = self.user_helper.create_conversation(u"http_api")
        conv2 = self.user_helper.create_conversation(u"http_api")
        batch_ids = sorted([conv1.batch.key, conv2.batch.key])
        self.clear_batches(batch_ids)
        batch_keys_file = make_batch_keys_file([conv1.batch.key])
        expected_output = "\n".join([
            u'Processing file %s ...' % (batch_keys_file.name,),
            u'  Performing reconcile on'
            u' batch %s ...' % conv1.batch.key,
            u'done.',
            u'Processing account Test User'
            u' <user@domain.com> [test-0-user] ...',
            u'  Performing reconcile on'
            u' batch %s ...' % batch_ids[0],
            u'  Performing reconcile on'
            u' batch %s ...' % batch_ids[1],
            u'done.',
            u''
        ])
        self.assert_command_output(
            expected_output, 'reconcile',
            email_address=self.user_email, active_conversations=True,
            batch_keys_file=batch_keys_file.name)
        self.assert_batches_reconciled(batch_ids)

    def test_switch_to_counters(self):
        conv = self.user_helper.create_conversation(u"http_api")
        self.clear_batches([conv.batch.key])
        self.assertFalse(self.uses_counters(conv.batch.key))
        expected_output = "\n".join([
            u'Processing account Test User'
            u' <user@domain.com> [test-0-user] ...',
            u'  Performing switch_to_counters on'
            u' batch %s ...' % conv.batch.key,
            u'done.',
            u''
        ])
        self.assert_command_output(
            expected_output, 'switch_to_counters',
            email_address=self.user_email, conversation_key=conv.key)
        self.assertTrue(self.uses_counters(conv.batch.key))
