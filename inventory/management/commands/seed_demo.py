"""Seed demo inventory, demo accounts and sample bookings (idempotent)."""
import os
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from inventory.models import Booking, Category, Product

CATEGORIES = [
    ("Seating", "seating", "Chairs and lounge furniture for every guest."),
    ("Tables", "tables", "Banquet, farmhouse and cocktail tables."),
    ("Tents & Canopies", "tents-canopies", "Weather cover for outdoor events."),
    ("Lighting", "lighting", "Festoon lights and uplighting for atmosphere."),
    ("Tableware", "tableware", "Dinnerware and glassware sets."),
    ("Décor", "decor", "Statement pieces and backdrops."),
]

# (category slug, name, slug, daily rate, quantity, image file, description)
PRODUCTS = [
    ("seating", "Gold Chiavari Chair", "gold-chiavari-chair", "4.50", 120, "chiavari-chair.svg",
     "Elegant gold-finish Chiavari chair with an ivory seat cushion. Lightweight, stackable and perfect for weddings and galas."),
    ("seating", "White Folding Chair", "white-folding-chair", "2.00", 200, "folding-chair.svg",
     "Sturdy white resin folding chair for ceremonies, conferences and garden parties. Weather resistant."),
    ("seating", "Velvet Lounge Sofa", "velvet-lounge-sofa", "85.00", 4, "velvet-sofa.svg",
     "Three-seat emerald velvet sofa with brass legs. Creates a stylish lounge area for receptions."),
    ("tables", "Round Banquet Table (6 ft)", "round-banquet-table", "12.00", 30, "round-banquet-table.svg",
     "Seats 8–10 guests. Supplied with a floor-length white linen cloth."),
    ("tables", "Rustic Farmhouse Table", "rustic-farmhouse-table", "45.00", 10, "farmhouse-table.svg",
     "Solid reclaimed-wood table, 8 ft long, seats 8. Beautiful without a tablecloth."),
    ("tables", "Cocktail High-Top Table", "cocktail-high-top-table", "15.00", 20, "cocktail-table.svg",
     "Bar-height standing table with a white stretch spandex cover. Ideal for mingling."),
    ("tents-canopies", "Frame Tent 20×30 ft", "frame-tent-20x30", "450.00", 3, "frame-tent.svg",
     "Free-standing white frame marquee covering 600 sq ft. Seats up to 60 guests. Side walls included."),
    ("tents-canopies", "Pop-up Canopy 10×10 ft", "popup-canopy-10x10", "60.00", 8, "popup-canopy.svg",
     "Quick-setup canopy for vendor stalls, catering stations and garden shade."),
    ("lighting", "Festoon String Lights (50 ft)", "festoon-string-lights", "18.00", 25, "festoon-lights.svg",
     "Warm-white LED festoon lights on a 50 ft weatherproof cable. Connect up to 5 runs."),
    ("lighting", "LED Uplighter", "led-uplighter", "12.00", 40, "led-uplighter.svg",
     "Battery-powered RGB uplighter with remote control. Wash walls and tents in any colour."),
    ("tableware", "Porcelain Dinner Set (10 guests)", "porcelain-dinner-set", "25.00", 30, "dinner-set.svg",
     "Gold-rimmed dinner plates, side plates and cutlery for ten guests. Returned unwashed."),
    ("tableware", "Crystal Glassware Set (10 guests)", "crystal-glassware-set", "20.00", 30, "glassware-set.svg",
     "Red wine, white wine and champagne glasses for ten guests, delivered in protective crates."),
    ("decor", "Brass Candelabra", "brass-candelabra", "10.00", 24, "brass-candelabra.svg",
     "Five-arm brass candelabra for long tables. LED taper candles included."),
    ("decor", "Floral Arch Backdrop", "floral-arch-backdrop", "120.00", 2, "floral-arch.svg",
     "Gold metal arch dressed with faux blush roses and greenery. A favourite ceremony backdrop."),
]

