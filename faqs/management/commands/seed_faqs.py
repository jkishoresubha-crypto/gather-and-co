from django.core.management.base import BaseCommand
from django.db import transaction

from faqs.models import FAQ, ErrorCode
from faqs.seed_data import ERROR_CODES, FAQS


class Command(BaseCommand):
    help = "Create or update the seed FAQs and error-code reference. Safe to run repeatedly."

    @transaction.atomic
    def handle(self, *args, **options):
        created = updated = 0
        for item in FAQS:
            _, was_created = FAQ.objects.update_or_create(
                question=item["question"],
                defaults={
                    "answer": item["answer"],
                    "category": item["category"],
                    "keywords": item.get("keywords", ""),
                    "is_active": True,
                },
            )
            created += was_created
            updated += not was_created

        for item in ERROR_CODES:
            ErrorCode.objects.update_or_create(code=item["code"], defaults={k: v for k, v in item.items() if k != "code"})

        self.stdout.write(self.style.SUCCESS(
            f"FAQs: {created} created, {updated} updated. Error codes: {len(ERROR_CODES)} ensured."
        ))
