import uuid
from StringIO import StringIO

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import CommandError
from django.db.models.signals import post_save
from django.test import TestCase
from django.test.client import Client
from django.test.utils import override_settings

from zope.interface import implements

from vumi.tests.helpers import (
    generate_proxies, proxyable, IHelper, IHelperEnabledTestCase)

from go.base import models as base_models
from go.base import utils as base_utils
from go.vumitools.tests.helpers import VumiApiHelper


class GoDjangoTestCase(TestCase):
    implements(IHelperEnabledTestCase)

    _cleanup_funcs = None

    def tearDown(self):
        # Run any cleanup code we've registered with .add_cleanup().
        if self._cleanup_funcs is not None:
            for cleanup, args, kw in reversed(self._cleanup_funcs):
                cleanup(*args, **kw)

    def add_cleanup(self, func, *args, **kw):
        if self._cleanup_funcs is None:
            self._cleanup_funcs = []
        self._cleanup_funcs.append((func, args, kw))

    def add_helper(self, helper_object, *args, **kw):
        if not IHelper.providedBy(helper_object):
            raise ValueError(
                "Helper object does not provide the IHelper interface: %s" % (
                    helper_object,))
        self.add_cleanup(helper_object.cleanup)
        helper_object.setup(*args, **kw)
        return helper_object


class DjangoVumiApiHelper(object):
    implements(IHelper)

    is_sync = True  # For when we're being treated like a VumiApiHelper.

    def __init__(self, use_riak=True):
        self.use_riak = use_riak
        self._vumi_helper = VumiApiHelper(is_sync=True, use_riak=use_riak)

        generate_proxies(self, self._vumi_helper)
        # TODO: Better/more generic way to do this patching?
        self._settings_patches = []
        self.replace_django_bits()

    def setup(self, setup_vumi_api=True):
        if setup_vumi_api:
            self.setup_vumi_api()

    def cleanup(self):
        self._vumi_helper.cleanup()
        self.restore_django_bits()
        for patch in reversed(self._settings_patches):
            patch.disable()

    def replace_django_bits(self):
        # We do this redis manager hackery here because we might use it from
        # Django-land before setting (or without) up a vumi_api.
        # TODO: Find a nicer way to give everything the same fake redis.
        pcfg = self._vumi_helper._persistence_helper._config_overrides
        pcfg['redis_manager']['FAKE_REDIS'] = self.get_redis_manager()

        vumi_config = settings.VUMI_API_CONFIG.copy()
        vumi_config.update(self.mk_config({}))
        self.patch_settings(VUMI_API_CONFIG=vumi_config)

        has_listeners = lambda: post_save.has_listeners(get_user_model())
        assert has_listeners(), "User model has no listeners. Aborting."
        post_save.disconnect(
            sender=get_user_model(),
            dispatch_uid='go.base.models.create_user_profile')
        assert not has_listeners(), (
            "User model still has listeners. Make sure DjangoVumiApiHelper"
            " is cleaned up properly.")
        post_save.connect(
            self.create_user_profile,
            sender=get_user_model(),
            dispatch_uid='DjangoVumiApiHelper.create_user_profile')

    def restore_django_bits(self):
        post_save.disconnect(
            sender=get_user_model(),
            dispatch_uid='DjangoVumiApiHelper.create_user_profile')
        post_save.connect(
            base_models.create_user_profile,
            sender=get_user_model(),
            dispatch_uid='go.base.models.create_user_profile')

    @proxyable
    def get_client(self):
        client = Client()
        client.login(username='user@domain.com', password='password')
        return client

    @proxyable
    def patch_settings(self, **kwargs):
        patch = override_settings(**kwargs)
        patch.enable()
        self._settings_patches.append(patch)

    @proxyable
    def make_django_user(self):
        user = get_user_model().objects.create_user(
            email='user@domain.com', password='password')
        user.first_name = "Test"
        user.last_name = "User"
        user.save()
        user_api = base_utils.vumi_api_for_user(user)
        return self.get_user_helper(user_api.user_account_key)

    def create_user_profile(self, sender, instance, created, **kwargs):
        if not created:
            return

        if not self.use_riak:
            # Just create the account key, no actual user.
            base_models.UserProfile.objects.create(
                user=instance, user_account=uuid.uuid4())
            return

        user_helper = self.make_user(
            unicode(instance.email), enable_search=False)
        base_models.UserProfile.objects.create(
            user=instance, user_account=user_helper.account_key)
        # We add this to the helper instance rather than subclassing or
        # wrapping it because we only need the one thing.
        user_helper.get_django_user = lambda: (
            get_user_model().objects.get(pk=instance.pk))

    @property
    def amqp_connection(self):
        # This is a property so that we get the patched version.
        return base_utils.connection


class GoAccountCommandTestCase(GoDjangoTestCase):
    """TestCase subclass for testing management commands.

    This isn't a helper because everything it does requires asserting, which
    requires a TestCase object to call assertion methods on.
    """

    def setup_command(self, command_class):
        self.command_class = command_class
        self.vumi_helper = self.add_helper(DjangoVumiApiHelper())
        self.user_helper = self.vumi_helper.make_django_user()
        self.command = self.command_class()
        self.command.stdout = StringIO()
        self.command.stderr = StringIO()

    def call_command(self, *command, **options):
        # Make sure we have options for the command(s) specified
        for cmd_name in command:
            self.assertTrue(
                cmd_name in self.command.list_commands(),
                "Command '%s' has no command line option" % (cmd_name,))
        # Make sure we have options for any option keys specified
        opt_dests = set(opt.dest for opt in self.command.option_list)
        for opt_dest in options:
            self.assertTrue(
                opt_dest in opt_dests,
                "Option key '%s' has no command line option" % (opt_dest,))
        # Call the command handler
        email_address = self.user_helper.get_django_user().email
        return self.command.handle(
            email_address=email_address, command=command, **options)

    def assert_command_error(self, regexp, *command, **options):
        self.assertRaisesRegexp(
            CommandError, regexp, self.call_command, *command, **options)

    def assert_command_output(self, expected_output, *command, **options):
        self.call_command(*command, **options)
        self.assertEqual(expected_output, self.command.stdout.getvalue())
