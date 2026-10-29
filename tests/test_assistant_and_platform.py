import json
import logging
import os
import subprocess
import sys
from io import StringIO
from pathlib import Path
from unittest import mock

import requests
from django.conf import settings
from django.core.cache import cache
from django.core.management import call_command
from django.db import DatabaseError
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from pymongo.errors import ServerSelectionTimeoutError

from assistant import mongo
from assistant.retrieval import retrieve
from core.weather import get_weather
from support.models import SupportTicket

BASE_DIR = Path(settings.BASE_DIR)


def fake_openai_response(text="Grounded answer.", status=200):
    response = mock.Mock(status_code=status)
    response.json.return_value = {"choices": [{"message": {"content": text}}]}
    return response


class AssistantTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", verbosity=0, stdout=StringIO())

    def setUp(self):
        cache.clear()
        mongo.reset_state()

    def chat(self, message, **extra):
        return self.client.post(reverse("assistant:chat"), json.dumps({"message": message, **extra}),
                                content_type="application/json")


@override_settings(OPENAI_API_KEY="")
class RetrievalTests(AssistantTestCase):
    def test_retrieves_relevant_faq(self):
        result = retrieve("How do I cancel my booking?")
        self.assertTrue(result.is_confident)
        self.assertEqual(result.faqs[0][0].question, "Can I cancel or change a booking?")

    def test_detects_error_codes(self):
        result = retrieve("I keep getting error 4600 and a 404")
        self.assertEqual([c.code for c in result.error_codes], [404, 4600])
        self.assertTrue(all("400 Bad" not in f.question for f, _ in result.faqs))

    def test_unrelated_question_is_below_threshold(self):
        result = retrieve("Who won the football world cup in 1966?")
        self.assertFalse(result.is_confident)

    def test_threshold_is_configurable(self):
        with override_settings(ASSISTANT_RELEVANCE_THRESHOLD=5):
            self.assertFalse(retrieve("How do I cancel my booking?").is_confident)

    def test_basic_website_questions_are_answered(self):
        expected = {
            "How do I sign up?": "How do I create an account?",
            "I forgot my password": "What should I do if I forgot my password?",
            "Where are my bookings?": "Where can I see my bookings?",
            "What does pending mean?": "What do the booking statuses mean?",
            "How long can I rent for?": "What are the booking rules and limits?",
            "What can I rent?": "What items can I rent?",
            "How much does it cost?": "How is the rental price calculated?",
            "How does the owner add products?": "How does the owner post items and manage bookings?",
            "Is my data safe?": "What personal data does the website store?",
            "How do I contact you?": "How do I contact support?",
        }
        for question, faq in expected.items():
            with self.subTest(question=question):
                result = retrieve(question)
                self.assertTrue(result.is_confident)
                self.assertIn(faq, [f.question for f, _ in result.faqs])

    def test_policy_not_in_knowledge_base_is_not_invented(self):
        self.assertFalse(retrieve("Do you deliver?").is_confident)

    def test_retrieves_products(self):
        result = retrieve("Do you rent a farmhouse table?")
        self.assertEqual(result.products[0][0].slug, "rustic-farmhouse-table")


