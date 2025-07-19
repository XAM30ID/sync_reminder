import json
import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from telebot.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from telebot import TeleBot

from ..models import UserProfile
from main.settings import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, SCOPES, REDIRECT_URI

def get_google_auth_url(user_id):

    '''
        Получение ссылки для аутентификации Гугл
    '''
    from google_auth_oauthlib.flow import Flow
    flow = Flow.from_client_config(
        client_config={
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [REDIRECT_URI]
            }
        },
        scopes=SCOPES
    )
    flow.redirect_uri = REDIRECT_URI
    auth_url, _ = flow.authorization_url(
        access_type='offline',
        prompt='consent',
        state=str(user_id)
    )
    return auth_url


def exchange_code_for_token(code):
    from google_auth_oauthlib.flow import Flow
    flow = Flow.from_client_config(
        client_config={
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [REDIRECT_URI]
            }
        },
        scopes=SCOPES
    )
    flow.redirect_uri = REDIRECT_URI
    print(REDIRECT_URI)
    flow.fetch_token(code=code)
    return flow.credentials


def create_calendar_event(user, event_data):
    creds = Credentials(
        token=user.token,
        refresh_token=user.refresh_token,
        token_uri='https://oauth2.googleapis.com/token',
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET
    )
    
    service = build('calendar', 'v3', credentials=creds)
    event = service.events().insert(calendarId='primary', body=event_data).execute()
    return event.get('htmlLink')


def auth_google(message: Message, bot: TeleBot):
    user_id = message.from_user.id
    auth_url = get_google_auth_url(user_id)
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Авторизоваться в Google", url=auth_url))
    
    bot.send_message(
        message.chat.id,
        "Пожалуйста, авторизуйтесь в Google Calendar:\n\n"
        "1. Перейдите по ссылке ниже\n"
        "2. Разрешите доступ\n"
        "3. Скопируйте код из адресной строки и отправьте боту\n\n"
        "Пример кода: 4/0Ade...",
        reply_markup=markup
    )


def handle_auth_code(message: Message, bot: TeleBot):
    try:
        code = message.text
        credentials = exchange_code_for_token(code)
        # Сохраняем учетные данные
        user = UserProfile.objects.get(user_id=message.from_user.id)
        user.token = credentials.token
        user.refresh_token = credentials.refresh_token
        user.token_uri = credentials.token_uri
        user.client_id = credentials.client_id
        user.client_secret = credentials.client_secret
        user.scopes = credentials.scopes
        user.save()
        
        bot.send_message(message.chat.id, "✅ Авторизация успешна! Теперь вы можете создавать события.")
        bot.send_message(message.chat.id, "Чтобы добавить событие, используйте /addevent")
    
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка авторизации: {str(e)}")


# def process_event_duration(message):
#     try:
#         duration = int(message.text)
#         user_id = message.from_user.id
        
#         from datetime import datetime, timedelta
#         start_time = datetime.fromisoformat(user_data[user_id]['start'])
#         end_time = start_time + timedelta(minutes=duration)
        
#         event_data = {
#             'summary': user_data[user_id]['title'],
#             'start': {
#                 'dateTime': start_time.isoformat(),
#                 'timeZone': 'Europe/Moscow',
#             },
#             'end': {
#                 'dateTime': end_time.isoformat(),
#                 'timeZone': 'Europe/Moscow',
#             },
#             'reminders': {
#                 'useDefault': True,
#                 },
#         }
        
#         # Проверяем авторизацию
#         if user_id not in user_credentials:
#             bot.send_message(message.chat.id, "❌ Вы не авторизованы! Используйте /auth")
#             return
        
#         # Создаем событие
#         event_link = create_calendar_event(user_credentials[user_id], event_data)
#         bot.send_message(message.chat.id, f"✅ Событие создано!\n{event_link}")
        
#         # Очищаем временные данные
#         del user_data[user_id]
    
#     except Exception as e:
#         bot.send_message(message.chat.id, f"❌ Ошибка создания события: {str(e)}")
