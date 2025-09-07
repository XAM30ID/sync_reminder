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
from bot.handlers.google_cal import *
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

@bot.message_handler(commands=['setting'])
def m_cmd_setting(message: Message):
    '''
        Обработчик команды setting
    '''
    
    try:
        cmd_setting(message=message, bot=bot)
    except Exception as e:
        print(e)


@bot.callback_query_handler(func=lambda call: call.data.startswith('set'))
def m_selected_google_action(call: CallbackQuery):
    '''
        Работа с Гугл календарём
    '''
    data = call.data.split('.')[-1]

    if call.data.startswith('set.a.'):
        data = call.data.split('.')[-1]
        print(call.from_user.id)
        user = UserProfile.objects.get(user_id=call.from_user.id)
        user.addressing = data
        user.save()
        try: 
            bot.edit_message_text(
                text=f"Готово! Выбрано обращение на {ADDRESSINGS[data]}",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id
            )
        except:
            bot.send_message(
                chat_id=call.message.chat.id, 
                text=f'Готово! Выбрано обращение на {ADDRESSINGS[data]}',
                parse_mode='html'
                )
        return
    
    if call.data.startswith('set.s.'):
        data = call.data.split('.')[-1]
        user = UserProfile.objects.get(user_id=call.from_user.id)
        user.tone = data
        user.save()
        try: 
            bot.edit_message_text(
                text=f"Готово! Выбран стиль общения: {STYLES[data]}",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id
            )
        except:
            bot.send_message(
                chat_id=call.message.chat.id, 
                text=f'Готово! Выбран стиль общения: {STYLES[data]}',
                parse_mode='html'
                )
        return
    

    if data == 'cancel':
        bot.delete_state(user_id=call.from_user.id, chat_id=call.message.chat.id)
        bot.delete_message(message_id=call.message.id, chat_id=call.message.chat.id)
        bot.delete_state(user_id=call.from_user.id)
        bot.send_message(
            chat_id=call.message.chat.id,
            text='Настройки отменены'
        )

    if data == 'a':
        bot.delete_message(message_id=call.message.id, chat_id=call.message.chat.id)
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton(text='На ты', callback_data='set.a.ty'), InlineKeyboardButton(text='На вы', callback_data='set.a.vy'))
        markup.add(InlineKeyboardButton(text='❌ Отмена', callback_data='set.cancel'))
        return bot.send_message(
            chat_id=call.message.chat.id, 
            text='🤝 Как мне обращаться?',
            reply_markup=markup,
            parse_mode='html'
            )
    
    if data == 's':
        bot.delete_message(message_id=call.message.id, chat_id=call.message.chat.id)
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(text='💼 Деловой', callback_data='set.s.business'), InlineKeyboardButton(text='🤝 Дружелюбный', callback_data='set.s.friendly'), InlineKeyboardButton(text='👥 Нейтральный', callback_data='set.s.neutral'))
        markup.add(InlineKeyboardButton(text='❌ Отмена', callback_data='set.cancel'))
        return bot.send_message(
            chat_id=call.message.chat.id, 
            text='👋 Как мне обращаться?',
            reply_markup=markup,
            parse_mode='html'
            )
    
    if data == 'h':
        bot.delete_message(message_id=call.message.id, chat_id=call.message.chat.id)
        bot.set_state(call.from_user.id, SettingsStates.change_timezone)
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(text='❌ Отмена', callback_data='set.cancel'))
        return bot.send_message(
            chat_id=call.message.chat.id, 
            text='Теперь отправьте часовой пояс в формате: +0',
            reply_markup=markup,
            parse_mode='html'
            )
    
    if data == 'g':
        try:
            try:
                bot.delete_message(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id
                )
            except:
                pass
            start_google(message=call.message, bot=bot, user_id=call.from_user.id)
        except Exception as e:
            print(e)


# @bot.message_handler(commands=['google_calendar'])
# def m_google_calendar(message: Message):
#     '''
#         Обработчик команды для работы с гугл календарём
#     '''
#     try:
#         start_google(message=message, bot=bot)
#     except Exception as e:
#         print(e)


# @bot.callback_query_handler(func=lambda call: call.data.startswith('G'))
# def m_selected_google_action(call: CallbackQuery):
#     '''
#         Работа с Гугл календарём
#     '''
#     data = call.data.split('.')[-1]
#     if data == 'cancel':
#         bot.delete_state(user_id=call.from_user.id, chat_id=call.message.chat.id)
#         bot.delete_message(message_id=call.message.id, chat_id=call.message.chat.id)
#         bot.send_message(
#             chat_id=call.message.chat.id,
#             text='Работа с Гугл календарём отменена'
#         )

#     if data == 'activate' or data == 'diactivate':
#         change_google_using(call=call, bot=bot)
    
#     if data == 'change_email':
#         bot.delete_message(message_id=call.message.id, chat_id=call.message.chat.id)
#         markup = InlineKeyboardMarkup()
#         markup.add(InlineKeyboardButton(text='❌ Отмена', callback_data='G.cancel'))
#         bot.set_state(user_id=call.message.chat.id, state=SettingsStates.google_email, chat_id=call.message.chat.id)
#         return bot.send_message(
#             chat_id=call.message.chat.id, 
#             text='Отправьте новый Email',
#             reply_markup=markup,
#             parse_mode='html'
#             )

