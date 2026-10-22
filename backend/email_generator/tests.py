from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from . import services
from .models import GeneratedEmail

AI_REPLY = "SUBJECT: Application for Internship\nBODY:\nDear Hiring Manager,\n\nI would like to apply.\n\nRegards,\n[Your Name]"

FORM_DATA = {
    "purpose": "Internship Application", "custom_purpose": "", "recipient_type": "HR",
    "tone": "Professional", "language": "English",
    "important_points": "Python, Django, MySQL skills", "additional_instructions": "",
}


class ParseEmailTests(TestCase):
    def test_parses_subject_and_body(self):
        subject, body = services.parse_email(AI_REPLY)
        self.assertEqual(subject, "Application for Internship")
        self.assertTrue(body.startswith("Dear Hiring Manager"))

    def test_handles_markdown_labels(self):
        subject, body = services.parse_email("**Subject:** Hello\n\n**Body:**\nHi there")
        self.assertEqual((subject, body), ("Hello", "Hi there"))

    def test_bad_reply_raises(self):
        with self.assertRaises(services.AIServiceError):
            services.parse_email("Sorry, I cannot help.")


class AuthTests(TestCase):
    def test_pages_require_login(self):
        for name in ("dashboard", "generate_email", "email_history"):
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 302)
            self.assertIn(reverse("login"), response["Location"])

    def test_register_logs_user_in(self):
        response = self.client.post(reverse("register"), {
            "username": "newuser", "email": "new@example.com",
            "password1": "Str0ng!Pass#123", "password2": "Str0ng!Pass#123",
        })
        self.assertRedirects(response, reverse("dashboard"))
        self.assertTrue(User.objects.filter(username="newuser").exists())

    def test_weak_password_rejected(self):
        response = self.client.post(reverse("register"), {
            "username": "weak", "email": "w@example.com", "password1": "123", "password2": "123",
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="weak").exists())

    def test_invalid_login_shows_error(self):
        response = self.client.post(reverse("login"), {"username": "nobody", "password": "wrong"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please enter a correct")


class EmailFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("alice", password="pass12345")
        self.other = User.objects.create_user("bob", password="pass12345")
        self.client.login(username="alice", password="pass12345")

    @patch("email_generator.services.call_ai", return_value=AI_REPLY)
    def test_generate_saves_email(self, _mock):
        response = self.client.post(reverse("generate_email"), FORM_DATA)
        email = GeneratedEmail.objects.get(user=self.user)
        self.assertRedirects(response, reverse("email_result", args=[email.pk]))
        self.assertEqual(email.subject, "Application for Internship")

    def test_empty_form_is_rejected(self):
        response = self.client.post(reverse("generate_email"), {})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(GeneratedEmail.objects.count(), 0)

    @override_settings(AI_API_KEY="")
    def test_missing_api_key_shows_friendly_error(self):
        response = self.client.post(reverse("generate_email"), FORM_DATA)
        self.assertContains(response, "not configured")
        self.assertEqual(GeneratedEmail.objects.count(), 0)

    @patch("email_generator.services.call_ai", return_value=AI_REPLY)
    def test_ai_actions(self, _mock):
        email = GeneratedEmail.objects.create(user=self.user, subject="Old", body="Old body", **{
            k: v for k, v in FORM_DATA.items() if k not in ("custom_purpose",)
        })
        url = reverse("email_ai_action", args=[email.pk])
        for action in ("improve", "shorter", "formal", "friendly", "regenerate"):
            response = self.client.post(url, {"action": action, "subject": "Old", "body": "Old body"},
                                        content_type="application/json")
            self.assertEqual(response.status_code, 200, action)
            self.assertEqual(response.json()["subject"], "Application for Internship")

    def test_users_cannot_access_other_users_emails(self):
        email = GeneratedEmail.objects.create(user=self.other, purpose="Leave Request", recipient_type="HR",
                                              tone="Polite", language="English", important_points="x",
                                              subject="Secret", body="Secret body")
        self.assertEqual(self.client.get(reverse("email_detail", args=[email.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("email_delete", args=[email.pk])).status_code, 404)
        self.assertTrue(GeneratedEmail.objects.filter(pk=email.pk).exists())

    def test_delete_requires_post(self):
        email = GeneratedEmail.objects.create(user=self.user, purpose="Leave Request", recipient_type="HR",
                                              tone="Polite", language="English", important_points="x",
                                              subject="Mine", body="Body")
        self.assertEqual(self.client.get(reverse("email_delete", args=[email.pk])).status_code, 405)
        self.client.post(reverse("email_delete", args=[email.pk]))
        self.assertFalse(GeneratedEmail.objects.filter(pk=email.pk).exists())

    def test_history_search_and_filter(self):
        base = dict(user=self.user, recipient_type="HR", language="English", important_points="x", body="Body")
        GeneratedEmail.objects.create(subject="Internship at Acme", purpose="Internship Application", tone="Formal", **base)
        GeneratedEmail.objects.create(subject="Need a day off", purpose="Leave Request", tone="Polite", **base)
        response = self.client.get(reverse("email_history"), {"q": "internship"})
        self.assertContains(response, "Internship at Acme")
        self.assertNotContains(response, "Need a day off")
        response = self.client.get(reverse("email_history"), {"tone": "Polite"})
        self.assertContains(response, "Need a day off")
        self.assertNotContains(response, "Internship at Acme")

    def test_dashboard_counts_come_from_database(self):
        GeneratedEmail.objects.create(user=self.user, purpose="Leave Request", recipient_type="HR", tone="Polite",
                                      language="English", important_points="x", subject="A", body="B")
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.context["total"], 1)
        self.assertEqual(response.context["today"], 1)
