from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from users.models import PhoneVerification


class Command(BaseCommand):
    help = '만료된 전화번호 인증 레코드 삭제'

    def handle(self, *args, **options):
        expired_time = timezone.now() - timedelta(minutes=5)

        deleted_count, _ = PhoneVerification.objects.filter(
            sent_at__lt=expired_time
        ).delete()

        self.stdout.write(
            self.style.SUCCESS(f'만료된 인증 레코드 {deleted_count}개 삭제 완료')
        )