class ChatEndpointTests(AssistantTestCase):
    @override_settings(OPENAI_API_KEY="test-key")
    def test_ai_answer_is_grounded_in_retrieved_faq(self):
        with mock.patch("assistant.llm.requests.post", return_value=fake_openai_response("You can cancel in My bookings.")) as post:
            response = self.chat("How do I cancel my booking?")
        data = response.json()
        self.assertEqual(data["source"], "ai")
        self.assertEqual(data["answer"], "You can cancel in My bookings.")
        sent = post.call_args.kwargs["json"]
        prompt = sent["messages"][1]["content"]
        self.assertIn("Can I cancel or change a booking?", prompt)       # retrieved FAQ is passed
        self.assertNotIn("Too Many Requests", prompt)                     # unrelated FAQ is not
        self.assertIn("Do not invent", sent["messages"][0]["content"])
        self.assertEqual(post.call_args.kwargs["headers"]["Authorization"], "Bearer test-key")

    @override_settings(OPENAI_API_KEY="test-key")
    def test_ai_explains_error_codes_with_reference_data(self):
        with mock.patch("assistant.llm.requests.post", return_value=fake_openai_response("429 explained")) as post:
            data = self.chat("What does 429 mean?").json()
        self.assertEqual(data["error_codes"], [429])
        prompt = post.call_args.kwargs["json"]["messages"][1]["content"]
        self.assertIn("ERROR CODE 429 Too Many Requests", prompt)
        self.assertIn("Troubleshooting:", prompt)

    @override_settings(OPENAI_API_KEY="")
    def test_fallback_when_ai_not_configured(self):
        data = self.chat("What does error 4600 mean?").json()
        self.assertEqual(data["source"], "fallback")
        self.assertEqual(data["code"], 4600)
        self.assertIn("not an AI answer", data["notice"])
        self.assertIn("AI_ASSISTANT_UNAVAILABLE", data["answer"])

    @override_settings(OPENAI_API_KEY="test-key")
    def test_fallback_when_ai_provider_fails(self):
        for side_effect in [requests.Timeout(), requests.ConnectionError()]:
            with mock.patch("assistant.llm.requests.post", side_effect=side_effect):
                data = self.chat("How is the rental price calculated?").json()
            self.assertEqual(data["source"], "fallback")
            self.assertIn("daily rate", data["answer"])
        with mock.patch("assistant.llm.requests.post", return_value=fake_openai_response(status=500)):
            self.assertEqual(self.chat("How is the rental price calculated?").json()["source"], "fallback")

    @override_settings(OPENAI_API_KEY="test-key")
    def test_unknown_question_offers_ticket_and_ticket_is_created(self):
        with mock.patch("assistant.llm.requests.post") as post:
            data = self.chat("What is the capital of Mongolia?").json()
        post.assert_not_called()  # nothing relevant retrieved, so no AI call and no invented answer
        self.assertEqual(data["source"], "no_answer")
        self.assertTrue(data["offer_ticket"])
        self.assertIn("not sure", data["answer"])

        response = self.client.post(reverse("assistant:ticket"),
                                    json.dumps({"message_id": data["message_id"], "email": "guest@example.com"}),
                                    content_type="application/json")
        ref = response.json()["reference"]
        ticket = SupportTicket.objects.get(reference=ref)
        self.assertEqual(ticket.category, SupportTicket.Category.ASSISTANT)
        self.assertIn("Mongolia", ticket.description)
        self.assertEqual(ticket.status, SupportTicket.Status.OPEN)

    def test_ticket_requires_known_message(self):
        response = self.client.post(reverse("assistant:ticket"), json.dumps({"message_id": "0" * 32}),
                                    content_type="application/json")
        self.assertEqual(response.status_code, 400)

    def test_undocumented_code_is_not_guessed(self):
        data = self.chat("What does error 418 mean?").json()
        self.assertEqual(data["source"], "no_answer")
        self.assertIn("won't guess", data["answer"])

    def test_error_page_context_is_used(self):
        with override_settings(OPENAI_API_KEY=""):
            data = self.chat("What should I do?", context="error_404", path="/missing/").json()
        self.assertIn(404, data["error_codes"])

    def test_input_validation(self):
        self.assertEqual(self.chat("").status_code, 400)
        self.assertEqual(self.chat("x" * 501).status_code, 400)
        bad = self.client.post(reverse("assistant:chat"), "not json", content_type="application/json")
        self.assertEqual(bad.status_code, 400)
        huge = self.client.post(reverse("assistant:chat"), json.dumps({"message": "a", "pad": "x" * 5000}),
                                content_type="application/json")
        self.assertEqual(huge.status_code, 413)
        self.assertEqual(self.client.get(reverse("assistant:chat")).status_code, 405)

    @override_settings(CHAT_RATE_LIMIT=3, OPENAI_API_KEY="")
    def test_chat_rate_limit(self):
        codes = [self.chat("How do I reserve an item?").status_code for _ in range(5)]
        self.assertEqual(codes, [200, 200, 200, 429, 429])

    def test_chat_requires_csrf(self):
        client = Client(enforce_csrf_checks=True)
        response = client.post(reverse("assistant:chat"), json.dumps({"message": "hi"}), content_type="application/json")
        self.assertEqual(response.status_code, 403)


