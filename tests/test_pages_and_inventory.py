from datetime import timedelta
from io import StringIO
from unittest import mock

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from faqs.models import FAQ, ErrorCode
from inventory.models import Booking, Product


class SeededTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", verbosity=0, stdout=StringIO())
        cls.customer = User.objects.get(username="customer")
        cls.owner = User.objects.get(username="owner")
        cls.chair = Product.objects.get(slug="gold-chiavari-chair")
        cls.sofa = Product.objects.get(slug="velvet-lounge-sofa")


class PageTests(SeededTestCase):
    def test_main_pages_render_with_chat_widget(self):
        for name in ["core:home", "inventory:catalog", "faqs:list", "faqs:error_codes", "support:support"]:
            with self.subTest(page=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'id="chat-widget"')
                self.assertContains(response, "Gather")

    def test_product_detail_shows_image(self):
        response = self.client.get(self.chair.get_absolute_url())
        self.assertContains(response, "img/products/chiavari-chair")
        self.assertContains(response, "Sign in to reserve")

    def test_faq_page_reads_from_database(self):
        FAQ.objects.create(question="Do you deliver on Sundays?", answer="Only by arrangement.", category="general")
        response = self.client.get(reverse("faqs:list"))
        self.assertContains(response, "Do you deliver on Sundays?")
        FAQ.objects.filter(question="Do you deliver on Sundays?").update(is_active=False)
        self.assertNotContains(self.client.get(reverse("faqs:list")), "Do you deliver on Sundays?")

    def test_faq_search_and_category_filter(self):
        response = self.client.get(reverse("faqs:list"), {"q": "cancel"})
        self.assertContains(response, "Can I cancel or change a booking?")
        self.assertNotContains(response, "What does a 429 Too Many Requests error mean?")
        response = self.client.get(reverse("faqs:list"), {"category": "errors"})
        self.assertContains(response, "What does a 404 Not Found error mean?")
        self.assertNotContains(response, "Can I cancel or change a booking?")

    def test_error_code_page_lists_all_required_codes(self):
        response = self.client.get(reverse("faqs:error_codes"))
        for code in [400, 401, 403, 404, 429, 500, 503, 4600]:
            self.assertContains(response, f'id="code-{code}"')
        self.assertContains(response, "AI_ASSISTANT_UNAVAILABLE")
        self.assertContains(response, "not</em> an HTTP status")

    def test_error_code_search(self):
        response = self.client.get(reverse("faqs:error_codes"), {"q": "4600"})
        self.assertContains(response, 'id="code-4600"')
        self.assertNotContains(response, 'id="code-404"')


class SeedTests(TestCase):
    def test_seed_is_idempotent_and_has_enough_faqs(self):
        call_command("seed_demo", verbosity=0, stdout=mock.MagicMock())
        counts = (FAQ.objects.count(), ErrorCode.objects.count(), Product.objects.count(),
                  Booking.objects.count(), User.objects.count())
        call_command("seed_demo", verbosity=0, stdout=mock.MagicMock())
        call_command("seed_faqs", verbosity=0, stdout=mock.MagicMock())
        self.assertEqual(counts, (FAQ.objects.count(), ErrorCode.objects.count(), Product.objects.count(),
                                  Booking.objects.count(), User.objects.count()))
        self.assertGreaterEqual(FAQ.objects.filter(is_active=True).count(), 30)
        self.assertEqual(set(ErrorCode.objects.values_list("code", flat=True)),
                         {400, 401, 403, 404, 429, 500, 503, 4600})
        for ec in ErrorCode.objects.all():
            self.assertTrue(ec.meaning and ec.causes_list and ec.steps_list and ec.next_action)

    def test_every_product_has_an_image(self):
        call_command("seed_demo", verbosity=0, stdout=mock.MagicMock())
        for product in Product.objects.all():
            self.assertTrue(product.image_url.endswith(".svg"), product.name)


