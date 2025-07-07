import datetime
import logging

from ..bot.models import Reminder, Task
from ..bot.handlers.common import send_reminders

def check_reminders():
    print('start_checking')
    send_reminders()
    # Очищаем завершенные напоминания каждые 10 циклов (примерно раз в 10 минут)
    if hasattr(check_reminders, 'cleanup_counter'):
        check_reminders.cleanup_counter += 1
    else:
        check_reminders.cleanup_counter = 1
        
    if check_reminders.cleanup_counter >= 10:
        try:
            Reminder.objects.filter(reminder_time__lte=datetime.datetime.now())
            check_reminders.cleanup_counter = 0
        except Exception as e:
            logging.error(f"Error cleaning up reminders: {e}")

if __name__ == '__main__':
    check_reminders()