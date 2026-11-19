from django.core.management.base import BaseCommand

from chores.services import sync_household
from households.models import Household


class Command(BaseCommand):
    help = "Close out finished weeks and generate this week's chore assignments for every household."

    def handle(self, *args, **options):
        count = 0
        for household in Household.objects.all():
            sync_household(household)
            count += 1
        self.stdout.write(self.style.SUCCESS(f"Rotated {count} household(s)."))
