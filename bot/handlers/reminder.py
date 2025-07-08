import os
import re
import time
from datetime import datetime, timedelta

from telebot.apihelper import ApiTelegramException
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, Message, InputMediaPhoto, User
from telebot import TeleBot

from django.utils import timezone

from config import AI_MODEL
from .ai import OpenAIAPI
from ..services.parser import parse_reminder_time, parse_date_query
from ..services.voice import convert_ogg_to_wav, transcribe_audio
from ..utils.timezone import format_moscow_time
from ..models import Reminder, Task, UserProfile

from bot import bot, logger

AI = OpenAIAPI()

# Словарь для хранения состояния удаления напоминаний
user_delete_context = {}


def reminder_button(message: Message, bot: TeleBot):
    bot.send_chat_action(chat_id=message.chat.id, action="typing")
    bot.send_message(
        chat_id=message.chat.id,
        text="🤖 Теперь я могу понимать ваши запросы! \n\n"
        "Просто напишите или скажите мне, что вы хотите:\n\n"
        "✅ Для создания напоминаний:\n"
        "• 'Напомни мне завтра в 10 утра купить хлеб'\n"
        "• 'Поставь напоминание на понедельник в 15:30 встреча'\n"
        "• 'Мне нужно каждый день в 22:00 принимать витамины'\n"
        "• 'Завтра погулять с собакой'\n"
        "• 'Через 2 часа позвонить маме'\n\n"
        "❌ Для удаления напоминаний:\n"
        "• 'Удали напоминание про кота'\n"
        "• 'Убери напоминание о встрече'\n"
        "• 'Отмени напоминание принимать витамины'\n"
        "• 'Удали все напоминания про врача'\n\n"
        "💬 Для обычного общения:\n"
        "• 'Привет, как дела?'\n"
        "• 'Что ты умеешь?'\n"
        "• 'Расскажи что-нибудь интересное'\n\n"
        "Я сама пойму, хотите ли вы создать, удалить напоминание или просто пообщаться!"
    )


def list_reminders(message: Message, bot: TeleBot):
    bot.send_chat_action(chat_id=message.chat.id, action="typing")
    reminders = Reminder.objects.filter(user_id=message.from_user.id)
    if not reminders:
        bot.send_message(
            chat_id=message.chat.id,
            text="📋 У вас пока нет активных напоминаний.\n\n"
            "💡 Создайте новое напоминание, написав мне что-то вроде:\n"
            "• 'Напомни завтра в 10 утра купить хлеб'\n"
            "• 'Каждый день в 22:00 принимать витамины'\n"
            "• 'В понедельник в 15:30 встреча'"
        )
        return
    
    # Группируем напоминания по типу
    one_time_reminders = reminders.filter(repeat_type=None)
    recurring_reminders = reminders.exclude(repeat_type=None)
    
    
    # Формируем красивое сообщение
    message_parts = ["📋 **Ваши напоминания:**\n"]
    
    # Одноразовые напоминания
    if one_time_reminders:
        message_parts.append("📅 **Разовые напоминания:**")
        for i, reminder in enumerate(one_time_reminders, 1):
            # Убираем информацию о часовом поясе
            offset = timedelta(hours=int(reminder.user.timezone[1:]))
            custom_tz = timezone.get_fixed_timezone(offset)
            reminder_time = reminder.reminder_time.astimezone(custom_tz)
            current_time = datetime.now(custom_tz)
            
            # Определяем статус
            if reminder_time > current_time:
                status_icon = "⏳"
                time_until = reminder_time - current_time
                if time_until.days > 0:
                    time_info = f"через {time_until.days} дн."
                elif time_until.seconds > 3600:
                    hours = time_until.seconds // 3600
                    time_info = f"через {hours} ч."
                else:
                    minutes = time_until.seconds // 60
                    time_info = f"через {minutes} мин."
            else:
                status_icon = "🔔"
                time_info = "скоро"
            
            message_parts.append(
                f"{status_icon} **{reminder.text}**\n"
                f"   🕐 {format_moscow_time(reminder_time)} ({time_info})\n"
            )
    # Повторяющиеся напоминания
    if recurring_reminders:
        if one_time_reminders:
            message_parts.append("")  # Пустая строка для разделения
        
        message_parts.append("🔄 **Повторяющиеся напоминания:**")
        for reminder in recurring_reminders:
            reminder_time = datetime.fromisoformat(reminder.reminder_time)
            
            if reminder.repeat_type == 'daily':
                repeat_text = "каждый день"
                next_time = reminder_time.strftime("%H:%M")

            elif reminder.repeat_type == 'weekly':
                repeat_text = "каждую неделю"
                weekdays = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
                weekday = weekdays[reminder_time.weekday()]
                next_time = f"{weekday} в {reminder_time.strftime('%H:%M')}"

            else:
                repeat_text = "периодически"
                next_time = format_moscow_time(reminder_time)
            
            message_parts.append(
                f"🔄 **{reminder.text}** ({repeat_text})\n"
                f"   🕐 Следующее: {next_time}\n"
            )
    
    # Добавляем информационное сообщение
    message_parts.append(
        "\n💡 **Информация:**\n"
        "• Разовые напоминания удаляются автоматически после выполнения\n"
        "• Повторяющиеся напоминания работают по расписанию\n"
        "• Вы получите уведомление за 15 минут до события"
    )
    
    # Отправляем одним сообщением
    full_message = "\n".join(message_parts)
    print(full_message)
    bot.send_message(chat_id=message.chat.id, text=full_message, parse_mode="Markdown")


