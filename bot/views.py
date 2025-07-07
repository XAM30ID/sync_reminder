from traceback import format_exc

from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from asgiref.sync import sync_to_async
from django.http import HttpRequest, JsonResponse
from django.conf import settings

from telebot.apihelper import ApiTelegramException
from telebot.types import Update

from bot import bot, logger
from bot.handlers.reminder import *
from bot.handlers.menu import *


@require_GET
def set_webhook(request: HttpRequest) -> JsonResponse:
    '''
        Установка вебхуков со стороны бота
    '''
    bot.set_webhook(url=f"{settings.HOOK}/bot/{settings.BOT_TOKEN}", allowed_updates=['message', 'callback_query'])
    bot.send_message(settings.OWNER_ID, "webhook set")
    return JsonResponse({"message": "OK"}, status=200)


@csrf_exempt
@require_POST
@sync_to_async
def index(request: HttpRequest) -> JsonResponse:
    '''
        Установка вебхуков со стороны сайта
    '''
    if request.META.get("CONTENT_TYPE") != "application/json":
        return JsonResponse({"message": "Bad Request"}, status=403)

    json_string = request.body.decode("utf-8")
    update = Update.de_json(json_string)
    try:
        bot.process_new_updates([update])
    except ApiTelegramException as e:
        logger.error(f"Telegram exception. {e} {format_exc()}")
    except ConnectionError as e:
        logger.error(f"Connection error. {e} {format_exc()}")
    except Exception as e:
        bot.send_message(settings.OWNER_ID, f'Error from index: {e}')
        logger.error(f"Unhandled exception. {e} {format_exc()}")
    return JsonResponse({"message": "OK"}, status=200)


@bot.message_handler(commands=['start'])
def m_cmd_start(message: Message):
    print(Reminder.objects.filter(is_pre_reminder_sent=False))
    try:
        cmd_start(message=message, bot=bot)
    except Exception as e:
        print(e)

@bot.message_handler(func=lambda message: message.text == '📝 Напоминание')
def m_reminder_button(message: Message):
    try:
        reminder_button(message=message, bot=bot)
    except Exception as e:
        print(e)


@bot.message_handler(func=lambda message: message.text == '📋 Мои напоминания')
def m_list_reminders(message: Message):
    try:
        list_reminders(message=message, bot=bot)
    except Exception as e:
        print(e)


@bot.message_handler(content_types=['voice'])
def m_handle_voice(message: Message):
    try:
        handle_voice(message=message, bot=bot)
    except Exception as e:
        print(e)


@bot.message_handler(content_types=['text'])
def m_handle_text(message: Message):
    try:
        handle_text(message=message, bot=bot)
    except Exception as e:
        print(e)