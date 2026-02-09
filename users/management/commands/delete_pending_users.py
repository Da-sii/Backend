from django.core.management import BaseCommand
from django.utils import timezone
from datetime import timedelta
from users.models import User

class Command(BaseCommand):
    help = "약관 미동의 24시간 경과 유저 삭제"

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(hours=24)

        delete_count, _ = User.objects.filter(
            is_terms_agreed = False,
            created_at__lt = cutoff,
        ).delete()

        self.stdout.write(
            self.style.SUCCESS(f"Deleted {delete_count} users")
        )