#     if data == 'delete_email':
#         bot.delete_message(message_id=call.message.id, chat_id=call.message.chat.id)
#         return bot.send_message(
#             chat_id=call.message.chat.id, 
#             text=delete_google_email(user=UserProfile.objects.get(user_id=call.message.chat.id), bot=bot),
#             parse_mode='html'
#             )
        
    
    
@bot.message_handler(state=SettingsStates.timezone.name)
def m_final_sets(message: Message):
    '''
        Установка параметров для пользователя
    '''
    try:
        final_sets(message, bot)

    except Exception as e:
        logger.error(f'При установке параметров для пользователя возникла ошибка: {e}')
        bot.send_message(chat_id=763283309, text=e)


@bot.callback_query_handler(func=lambda call: call.data.startswith('o'))
def m_selected_addressing(call: CallbackQuery):
    '''
        Выбор обращения к пользователю
    '''
    try:
        selected_addressing(call, bot)

    except Exception as e:
        logger.error(f'При выборе обращения к пользователю возникла ошибка: {e}')
        bot.send_message(chat_id=763283309, text=e)


@bot.callback_query_handler(func=lambda call: call.data.startswith('f'))
def m_selected_tone(call: CallbackQuery):
    '''
        Выбор тона разговора
    '''
    try:
        selected_tone(call, bot)
        
    except Exception as e:
        logger.error(f'При выборе тона общения возникла ошибка: {e}')
        bot.send_message(chat_id=763283309, text=e)


@bot.callback_query_handler(func=lambda call: call.data.startswith('t'))
def m_task_sets(call: CallbackQuery):
    '''
        Действия с задачей (Завершить, перенести, удалить)
    '''
    try:
        task_sets(call, bot)

    except Exception as e:
        logger.error(f'При работе с задачей возникла ошибка: {e}')
        bot.send_message(chat_id=763283309, text=e)


@bot.message_handler(func=lambda message: message.text == '📝 Напоминание' or message.text == '⚙️ Задача')
def m_reminder_button(message: Message):
    '''
        Кнопка создания напоминания
    '''
    try:
        reminder_button(message=message, bot=bot)

    except Exception as e:
        logger.error(f'При начале работы с напоминанием возникла ошибка: {e}')
        bot.send_message(chat_id=763283309, text=e)


@bot.message_handler(func=lambda message: message.text == '📋 Все напоминания и задачи')
def m_list_reminders(message: Message):
    '''
        Кнопка всех напоминаний
    '''
    try:
        list_reminders(message=message, bot=bot)

    except Exception as e:
        logger.error(f'При выведении списка напоминаний возникла ошибка: {e}')
        bot.send_message(chat_id=763283309, text=e)


@bot.message_handler(content_types=['voice'])
def m_handle_voice(message: Message):
    '''
        Обработка голоса
    '''
    try:
        handle_voice(message=message, bot=bot)

    except Exception as e:
        logger.error(f'При обработке возникла ошибка {e}')
        bot.send_message(chat_id=763283309, text=e)


@bot.message_handler(content_types=['text'])
def m_handle_text(message: Message):
    '''
        Обработка текста
    '''
    
    if bot.get_state(message.from_user.id) == SettingsStates.google_email.name:
        try:
            set_google_email(message=message, bot=bot)
        except Exception as e:
            print(e)
            bot.send_message(chat_id=763283309, text=e)

    elif bot.get_state(message.from_user.id) == SettingsStates.change_timezone.name:
        try:
            if message.text.startswith('+') or message.text.startswith('-') and len(message.text) <= 3:
                bot.delete_state(message.from_user.id, message.chat.id)
                user = UserProfile.objects.get(user_id=message.from_user.id)
                user.timezone = message.text
                try:
                    bot.delete_message(
                        chat_id=message.chat.id,
                        message_id=message.message_id - 1
                    )
                except:
                    pass
                bot.send_message(
                    chat_id=message.chat.id,
                    text=f'Готово! Ваш часовой пояс: {message.text}'
                )
                return 
            else:
                markup = InlineKeyboardMarkup()
                markup.add(InlineKeyboardButton(text='❌ Отмена', callback_data='set.cancel'))
                try:
                    bot.delete_message(
                        chat_id=message.chat.id,
                        message_id=message.message_id - 1
                    )
                except:
                    pass
                bot.send_message(
                    chat_id=message.chat.id,
                    text='Некорректный часовой пояс',
                    reply_markup=markup
                )
                return

        except Exception as e:
            print(e)
            bot.send_message(chat_id=763283309, text=e)

    elif bot.get_state(message.from_user.id) == SettingsStates.timezone.name:
        try:
            final_sets(message, bot)
        except Exception as e:
            logger.error(f'При установке параметров для пользователя возникла ошибка: {e}')
            bot.send_message(chat_id=763283309, text=e)

    else:
        try:
            handle_text(message=message, bot=bot)
        except Exception as e:
            bot.send_message(chat_id=763283308, text=e)