class BookingTests(SeededTestCase):
    def dates(self, start=40, end=41):
        today = timezone.localdate()
        return (today + timedelta(days=start)).isoformat(), (today + timedelta(days=end)).isoformat()

    def test_anonymous_user_redirected_to_login(self):
        start, end = self.dates()
        response = self.client.post(self.chair.get_absolute_url(), {"start_date": start, "end_date": end, "quantity": 1})
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response["Location"])
        self.assertFalse(Booking.objects.filter(start_date=start).exists())

    def test_customer_can_reserve_and_status_cannot_be_injected(self):
        self.client.force_login(self.customer)
        start, end = self.dates()
        response = self.client.post(self.chair.get_absolute_url(), {
            "start_date": start, "end_date": end, "quantity": 10, "status": "confirmed",
        })
        self.assertRedirects(response, reverse("inventory:my_bookings"))
        booking = Booking.objects.get(start_date=start, product=self.chair)
        self.assertEqual(booking.status, Booking.Status.PENDING)
        self.assertEqual(booking.customer, self.customer)
        self.assertTrue(booking.reference.startswith("BK-"))
        self.assertContains(self.client.get(reverse("inventory:my_bookings")), booking.reference)

    def test_cannot_overbook(self):
        self.client.force_login(self.customer)
        start, end = self.dates()
        self.client.post(self.sofa.get_absolute_url(), {"start_date": start, "end_date": end, "quantity": 3})
        response = self.client.post(self.sofa.get_absolute_url(), {"start_date": start, "end_date": end, "quantity": 2})
        self.assertContains(response, "Only 1 unit(s) available")
        self.assertEqual(self.sofa.available_quantity(*[timezone.datetime.fromisoformat(d).date() for d in (start, end)]), 1)

    def test_invalid_dates_rejected(self):
        self.client.force_login(self.customer)
        start, end = self.dates(10, 5)
        response = self.client.post(self.chair.get_absolute_url(), {"start_date": start, "end_date": end, "quantity": 1})
        self.assertContains(response, "end date must be on or after")
        past = (timezone.localdate() - timedelta(days=2)).isoformat()
        response = self.client.post(self.chair.get_absolute_url(), {"start_date": past, "end_date": past, "quantity": 1})
        self.assertContains(response, "cannot be in the past")

    def test_customer_can_cancel_own_booking_only(self):
        booking = Booking.objects.filter(customer=self.customer, status=Booking.Status.PENDING).first()
        jordan = User.objects.get(username="jordan")
        self.client.force_login(jordan)
        response = self.client.post(reverse("inventory:cancel_booking", args=[booking.reference]))
        self.assertEqual(response.status_code, 404)
        self.client.force_login(self.customer)
        self.client.post(reverse("inventory:cancel_booking", args=[booking.reference]))
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.CANCELLED)

    def test_catalog_availability_for_dates(self):
        confirmed = Booking.objects.get(product=self.chair, status=Booking.Status.CONFIRMED)
        response = self.client.get(reverse("inventory:catalog"), {
            "start": confirmed.start_date.isoformat(), "end": confirmed.end_date.isoformat(), "q": "chiavari"})
        self.assertContains(response, f"{self.chair.quantity_total - confirmed.quantity} available")


class OwnerTests(SeededTestCase):
    def test_customer_cannot_open_owner_dashboard(self):
        self.client.force_login(self.customer)
        self.assertEqual(self.client.get(reverse("inventory:owner_dashboard")).status_code, 403)
        self.client.logout()
        response = self.client.get(reverse("inventory:owner_dashboard"))
        self.assertEqual(response.status_code, 302)

    def test_owner_sees_and_confirms_bookings(self):
        self.client.force_login(self.owner)
        booking = Booking.objects.filter(status=Booking.Status.PENDING).first()
        response = self.client.get(reverse("inventory:owner_dashboard"))
        self.assertContains(response, booking.reference)
        self.client.post(reverse("inventory:owner_update_booking", args=[booking.reference]),
                         {"status": "confirmed", "owner_note": "See you there"})
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.CONFIRMED)
        # A disallowed transition (confirmed -> pending) is rejected.
        self.client.post(reverse("inventory:owner_update_booking", args=[booking.reference]), {"status": "pending"})
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.CONFIRMED)

    def test_owner_can_post_product_with_photo(self):
        from io import BytesIO

        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image

        buf = BytesIO()
        Image.new("RGB", (40, 30), "red").save(buf, "PNG")
        self.client.force_login(self.owner)
        response = self.client.post(reverse("inventory:owner_product_new"), {
            "name": "Photo Booth Kit", "category": self.chair.category_id, "description": "Props and backdrop.",
            "daily_rate": "75.00", "quantity_total": 2, "image_alt": "", "is_active": "on",
            "image": SimpleUploadedFile("booth.png", buf.getvalue(), content_type="image/png"),
        })
        self.assertRedirects(response, reverse("inventory:owner_products"))
        product = Product.objects.get(name="Photo Booth Kit")
        image = self.client.get(reverse("inventory:image", args=[product.slug]))
        self.assertEqual(image["Content-Type"], "image/png")
        self.assertContains(self.client.get(reverse("inventory:catalog")), "Photo Booth Kit")

    def test_non_image_upload_rejected(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        self.client.force_login(self.owner)
        response = self.client.post(reverse("inventory:owner_product_new"), {
            "name": "Bad", "category": self.chair.category_id, "description": "x", "daily_rate": "1",
            "quantity_total": 1, "image": SimpleUploadedFile("x.png", b"<svg onload=alert(1)>", content_type="image/png"),
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Product.objects.filter(name="Bad").exists())


class SignupTests(TestCase):
    def test_signup_creates_customer_and_logs_in(self):
        response = self.client.post(reverse("signup"), {
            "username": "newguest", "first_name": "New", "email": "new@example.com",
            "password1": "A-strong-pass-123", "password2": "A-strong-pass-123",
        })
        self.assertRedirects(response, reverse("inventory:catalog"))
        user = User.objects.get(username="newguest")
        self.assertFalse(user.is_staff)


@override_settings(OPENWEATHER_API_KEY="")
class HomeWithoutWeatherKey(TestCase):
    def test_friendly_weather_message(self):
        response = self.client.get(reverse("core:home"))
        self.assertContains(response, "Live weather is temporarily unavailable")
