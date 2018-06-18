from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import resolve_url as r
from sgce.core.forms import UserForm
from sgce.core.models import Profile
from sgce.core.tests.base import LoggedInTestCase


class UserCreateWithoutPermission(LoggedInTestCase):
    def setUp(self):
        super(UserCreateWithoutPermission, self).setUp()
        # user created on LoggedInTestCase setUp()
        self.user = get_user_model().objects.get(pk=1)

        self.response = self.client.get(r('core:user-create'))

    def test_get(self):
        """Must return 403 HttpError (No permission)"""
        self.assertEqual(403, self.response.status_code)


# class Base. Add permission: can_enable_or_disable_user
class Base(LoggedInTestCase):
    def setUp(self):
        super(Base, self).setUp()
        # permission required: profile.can_enable_or_disable_user
        content_type = ContentType.objects.get_for_model(get_user_model())
        self.permission = Permission.objects.get(
            codename='add_user',
            content_type=content_type,
        )

        self.user.user_permissions.add(self.permission)
        self.user.refresh_from_db()


class UserCreateGet(Base):
    def setUp(self):
        super(UserCreateGet, self).setUp()
        self.response = self.client.get(r('core:user-create'))

    def test_get(self):
        self.assertEqual(200, self.response.status_code)

    def test_template(self):
        self.assertTemplateUsed(self.response, 'core/user/user_form.html')

    def test_html(self):
        """Html must contain input tags"""
        tags = (
            ('<form', 1),
            # Csrf, first_name, last_name, email, superuser, username and password
            ('<input', 7),
            # Role
            ('<select', 1),
            ('type="text"', 3),
            ('type="password"', 1),
            ('type="checkbox"', 1),
            ('type="email"', 1),
            ('type="submit"', 1),
        )
        for text, count in tags:
            with self.subTest():
                self.assertContains(self.response, text, count)

    def test_has_form(self):
        """Context must have user form"""
        form = self.response.context['form']
        self.assertIsInstance(form, UserForm)

    def test_csrf(self):
        """HTML must contains csrf"""
        self.assertContains(self.response, 'csrfmiddlewaretoken')


class UserCreatePost(Base):
    def setUp(self):
        super(UserCreatePost, self).setUp()
        data = dict(
            first_name = 'Alan',
            last_name = 'Turing',
            email = 'alan@turing.com',
            is_superuser = False,
            username = 'alanturing',
            password = 'password',
            role = Profile.MANAGER
        )
        self.response = self.client.post(r('core:user-create'), data)

    def test_post(self):
        """ Valid POST should redirect to 'user-list' """
        self.assertRedirects(self.response, r('core:user-list'))

    def test_save_user(self):
        self.assertTrue(get_user_model().objects.filter(username='alanturing').exists())

    def test_role_change_in_profile(self):
        """
        Must update profile.role attr. By default profile.role is 'u'.
        When a user is created, a signal is triggered: create_user_profile (core/signals.py)
        """
        profile = get_user_model().objects.get(username='alanturing').profile
        self.assertEqual(Profile.MANAGER, profile.role)


class UserCreatePostInvalid(Base):
    def setUp(self):
        super(UserCreatePostInvalid, self).setUp()
        self.response = self.client.post(r('core:user-create'), {})

    def test_post(self):
        """Invalid Post should not redirect"""
        self.assertEqual(200, self.response.status_code)

    def test_template(self):
        self.assertTemplateUsed(self.response, 'core/user/user_form.html')

    def test_has_form(self):
        form = self.response.context['form']
        self.assertIsInstance(form, UserForm)

    def test_form_has_errors(self):
        form = self.response.context['form']
        self.assertTrue(form.errors)

    def test_dont_save_new_user(self):
        """The base class LoggedInTestCase creates a user."""
        self.assertEqual(get_user_model().objects.exists(), 1)