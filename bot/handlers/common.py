import datetime
import logging

from django.db.models import Q
from django.utils import timezone
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from telebot import TeleBot

from bot import bot
from ..models import Reminder, Task

def send_reminders():
    pre_reminders = Reminder.objects.filter(reminder_time__lte=timezone.now(), is_pre_reminder_sent=False) | \
                    Reminder.objects.filter(~Q(repeat_type=None), ~Q(repeat_time=None), repeat_time__lte=timezone.now() - datetime.timedelta(minutes=15), is_pre_reminder_sent=False)
    
    pre_tasks = Task.objects.filter(reminder_time__lte=timezone.now(), is_pre_reminder_sent=False) | \
                Task.objects.filter(~Q(repeat_type=None), ~Q(repeat_time=None), repeat_time__lte=timezone.now() - datetime.timedelta(minutes=15), is_pre_reminder_sent=False)
    
    reminders = Reminder.objects.filter(reminder_time__lte=timezone.now(), is_main_reminder_sent=False) | \
                Reminder.objects.filter(~Q(repeat_type=None), ~Q(repeat_time=None), repeat_time__lte=timezone.now(), is_main_reminder_sent=False)
    
    tasks = Task.objects.filter(reminder_time__lte=timezone.now(), is_completed=False) | \
            Task.objects.filter(~Q(repeat_type=None), ~Q(repeat_time=None), repeat_time__lte=timezone.now(), is_main_reminder_sent=False, is_completed=False) | \
            Task.objects.filter(transfer_time__lte=timezone.now(), is_transfered=True, is_completed=False)
    
    try:
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

        for task in pre_tasks:
            repeat_info = ""
            if not task.repeat_type is None:
                if task.repeat_type == 'daily':
                    repeat_info = " 🔄 (повторится завтра)"
                elif task.repeat_type == 'weekly':
                    repeat_info = " 🔄 (повторится через неделю)"

            bot.send_message(
                chat_id=task.user.user_id,
                text=f"⏰ Предварительное напоминание для задачи (через 15 минут)!{repeat_info}\n"
                f"📝 {task.text}"
            )
            task.is_pre_reminder_sent = True
            task.save()
        
        for task in tasks:
            kb = [
                InlineKeyboardButton(text="✅ Завершить!", callback_data=f"t.finish|{task.id}"),
                InlineKeyboardButton(text="⏳ Отложить", callback_data=f"t.put_off|{task.id}"),
                InlineKeyboardButton(text="❌ Удалить", callback_data=f"t.remove|{task.id}")
            ]
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton(text="✅ Завершить!", callback_data=f"t.finish|{task.id}"))
            markup.add(InlineKeyboardButton(text="⏳ Отложить", callback_data=f"t.put_off|{task.id}"))
            markup.add(InlineKeyboardButton(text="❌ Удалить", callback_data=f"t.remove|{task.id}"))
            
            repeat_info = ""
            if not task.repeat_type is None:
                if task.repeat_type == 'daily':
                    repeat_info = " 🔄 (повторится завтра)"
                elif task.repeat_type == 'weekly':
                    repeat_info = " 🔄 (повторится через неделю)"

            bot.send_message(
                chat_id=task.user.user_id,
                text=f"🔔 Время пришло!{repeat_info}\n"
                f"📝 {task.text}",
                reply_markup=markup
            )

            task.is_main_reminder_sent = True
            task.save()


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


def task_sets(call: CallbackQuery, bot: TeleBot):
    print(call.data)
    task_data = call.data.split('.')[1].split('|')
    
    if task_data[0] == 'finish':
        try: 
            bot.answer_callback_query(callback_query_id=call.id)
            bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
            task = Task.objects.get(id=task_data[1])
            task.is_completed = True
            task.save()
            bot.send_message(
                text='Отлично!'
                f'\nЗадача "{task.text}" завершена! ✅',
                chat_id=call.message.chat.id
                )
        except Exception as e:
            bot.send_message(
                text='Возникла ошибка, приносим свои извинения и уже работаем над исправлением',
                chat_id=call.message.chat.id
            )
            print(e)

    if task_data[0] == 'put_off':
        try: 
            bot.answer_callback_query(callback_query_id=call.id)
            bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
            task = Task.objects.get(id=task_data[1])
            offset = datetime.timedelta(hours=int(task.user.timezone[1:]))
            custom_tz = timezone.get_fixed_timezone(offset)
            transfer_time = task.reminder_time.astimezone(custom_tz) + datetime.timedelta(minutes=30)
            task.is_transfered = True
            task.transfer_time = transfer_time
            task.save()
            bot.send_message(
                text='Задача перенесена на полчаса.'
                f'\nСледующее напоминание будет в {transfer_time}',
                chat_id=call.message.chat.id
                )
        except Exception as e:
            bot.send_message(
                text='Возникла ошибка, приносим свои извинения и уже работаем над исправлением',
                chat_id=call.message.chat.id
            )
            print(e)

    if task_data[0] == 'remove':
        try: 
            bot.answer_callback_query(callback_query_id=call.id)
            bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
            task = Task.objects.get(id=task_data[1])
            bot.send_message(
                text=f'\nЗадача "{task.text}" была удалена! ✅',
                chat_id=call.message.chat.id
                )
            task.delete()
        except Exception as e:
            bot.send_message(
                text='Возникла ошибка, приносим свои извинения и уже работаем над исправлением',
                chat_id=call.message.chat.id
            )
            print(e)
    