def handle_voice(message: Message, bot: TeleBot):
    """Обработка голосовых сообщений"""
    bot.send_chat_action(chat_id=message.chat.id, action="typing")
    try:
        # Скачиваем голосовое сообщение
        file = bot.get_file(message.voice.file_id)
        file_path = f"voice_{message.from_user.id}_{message.message_id}.ogg"
        downloaded = bot.download_file(file.file_path)
        with open(file_path, 'wb') as f:
            f.write(downloaded)
        
        # Распознаем текст
        text = transcribe_audio(file_path)
        
        if not text:
            bot.send_message(chat_id=message.chat.id, text="Извините, не удалось распознать голосовое сообщение. Попробуйте еще раз.")
            return
        
        addressing = None
        tone = None
        user_info = UserProfile.objects.get(user_id=message.from_user.id)
        if user_info.pk:
            utc_info = user_info.timezone
            addressing = user_info.addressing
            tone = user_info.tone
        # Получаем ответ от ИИ
        ai_response = AI.get_response(
            chat_id=message.from_user.id, 
            text=text, 
            model=AI_MODEL, 
            max_token=3000,
            tone=tone,
            addressing=addressing
        )
        
        if not ai_response or not ai_response.get('message'):
            bot.send_message(chat_id=message.chat.id, text="Извините, произошла ошибка при обработке сообщения.")
            return
        
        # Парсим ответ ИИ
        parsed_response = AI.parse_ai_response(ai_response['message'])
        
        if parsed_response['type'] == 'reminder':
            # ИИ определила, что нужно создать напоминание
            create_reminder_from_ai(message, parsed_response, bot)
        elif parsed_response['type'] == 'delete':
            # ИИ определила, что нужно удалить напоминание
            handle_delete_reminder_from_ai(message, parsed_response, bot)
        else:
            # Обычное общение
            bot.send_message(chat_id=message.chat.id, text=parsed_response['message'])
        
    except Exception as e:
        print(f"Error processing voice message: {e}")
        bot.send_message(chat_id=message.chat.id, text="Произошла ошибка при обработке голосового сообщения. Попробуйте еще раз.")