DEMO_OWNER = ("owner", "owner@gatherco.example", "Olivia", "Owner")
DEMO_CUSTOMERS = [
    ("customer", "customer@gatherco.example", "Casey", "Customer"),
    ("jordan", "jordan@gatherco.example", "Jordan", "Lee"),
]


class Command(BaseCommand):
    help = "Seed FAQs, demo inventory, demo owner/customer accounts and sample bookings. Safe to rerun."

    def handle(self, *args, **options):
        call_command("seed_faqs", stdout=self.stdout)
        with transaction.atomic():
            self.seed_inventory()
            owner, customers = self.seed_accounts()
            self.seed_bookings(customers)
        self.stdout.write(self.style.SUCCESS("Demo data ready."))

    def seed_inventory(self):
        cats = {}
        for name, slug, desc in CATEGORIES:
            cats[slug], _ = Category.objects.update_or_create(slug=slug, defaults={"name": name, "description": desc})
        for cat, name, slug, rate, qty, image, desc in PRODUCTS:
            product, created = Product.objects.get_or_create(
                slug=slug,
                defaults={
                    "category": cats[cat], "name": name, "daily_rate": Decimal(rate),
                    "quantity_total": qty, "description": desc,
                    "static_image": f"img/products/{image}", "image_alt": name,
                },
            )
            # Keep the illustration reference fresh without overwriting owner edits.
            if not created and not product.static_image:
                product.static_image = f"img/products/{image}"
                product.save(update_fields=["static_image"])
        self.stdout.write(f"Inventory: {len(CATEGORIES)} categories, {len(PRODUCTS)} products ensured.")

    def seed_accounts(self):
        User = get_user_model()
        owner_password = os.environ.get("DEMO_OWNER_PASSWORD", "GatherOwner#2026")
        customer_password = os.environ.get("DEMO_CUSTOMER_PASSWORD", "GatherGuest#2026")
        owners_group, _ = Group.objects.get_or_create(name="Owners")

        username, email, first, last = DEMO_OWNER
        owner, created = User.objects.get_or_create(
            username=username, defaults={"email": email, "first_name": first, "last_name": last}
        )
        owner.is_staff = True
        owner.is_superuser = True
        if created:
            owner.set_password(owner_password)
        owner.save()
        owner.groups.add(owners_group)

        customers = []
        for username, email, first, last in DEMO_CUSTOMERS:
            user, created = User.objects.get_or_create(
                username=username, defaults={"email": email, "first_name": first, "last_name": last}
            )
            if created:
                user.set_password(customer_password)
                user.save()
            customers.append(user)
        self.stdout.write("Accounts: owner + 2 demo customers ensured (existing passwords are not changed).")
        return owner, customers

    def seed_bookings(self, customers):
        if Booking.objects.exists():
            self.stdout.write("Bookings already exist; sample bookings skipped.")
            return
        today = timezone.localdate()
        samples = [
            (customers[0], "gold-chiavari-chair", 60, 10, 11, Booking.Status.CONFIRMED, "Garden wedding, 60 guests"),
            (customers[0], "round-banquet-table", 6, 10, 11, Booking.Status.CONFIRMED, "Garden wedding tables"),
            (customers[0], "festoon-string-lights", 4, 10, 11, Booking.Status.PENDING, "Lights over the dance floor"),
            (customers[1], "frame-tent-20x30", 1, 21, 23, Booking.Status.PENDING, "Company summer party"),
            (customers[1], "cocktail-high-top-table", 8, 21, 23, Booking.Status.PENDING, "Company summer party"),
            (customers[1], "velvet-lounge-sofa", 2, -20, -19, Booking.Status.COMPLETED, "Birthday lounge"),
        ]
        for user, slug, qty, start, end, status, note in samples:
            Booking.objects.create(
                customer=user, product=Product.objects.get(slug=slug), quantity=qty,
                start_date=today + timedelta(days=start), end_date=today + timedelta(days=end),
                status=status, event_note=note,
            )
        self.stdout.write(f"Bookings: {len(samples)} sample bookings created.")
