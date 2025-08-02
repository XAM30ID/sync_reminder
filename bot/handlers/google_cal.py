from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import re, os

from telebot.types import KeyboardButton, ReplyKeyboardMarkup, CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from telebot import TeleBot

from main.settings import BASE_DIR
from bot import SettingsStates
from ..models import UserProfile

ON_OFF_BUTTONS = {
    False: InlineKeyboardButton(text='🔛 Включить', callback_data='G.activate'),
    True: InlineKeyboardButton(text='📴 Отключить', callback_data='G.diactivate')
}

def start_google(message: Message, bot: TeleBot):
    user = UserProfile.objects.get(user_id=message.from_user.id)
    markup = InlineKeyboardMarkup()
    if user.use_google_calendar:
        if user.google_email is None and user.google_email == '':
            markup.add(InlineKeyboardButton(text='❌ Отмена', callback_data='G.cancel'))
            bot.set_state(user_id=message.from_user.id, state=SettingsStates.google_email, chat_id=message.chat.id)
            return bot.send_message(
                chat_id=message.chat.id, 
                text='Для работы с Гугл календарём, Вам нужно дать доступ к календарю этому аккаунту:\n' \
                '<code>reminderbot@remindercalendar.iam.gserviceaccount.com</code>\n' \
                'Это сервисный аккаунт, который будет вносить напоминания в Ваш календарь, а так же, нужно отправить Email аккаунта, с чьим календарём необходимо будет работать.',
                reply_markup=markup,
                parse_mode='html'
                )
        markup.add(ON_OFF_BUTTONS[user.use_google_calendar])
        markup.add(InlineKeyboardButton(text='🔁 Сменить Email', callback_data='G.change_email'))
        markup.add(InlineKeyboardButton(text='🗑️ Удалить Email', callback_data='G.delete_email'))
        return bot.send_message(
            chat_id=message.chat.id, 
            text='Для работы с Гугл календарём Вы используете аккаунт\n' \
            f'<strong>{user.google_email}</strong>\n' \
            'Что Вы хотите сделать?',
            reply_markup=markup,
            parse_mode='html'
            )
    markup.add(ON_OFF_BUTTONS[user.use_google_calendar])
    print(user.google_email)
    if not user.google_email is None and not user.google_email == '':
        markup.add(InlineKeyboardButton(text='🔁 Сменить Email', callback_data='G.change_email'))
        markup.add(InlineKeyboardButton(text='🗑️ Удалить Email', callback_data='G.delete_email'))
        return bot.send_message(
            chat_id=message.chat.id, 
            text='Для работы с Гугл календарём Вы используете аккаунт\n' \
            f'<strong>{user.google_email}</strong>\n' \
            'Что Вы хотите сделать?',
            reply_markup=markup,
            parse_mode='html'
            )
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(text='❌ Отмена', callback_data='G.cancel'))
    bot.set_state(user_id=message.from_user.id, state=SettingsStates.google_email, chat_id=message.chat.id)
    return bot.send_message(
        chat_id=message.chat.id, 
        text='Для работы с Гугл календарём, Вам нужно дать доступ к календарю этому аккаунту (Это можно сделать в настройках календаря):\n' \
        '<code>reminderbot@remindercalendar.iam.gserviceaccount.com</code>\n' \
        'Это сервисный аккаунт, который будет вносить напоминания в Ваш календарь, а так же, нужно отправить Email аккаунта, с чьим календарём необходимо будет работать.',
        reply_markup=markup,
        parse_mode='html'
        )

def set_google_email(message: Message, bot: TeleBot):
    user = UserProfile.objects.get(user_id=message.from_user.id)
    markup = InlineKeyboardMarkup()
    if '@' in message.text and message.text.split('@')[0].count(' ') == 0 and re.fullmatch(r'\S+.\S', message.text.split('@')[1]):
        bot.delete_state(user_id=message.from_user.id, chat_id=message.chat.id)
        user.google_email = message.text
        user.use_google_calendar = True
        user.save()
        markup.add(ON_OFF_BUTTONS[user.use_google_calendar])
        return bot.send_message(
            chat_id=message.chat.id, 
            text=f'✅ Отлично! Вы поставили email <strong>{message.text}</strong>.\n' \
            'Не забудьте дать доступ к календарю этому аккаунту:\n' \
            '<code>reminderbot@remindercalendar.iam.gserviceaccount.com</code>\n' \
            'Это сервисный аккаунт, который будет вносить напоминания в Ваш календарь.',
            reply_markup=markup,
            parse_mode='html'
            )
    
    markup.add(InlineKeyboardButton(text='❌ Отмена', callback_data='G.cancel'))
    return bot.send_message(
        chat_id=message.chat.id, 
        text=f'Введён некорректный Email. Пример:\n' \
        '<code>example@gmail.com</code>',
        reply_markup=markup,
        parse_mode='html'
        )


def change_google_using(call: CallbackQuery, bot: TeleBot):
    user = UserProfile.objects.get(user_id=call.message.chat.id)
    markup = InlineKeyboardMarkup()
    bot.answer_callback_query(callback_query_id=call.id)
    if call.data.split('.')[1] == 'activate':
        user.use_google_calendar = True
    else:
        user.use_google_calendar = False
    user.save()
    markup.add(ON_OFF_BUTTONS[user.use_google_calendar])
    text= '🔛 Включено' if user.use_google_calendar else '📴 Выключено'
    return bot.edit_message_text(
        message_id=call.message.message_id,
        chat_id=call.message.chat.id,
        text=f'{text} использование Гугл календаря',
        reply_markup=markup
    )


def delete_google_email(user: UserProfile, bot: TeleBot):
    try:
        user.google_email = None
        user.use_google_calendar = False
        user.save()
        return '✅ Email успешно удалён!'
    
    except Exception as e:
        print(e)
        bot.send_message(chat_id=763283309, text=e)
        return '❌ Возникла ошибка при удалении Email!'
        

from googleapiclient.errors import HttpError

# Конфигурация
SERVICE_ACCOUNT_FILE = os.path.join(BASE_DIR, 'service-account.json')  # Файл ключа сервисного аккаунта
USER_EMAIL = 'khamzavaliev@gmail.com'  # Почта пользователя (должна быть предварительно настроена)

def add_event(date=datetime.now(), title='Напоминание', description=None):
    try:
        # Создаем учетные данные сервисного аккаунта
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE,
            scopes=['https://www.googleapis.com/auth/calendar']
        )
        
        # Создаем сервис
        service = build('calendar', 'v3', credentials=credentials)
        
        # Создаем событие
        event = {
            'summary': title,
            'start': {'dateTime': f'{date}'},
            'end': {'dateTime': f'{date}'},
            'description': description
        }
        
        # Добавляем событие
        event = service.events().insert(
            calendarId=USER_EMAIL,  # Используем email как calendar ID
            sendNotifications=True,
            body=event
        ).execute()
        
        print(f'Событие создано! Ссылка: {event.get("htmlLink")}')
        return (True, event.get("htmlLink"))
        
    except HttpError as error:
        print(f'Ошибка API: {error}')
        return (False, None)