class MongoTests(AssistantTestCase):
    @override_settings(MONGODB_URI="mongodb://example.invalid:27017", OPENAI_API_KEY="")
    def test_chat_logs_and_feedback_are_written(self):
        fake_db = mock.MagicMock()
        with mock.patch("assistant.mongo.get_db", return_value=fake_db):
            data = self.chat("How do I reserve an item?").json()
            fb = self.client.post(reverse("assistant:feedback"),
                                  json.dumps({"message_id": data["message_id"], "rating": 5, "comment": "Great"}),
                                  content_type="application/json").json()
        log_doc = fake_db["chat_logs"].insert_one.call_args_list[0].args[0]
        self.assertEqual(log_doc["question"], "How do I reserve an item?")
        self.assertEqual(log_doc["source"], "fallback")
        self.assertTrue(log_doc["faq_ids"])
        self.assertEqual(len(log_doc["conversation_id"]), 32)
        self.assertNotIn("email", log_doc)
        self.assertTrue(fb["stored"])
        fb_doc = fake_db["feedback"].insert_one.call_args.args[0]
        self.assertEqual((fb_doc["rating"], fb_doc["comment"]), (5, "Great"))

    @override_settings(MONGODB_URI="mongodb://example.invalid:27017", OPENAI_API_KEY="")
    def test_site_keeps_working_when_mongodb_is_down(self):
        fake_db = mock.MagicMock()
        fake_db.__getitem__.return_value.insert_one.side_effect = ServerSelectionTimeoutError("down")
        with mock.patch("assistant.mongo.get_db", return_value=fake_db), \
                self.assertLogs("gather.mongo", level="WARNING") as logs:
            response = self.chat("How do I reserve an item?")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.assertIn("MongoDB unavailable", logs.output[0])
        self.assertNotIn("example.invalid", logs.output[0])  # no connection details in logs
        self.assertEqual(self.client.get(reverse("faqs:list")).status_code, 200)

    def test_feedback_validation(self):
        with override_settings(OPENAI_API_KEY=""):
            mid = self.chat("How do I reserve an item?").json()["message_id"]
        post = lambda body: self.client.post(reverse("assistant:feedback"), json.dumps(body),
                                             content_type="application/json")
        self.assertEqual(post({"message_id": mid, "rating": 9}).status_code, 400)
        self.assertEqual(post({"message_id": mid, "rating": "5"}).status_code, 400)
        self.assertEqual(post({"message_id": mid, "rating": 4, "comment": "x" * 501}).status_code, 400)
        self.assertEqual(post({"message_id": "f" * 32, "rating": 4}).status_code, 400)
        # MongoDB not configured: accepted but reported as not stored.
        self.assertFalse(post({"message_id": mid, "rating": 4}).json()["stored"])


class SupportTicketTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_create_ticket_and_confirmation(self):
        response = self.client.post(reverse("support:support"), {
            "name": "Sam", "email": "sam@example.com", "category": "booking",
            "subject": "Change my dates", "description": "Please move booking BK-123456 by one day.",
            "status": "closed", "priority": "high",  # must be ignored
        })
        ticket = SupportTicket.objects.get()
        self.assertRedirects(response, reverse("support:submitted", args=[ticket.reference]))
        self.assertEqual((ticket.status, ticket.priority), ("open", "normal"))
        self.assertContains(self.client.get(response["Location"]), ticket.reference)

    def test_confirmation_not_visible_to_other_visitors(self):
        ticket = SupportTicket.objects.create(subject="Private", description="Private details here")
        response = Client().get(reverse("support:submitted", args=[ticket.reference]))
        self.assertRedirects(response, reverse("support:support"))

    def test_invalid_ticket_input(self):
        response = self.client.post(reverse("support:support"), {
            "category": "nonsense", "subject": "", "description": "short", "email": "not-an-email"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(SupportTicket.objects.count(), 0)
        self.assertContains(response, "is-invalid", status_code=400)

    @override_settings(TICKET_RATE_LIMIT=2)
    def test_ticket_rate_limit(self):
        data = {"category": "other", "subject": "Hello there", "description": "A long enough description."}
        codes = [self.client.post(reverse("support:support"), data).status_code for _ in range(3)]
        self.assertEqual(codes, [302, 302, 429])


class WeatherTests(TestCase):
    def setUp(self):
        cache.clear()

    @override_settings(OPENWEATHER_API_KEY="k")
    def test_success_is_cached(self):
        ok = mock.Mock(status_code=200)
        ok.json.return_value = {"name": "Paris", "sys": {"country": "FR"}, "main": {"temp": 21.4, "feels_like": 20,
                                "humidity": 50}, "wind": {"speed": 3.2}, "weather": [{"description": "clear sky", "icon": "01d"}]}
        with mock.patch("core.weather.requests.get", return_value=ok) as get:
            first, second = get_weather("Paris"), get_weather("Paris")
        self.assertEqual(get.call_count, 1)
        self.assertEqual(first["temp"], 21)
        self.assertEqual(second["city"], "Paris")
        self.assertEqual(get.call_args.kwargs["timeout"], (3.05, 5))

    @override_settings(OPENWEATHER_API_KEY="k")
    def test_timeout_and_errors_fall_back(self):
        with mock.patch("core.weather.requests.get", side_effect=requests.Timeout()):
            self.assertIn("timed out", get_weather("Paris")["message"])
        for status, text in [(429, "rate limit"), (404, "couldn't find"), (502, "temporarily unavailable")]:
            cache.clear()
            with mock.patch("core.weather.requests.get", return_value=mock.Mock(status_code=status)):
                result = get_weather("Paris")
            self.assertFalse(result["ok"])
            self.assertIn(text, result["message"])
        bad = mock.Mock(status_code=200)
        bad.json.return_value = {"unexpected": True}
        with mock.patch("core.weather.requests.get", return_value=bad):
            self.assertIn("unexpected response", get_weather("Paris")["message"])

    @override_settings(OPENWEATHER_API_KEY="k")
    def test_city_validation(self):
        with mock.patch("core.weather.requests.get") as get:
            self.assertFalse(get_weather("<script>")["ok"])
            self.assertFalse(get_weather("x" * 80)["ok"])
        get.assert_not_called()

    @override_settings(OPENWEATHER_API_KEY="")
    def test_missing_key(self):
        self.assertIn("not configured", get_weather("Paris")["message"])

    @override_settings(OPENWEATHER_API_KEY="super-secret-weather-key")
    def test_key_never_rendered(self):
        with mock.patch("core.weather.requests.get", side_effect=requests.Timeout()):
            response = self.client.get(reverse("core:home"))
        self.assertNotContains(response, "super-secret-weather-key")


class HealthTests(TestCase):
    def test_health_ok_without_mongo(self):
        with override_settings(MONGODB_URI=""):
            response = self.client.get(reverse("health"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "checks": {"app": "ok", "database": "ok",
                                                                        "mongodb": "not_configured"}})

    def test_health_degraded_when_mongo_down(self):
        with mock.patch("monitoring.views.mongo.ping", return_value=False):
            response = self.client.get(reverse("health"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "degraded")

    def test_health_503_when_database_down(self):
        with mock.patch("monitoring.views.connection.cursor", side_effect=DatabaseError("boom")):
            response = self.client.get(reverse("health"))
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["checks"]["database"], "unavailable")
        self.assertNotIn("boom", response.content.decode())


class ErrorHandlerTests(TestCase):
    def test_custom_404(self):
        response = self.client.get("/this-page-does-not-exist/")
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "We couldn't find that page", status_code=404)
        self.assertContains(response, 'data-context="error_404"', status_code=404)
        self.assertContains(response, "Ask the assistant", status_code=404)
        self.assertContains(response, "Return home", status_code=404)

    def test_custom_500(self):
        from django.urls import path

        from config import urls as root_urls

        def boom(request):
            raise RuntimeError("SECRET_DB_PASSWORD=hunter2")

        class TestUrls:
            urlpatterns = root_urls.urlpatterns + [path("boom/", boom)]
            handler404 = root_urls.handler404
            handler500 = root_urls.handler500

        client = Client(raise_request_exception=False)
        with override_settings(ROOT_URLCONF=TestUrls, DEBUG=False), \
                self.assertLogs("gather.requests", level="ERROR"):
            response = client.get("/boom/")
        self.assertEqual(response.status_code, 500)
        self.assertContains(response, "Something went wrong on our side", status_code=500)
        self.assertContains(response, 'data-context="error_500"', status_code=500)
        self.assertNotContains(response, "hunter2", status_code=500)
        self.assertNotContains(response, "Traceback", status_code=500)


class RequestLoggingTests(TestCase):
    def test_request_is_logged_without_query_string(self):
        with self.assertLogs("gather.requests", level="INFO") as logs:
            self.client.get("/faq/?q=secret-token-123")
        line = logs.output[-1]
        self.assertIn("method=GET path=/faq/ status=200 duration_ms=", line)
        self.assertNotIn("secret-token-123", line)

    def test_404_logged_as_warning(self):
        with self.assertLogs("gather.requests", level="WARNING") as logs:
            self.client.get("/nope/")
        self.assertIn("status=404", logs.output[0])


class SecurityConfigTests(TestCase):
    def run_check(self, env):
        clean_env = {k: v for k, v in os.environ.items()
                     if not k.startswith(("DJANGO_", "DATABASE_URL", "RENDER"))}
        clean_env.update(env)
        code = ("import django,os;os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings');"
                "django.setup();from django.conf import settings as s;"
                "print(s.DEBUG, s.SESSION_COOKIE_SECURE, s.CSRF_COOKIE_SECURE, s.SECURE_SSL_REDIRECT, "
                "s.DATABASES['default']['ENGINE'], s.SECURE_HSTS_SECONDS > 0)")
        return subprocess.run([sys.executable, "-c", code], cwd=BASE_DIR, env=clean_env,
                              capture_output=True, text=True, timeout=60)

    def test_production_requires_secret_key(self):
        result = self.run_check({"DJANGO_DEBUG": "False", "DATABASE_URL": "postgres://u:p@h:5432/d",
                                 "DJANGO_SECRET_KEY": ""})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("DJANGO_SECRET_KEY is not set", result.stderr)

    def test_production_requires_database_url(self):
        result = self.run_check({"DJANGO_DEBUG": "False", "DJANGO_SECRET_KEY": "x" * 50})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("DATABASE_URL is not set", result.stderr)

    def test_production_settings_are_secure(self):
        result = self.run_check({"DJANGO_DEBUG": "False", "DJANGO_SECRET_KEY": "x" * 50,
                                 "DATABASE_URL": "postgres://u:p@h:5432/d", "RENDER_EXTERNAL_HOSTNAME": "x.onrender.com"})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.split(), ["False", "True", "True", "True", "django.db.backends.postgresql", "True"])

    def test_admin_requires_login(self):
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])

    def test_env_file_is_gitignored_and_example_has_no_secrets(self):
        gitignore = (BASE_DIR / ".gitignore").read_text()
        self.assertIn(".env", gitignore.splitlines())
        example = (BASE_DIR / ".env.example").read_text()
        self.assertNotRegex(example, r"sk-[A-Za-z0-9]{20,}")
        self.assertIn("OPENAI_API_KEY=\n", example)

    def test_security_headers(self):
        response = self.client.get("/")
        self.assertEqual(response["X-Frame-Options"], "DENY")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