# ПОД ВОПРОСОМ
def handle_text(message: Message, bot: TeleBot):
    """Обработка текстовых сообщений через ИИ"""
    if message.text.startswith('/'):  # Пропускаем команды
        return
    
    user_id = message.from_user.id
    user_text = message.text.lower().strip()
    
    # Проверяем, есть ли у пользователя сохраненный контекст удаления
    if user_id in user_delete_context:
        context = user_delete_context[user_id]
        
        if user_text in ['удали все', 'удалить все']:
            # Удаляем все найденные напоминания
            reminder_ids = [r['id'] for r in context['reminders']]
            Reminder.objects.filter(id__in=reminder_ids).delete()
            
            # Очищаем контекст
            del user_delete_context[user_id]
            
            bot.send_message(
                chat_id=message.chat.id,
                text=f"✅ Удалено {len(reminder_ids)} напоминаний по запросу '{context['search_text']}'"
            )
            return
        
        elif user_text in ['удали первое', 'удалить первое', 'первое']:
            # Удаляем первое напоминание из списка
            first_reminder = context['reminders'][0]
            Reminder.objects.get(id=first_reminder['id']).delete()
            
            # Очищаем контекст
            del user_delete_context[user_id]
            
            bot.send_message(
                chat_id=message.chat.id,
                text=f"✅ Удалено напоминание: **{first_reminder['text']}**",
                parse_mode="Markdown"
            )
            return
        
        elif user_text in ['отмена', 'отменить']:
            # Отменяем удаление
            del user_delete_context[user_id]
            bot.send_message(chat_id=message.chat.id, text="❌ Удаление отменено")
            return
        
        elif user_text.startswith('удали ') and user_text[6:].isdigit():
            # Удаляем напоминание по номеру (например, "удали 3")
            try:
                index = int(user_text[6:]) - 1  # -1 потому что нумерация с 1
                if 0 <= index < len(context['reminders']):
                    reminder_to_delete = context['reminders'][index]['id']
                    Reminder.objects.get(id=reminder_to_delete).delete()
                    # Очищаем контекст
                    del user_delete_context[user_id]
                    
                    bot.send_message(
                        chat_id=message.chat.id,
                        text=f"✅ Удалено напоминание: **{reminder_to_delete['text']}**",
                        parse_mode="Markdown"
                    )
                    return
                else:
                    bot.send_message(chat_id=message.chat.id, text=f"❌ Неверный номер. Выберите от 1 до {len(context['reminders'])}")
                    return
            except:
                pass
    
    bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    addressing = None
    tone = None
    user_info = UserProfile.objects.get(user_id=message.from_user.id)
    if user_info.pk:
        addressing = user_info.addressing
        tone = user_info.tone
    # Получаем ответ от ИИ
    ai_response = AI.get_response(
        chat_id=message.from_user.id, 
        text=message.text, 
        model=AI_MODEL, 
        max_token=3000,
        tone=tone,
        addressing=addressing
    )
    
    if not ai_response or not ai_response.get('message'):
        bot.send_message(chat_id=message.chat_id, text="Извините, произошла ошибка при обработке сообщения.")
        return
    
    # Парсим ответ ИИ   
    parsed_response = AI.parse_ai_response(ai_response['message'])
    if parsed_response['type'] == 'reminder':
        # ИИ определила, что нужно создать напоминание
        create_reminder_from_ai(message, parsed_response, bot)
    elif parsed_response['type'] == 'delete':
        # ИИ определила, что нужно удалить напоминание
        handle_delete_reminder_from_ai(message, parsed_response)
    else:
        # Обычное общение
        bot.send_message(chat_id=message.chat.id, text=parsed_response['message'])

