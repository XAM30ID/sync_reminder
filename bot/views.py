from traceback import format_exc

from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from asgiref.sync import sync_to_async
from django.http import HttpRequest, JsonResponse
from django.conf import settings

from telebot.apihelper import ApiTelegramException
from telebot.types import Update

from bot import bot, logger, SettingsStates
from bot.handlers.reminder import *
from bot.handlers.menu import *
from bot.handlers.common import *


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
    '''
        Обработчик команды старт
    '''
    
    try:
        cmd_start(message=message, bot=bot)
    except Exception as e:
        print(e)


@bot.message_handler(state=SettingsStates.timezone.name)
def m_final_sets(message: Message):
    '''
        Установка параметров для пользователя
    '''
    try:
        final_sets(message, bot)

    except Exception as e:
        logger.error(f'При установке параметров для пользователя возникла ошибка: {e}')


@bot.callback_query_handler(func=lambda call: call.data.startswith('o'))
def m_selected_addressing(call: CallbackQuery):
    '''
        Выбор обращения к пользователю
    '''
    try:
        selected_addressing(call, bot)

    except Exception as e:
        logger.error(f'При выборе обращения к пользователю возникла ошибка: {e}')


@bot.callback_query_handler(func=lambda call: call.data.startswith('f'))
def m_selected_tone(call: CallbackQuery):
    '''
        Выбор тона разговора
    '''
    try:
        selected_tone(call, bot)
        
    except Exception as e:
        logger.error(f'При выборе тона общения возникла ошибка: {e}')


@bot.callback_query_handler(func=lambda call: call.data.startswith('t'))
def m_task_sets(call: CallbackQuery):
    '''
        Действия с задачей (Завершить, перенести, удалить)
    '''
    try:
        task_sets(call, bot)

    except Exception as e:
        logger.error(f'При работе с задачей возникла ошибка: {e}')


@bot.message_handler(func=lambda message: message.text == '📝 Напоминание' or message.text == '⚙️ Задача')
def m_reminder_button(message: Message):
    '''
        Кнопка создания напоминания
    '''
    try:
        reminder_button(message=message, bot=bot)

    except Exception as e:
       logger.error(f'При начале работы с напоминанием возникла ошибка: {e}')


@bot.message_handler(func=lambda message: message.text == '📋 Все напоминания и задачи')
def m_list_reminders(message: Message):
    '''
        Кнопка всех напоминаний
    '''
    try:
        list_reminders(message=message, bot=bot)

    except Exception as e:
        logger.error(f'При выведении списка напоминаний возникла ошибка: {e}')


@bot.message_handler(content_types=['voice'])
def m_handle_voice(message: Message):
    '''
        Обработка голоса
    '''
    try:
        handle_voice(message=message, bot=bot)

    except Exception as e:
        logger.error(f'При обработке возникла ошибка {e}')


@bot.message_handler(content_types=['text'])
def m_handle_text(message: Message):
    '''
        Обработка текста
    '''
    if bot.get_state(message.from_user.id) == SettingsStates.timezone.name:
        try:
            final_sets(message, bot)
        except Exception as e:
            logger.error(f'При установке параметров для пользователя возникла ошибка: {e}')

    else:
        try:
            handle_text(message=message, bot=bot)
        except Exception as e:
            logger.error(f'При обработке текста возникла ошибка: {e}')