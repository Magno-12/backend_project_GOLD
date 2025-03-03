from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.lottery.models import Lottery


class Command(BaseCommand):
    help = 'Restablecer fechas de sorteo de lotería cuando la fecha de sorteo actual ha pasado'

    def handle(self, *args, **options):
        current_date = timezone.now().date()

        # Obtener loterías con fecha de sorteo en el pasado
        outdated_lotteries = Lottery.objects.filter(
            next_draw_date__lt=current_date,
            is_active=True
        )
        count = 0
        for lottery in outdated_lotteries:
            lottery.update_next_draw_date()
            count += 1

        self.stdout.write(self.style.SUCCESS(f'Actualizadas {count} loterías con nuevas fechas de sorteo'))