def create_reminder_from_ai(message: Message, ai_data: dict, bot: TeleBot):
    """
    Создает напоминание на основе данных от ИИ
    """
    try:
        # ОТЛАДКА: выводим что получили от ИИ
        print(f"=== ОТЛАДКА ИИ ===")
        print(f"reminder_text: '{ai_data.get('reminder_text', '')}'")
        print(f"time_text: '{ai_data.get('time_text', '')}'")
        print(f"Исходное сообщение пользователя: '{message.text}'")
        print("==================")
        
        # Используем данные от ИИ напрямую
        reminder_text = ai_data.get('reminder_text', '').strip()
        time_text = ai_data.get('time_text', '').strip()
        
        print(f"=== ПОСЛЕ ОБРАБОТКИ ===")
        print(f"reminder_text после strip: '{reminder_text}'")
        print(f"time_text после strip: '{time_text}'")
        print("======================")
        
        if not reminder_text:
            bot.send_message(chat_id=message.chat.id, text="Не удалось определить текст напоминания. Попробуйте еще раз.")
            return False
        
        if not time_text:
            bot.send_message(
                chat_id=message.chat.id,
                text=f"Конечно! Я помогу создать напоминание: {reminder_text}\n\n"
                "⏰ Когда вам напомнить? Укажите время, например:\n"
                "• 'завтра в 10 утра'\n"
                "• 'в понедельник в 15:30'\n"
                "• 'каждый день в 22:00'\n"
                "• 'через 2 часа'"
            )
            return False
        
        # Парсим время, используя улучшенный парсер
        reminder_time, pre_reminder_time, parsed_text, repeat_type = parse_reminder_time(time_text)
        
        print(f"=== РЕЗУЛЬТАТ ПАРСЕРА ===")
        print(f"reminder_time: {reminder_time}")
        print(f"pre_reminder_time: {pre_reminder_time}")
        print(f"parsed_text: '{parsed_text}'")
        print(f"repeat_type: {repeat_type}")
        print("========================")
        
        if not reminder_time:
            bot.send_message(
                chat_id=message.chat.id,
                text=f"Не удалось определить время напоминания из фразы: '{time_text}'\n\n"
                "Пожалуйста, укажите время более точно.\n"
                "Примеры:\n"
                "- 'завтра в 10 часов утра'\n"
                "- 'в понедельник в 15:30'\n"
                "- 'каждый день в 22:00'\n"
                "- 'через 2 часа'\n"
                "- 'послезавтра в обед'\n"
                "- 'в среду в 2 дня'"
            )
            return False
        
        # Используем текст напоминания от ИИ, а не извлеченный из временной строки
        final_reminder_text = reminder_text  # Используем текст от ИИ
        
        print(f"=== ФИНАЛЬНЫЕ ДАННЫЕ ===")
        print(f"final_reminder_text: '{final_reminder_text}'")
        print(f"reminder_time: {reminder_time}")
        print("=======================")
        user = UserProfile.objects.get(user_id=message.from_user.id)
        if user.pk:
            utc_offset = int(user.timezone[1:])
        else:
            utc_offset = 3
        offset = timedelta(hours=utc_offset)
        custom_timezone = timezone.get_fixed_timezone(offset=offset)
        aware_reminder_time = timezone.make_aware(reminder_time, timezone=custom_timezone)
        aware_pre_reminder_time = timezone.make_aware(pre_reminder_time, timezone=custom_timezone)
        # Добавляем напоминание в базу, используя короткое название от ИИ
        repeat_time=None
        if repeat_type == 'daily':
            repeat_time = aware_reminder_time + timedelta(days=1)
        elif repeat_type == 'weekly':
            repeat_time = aware_reminder_time + timedelta(weeks=1)
        
        Reminder.objects.create(
            user_id=message.from_user.id,
            text=final_reminder_text,
            reminder_time=aware_reminder_time,
            pre_reminder_time=aware_pre_reminder_time,
            is_pre_reminder_sent=False,
            is_main_reminder_sent=False,
            created_at=datetime.now(),
            repeat_type=repeat_type,
            repeat_time=repeat_time
        )
        
        # Формируем сообщение о создании напоминания
        repeat_info = ""
        if repeat_type:
            if repeat_type == 'daily':
                repeat_info = "\n🔄 Тип: каждый день"
            elif repeat_type == 'weekly':
                repeat_info = "\n🔄 Тип: каждую неделю"
        
        bot.send_message(
            chat_id=message.chat.id,
            text=f"✅ Напоминание установлено!\n"
            f"📝 Текст: {final_reminder_text}\n"
            f"🕐 Время: {format_moscow_time(reminder_time)}\n"
            f"⏰ Предварительное напоминание: {format_moscow_time(pre_reminder_time)}{repeat_info}"
        )
        return True
    except Exception as e:
        print(f"Error creating reminder: {e}")
        bot.send_message(
            chat_id=message.chat.id,
            text="Произошла ошибка при создании напоминания. Попробуйте еще раз.")
        return False

