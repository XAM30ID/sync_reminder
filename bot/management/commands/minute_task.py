import logging
from django.core.management.base import BaseCommand
from django.utils import timezone

from bot.handlers.common import send_reminders, clear_reminders

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Отправляет ежедневные отчеты всем пользователям и сбрасывает дневные расходы'

    def handle(self, *args, **kwargs):
        with open('checking_log.txt', 'a', encoding='utf-8') as f:
            f.write('\n' + '=' * 10 + 'Начало' + '=' * 10)
        try:
            send_reminders()
            with open('checking_log.txt', 'a', encoding='utf-8') as f:
                f.write('\n✅Успех при отправке')
        except Exception as e:
            with open('checking_log.txt', 'a', encoding='utf-8') as f:
                f.write(f'\n❌Ошибка при отправке: {e}')
        # Очищаем завершенные напоминания каждые 10 циклов (примерно раз в 10 минут)
        try:
            with open('checking_log.txt', 'a', encoding='utf-8') as f:
                    f.write(str(timezone.now().minute % 10) + f'\n{timezone.now().minute}' + '\n\n')
            if timezone.now().minute % 10 == 0:
                clear_reminders()
                with open('checking_log.txt', 'a', encoding='utf-8') as f:
                    f.write('\n✅Успех при чистке')
        except Exception as e:
            with open('checking_log.txt', 'a', encoding='utf-8') as f:
                f.write(f'\n❌Ошибка при чистке: {e}')

        with open('checking_log.txt', 'a', encoding='utf-8') as f:
            f.write('\nКонец\n' + '=' * 30)