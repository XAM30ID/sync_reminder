import datetime
import logging

from django.db.models import Q
from django.utils import timezone

from bot import bot
from ..models import Reminder

def send_reminders():
    pre_reminders = Reminder.objects.filter(reminder_time__gte=timezone.now(), is_pre_reminder_sent=False) | \
                    Reminder.objects.filter(~Q(repeat_type=None), ~Q(repeat_time=None), repeat_time__lte=timezone.now() - datetime.timedelta(minutes=15), is_pre_reminder_sent=False)
    
    reminders = Reminder.objects.filter(reminder_time__lte=timezone.now(), is_main_reminder_sent=False) | \
                    Reminder.objects.filter(~Q(repeat_type=None), ~Q(repeat_time=None), repeat_time__lte=timezone.now(), is_main_reminder_sent=False)
    try:
        with open('all_reminders.txt', 'a', encoding='utf-8') as f:
            f.write('ПРЕДВАРИТЕЛЬНЫЕ НАПОМИНАНИЯ')
    # Отправляем предварительные напоминания
        for pre_reminder in pre_reminders:
            repeat_info = ""
            if not pre_reminder.repeat_type is None:
                if pre_reminder.repeat_type == 'daily':
                    repeat_info = " 🔄"
                elif pre_reminder.repeat_type == 'weekly':
                    repeat_info = " 🔄"

            bot.send_message(
                chat_id=pre_reminder.user.user_id,
                text=f"⏰ Предварительное напоминание (через 15 минут)!{repeat_info}\n"
                f"📝 {pre_reminder.text}"
            )
            with open('all_reminders.txt', 'a', encoding='utf-8') as f:
                f.write('\nПредварительное напоминание: ' + str(pre_reminder.text) + str(pre_reminder.repeat_type))
                f.write('\nПользователь: ' + str(pre_reminder.user.user_id))

            pre_reminder.is_pre_reminder_sent = True
            pre_reminder.save()
        
        for reminder in reminders:
            repeat_info = ""
            if not reminder.repeat_type is None:
                if reminder.repeat_type == 'daily':
                    repeat_info = " 🔄 (повторится завтра)"
                elif reminder.repeat_type == 'weekly':
                    repeat_info = " 🔄 (повторится через неделю)"
            
            bot.send_message(
                chat_id=reminder.user.user_id,
                text=f"🔔 Время пришло!{repeat_info}\n"
                f"📝 {reminder.text}"
            )

            reminder.is_main_reminder_sent = True
            reminder.save()

    except Exception as e:
        logging.error(f"Error checking reminders: {e}")
        with open('all_reminders.txt', 'a', encoding='utf-8') as f:
            f.write('\nОШИБКА: ' + str(e))
    

def clear_reminders():
    try:
        to_delete = Reminder.objects.filter(reminder_time__lte=datetime.datetime.now())
        with open('delete_log.txt', 'a', encoding='utf-8') as f:
            f.write('\nУдалено: ' + str(to_delete.count))

        to_delete.delete()

    except Exception as e:
        with open('delete_log.txt', 'a', encoding='utf-8') as f:
            f.write('\n\n' + e)