def handle_delete_reminder_from_ai(message: Message, ai_data: dict, bot: TeleBot):
    """
    Обрабатывает удаление напоминаний на основе данных от ИИ
    """
    try:
        search_text = ai_data.get('search_text', '').strip()
        
        print(f"=== ОТЛАДКА УДАЛЕНИЯ ===")
        print(f"search_text: '{search_text}'")
        print("=======================")
        
        if not search_text:
            bot.send_message(chat_id=message.chat.id, text="Не удалось определить, какое напоминание нужно удалить. Попробуйте еще раз.")
            return False
        
        # Сначала пытаемся найти по дате
        target_date = parse_date_query(search_text)
        matching_reminders = []
        
        if target_date:
            print(f"Найдена дата: {target_date}")
            matching_reminders = Reminder.objects.filter(user_id=message.from_user.id, reminder_time=target_date)
            # matching_reminders = await find_user_reminders_by_date(message.from_user.id, target_date)
        
        # Если по дате не найдено или дата не определена, ищем по тексту
        if not matching_reminders:
            matching_reminders = Reminder.objects.filter(user_id=message.from_user.id, text=search_text)
            # matching_reminders = await find_user_reminders_by_text(message.from_user.id, search_text)
        
        if not matching_reminders:
            bot.send_message(
                chat_id=message.chat.id, 
                text=f"Не найдено напоминаний по запросу: '{search_text}'\n\n"
                "💡 Попробуйте:\n"
                "• Использовать другие ключевые слова\n"
                "• Посмотреть все напоминания: нажмите '📋 Мои напоминания'\n"
                "• Указать более точное описание"
            )
            return False
        
        if len(matching_reminders) == 1:
            # Если найдено одно напоминание, удаляем его сразу
            reminder = matching_reminders[0]
            
            reminder_time = datetime.fromisoformat(reminder['reminder_time'])
            repeat_info = ""
            if reminder['repeat_type']:
                if reminder['repeat_type'] == 'daily':
                    repeat_info = " (повторяющееся каждый день)"
                elif reminder['repeat_type'] == 'weekly':
                    repeat_info = " (повторяющееся каждую неделю)"
            
            bot.send_message(
                chat_id=message.chat.id, 
                text=f"✅ Напоминание удалено!\n"
                f"📝 Текст: {reminder['text']}\n"
                f"🕐 Время: {format_moscow_time(reminder_time)}{repeat_info}"
            )
            reminder.delete()
            return True
        
        else:
            # Если найдено несколько напоминаний, показываем список и спрашиваем какое удалить
            # Сохраняем контекст для пользователя
            user_delete_context[message.from_user.id] = {
                'reminders': matching_reminders,
                'search_text': search_text
            }
            
            # Определяем тип поиска для сообщения
            search_type = "по дате" if target_date else "по тексту"
            
            message_parts = [
                f"Найдено {len(matching_reminders)} напоминаний {search_type} '{search_text}':\n"
            ]
            
            for i, reminder in enumerate(matching_reminders, 1):
                reminder_time = datetime.fromisoformat(reminder['reminder_time'])
                repeat_info = ""
                if reminder['repeat_type']:
                    if reminder['repeat_type'] == 'daily':
                        repeat_info = " 🔄"
                    elif reminder['repeat_type'] == 'weekly':
                        repeat_info = " 🔄"
                
                message_parts.append(
                    f"{i}. **{reminder['text']}**{repeat_info}\n"
                    f"   🕐 {format_moscow_time(reminder_time)}\n"
                )
            
            message_parts.append(
                "\n💡 Что хотите сделать? Напишите:\n"
                "• 'Удали все' - чтобы удалить все найденные\n"
                "• 'Удали первое' - чтобы удалить первое в списке\n"
                "• 'Удали 3' - чтобы удалить напоминание под номером 3\n"
                "• 'Отмена' - чтобы отменить удаление"
            )
            
            full_message = "\n".join(message_parts)
            bot.send_message(chat_id=message.chat.id, text=full_message, parse_mode="Markdown")
            return True
            
    except Exception as e:
        print(f"Error deleting reminder: {e}")
        bot.send_message(chat_id=message.chat.id, text="Произошла ошибка при удалении напоминания. Попробуйте еще раз.")
        return False 