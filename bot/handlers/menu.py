from telebot.types import KeyboardButton, ReplyKeyboardMarkup, CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from telebot import TeleBot


from ..models import UserProfile
from bot import SettingsStates
from .ai import OpenAIAPI

start_markup = InlineKeyboardMarkup()
start_markup.add(InlineKeyboardButton(text='На ты', callback_data='o.ty'))
start_markup.add(InlineKeyboardButton(text='На Вы', callback_data='o.vy'))

main_markup = ReplyKeyboardMarkup(resize_keyboard=True)
main_markup.add(KeyboardButton(text='📝 Напоминание'))
main_markup.add(KeyboardButton(text='⚙️ Задача'))
main_markup.add(KeyboardButton(text='📋 Все напоминания и задачи'))

def cmd_start(message: Message, bot: TeleBot):
    """
        Обработчик команды /start
    """
    bot.set_state(message.from_user.id, SettingsStates.addressing, message.chat.id)
    return bot.send_message(
        chat_id=message.chat.id,
        text=f"👋 Привет! Я бот для создания напоминаний.\n\n"
        f"Для начала, давай определим, как мне лучше обращаться?\n\n",
        reply_markup=start_markup,
        parse_mode="Markdown"
    ) 


def selected_addressing(call: CallbackQuery, bot: TeleBot):
    '''
        Выбор обращения к пользователю
    '''
    addressing = call.data.split('.')[-1]
    try:
        communication_markup = InlineKeyboardMarkup()
        communication_markup.add(InlineKeyboardButton(text='💼 Деловой', callback_data=f'f.{addressing}|business'))
        communication_markup.add(InlineKeyboardButton(text='🤝 Дружелюбный', callback_data=f'f.{addressing}|friendly'))
        communication_markup.add(InlineKeyboardButton(text='👥 Нейтральный', callback_data=f'f.{addressing}|neutral'))
        communication_markup.add(InlineKeyboardButton(text='↩️ Вернуться', callback_data=f'f.return'))
        bot.set_state(call.from_user.id, SettingsStates.tone, call.message.chat.id)
        bot.add_data(call.from_user.id, call.message.chat.id, addressing=addressing)
        return bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f'Отлично! Я буду обращаться на {addressing}.\n\n'
            f'Теперь нужно выбрать тон общения:',
            reply_markup=communication_markup
        )
    except Exception as e:
        print(e)
        bot.send_message(
            chat_id=call.message.chat.id,
            text='Извините, возникла ошибка. Попробуйте снова'
        )
        return bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"👋 Привет! Я бот для создания напоминаний.\n\n"
            f"Для начала, давай определим, как мне лучше обращаться?\n\n",
            reply_markup=start_markup,
            parse_mode="Markdown"
        ) 


def selected_tone(call: CallbackQuery, bot: TeleBot):
    '''
        Выбор тона общения
    '''
    data = call.data.split('.')[-1]
    bot.answer_callback_query(callback_query_id=call.id)
    if data == 'return':
        return bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"👋 Привет! Я бот для создания напоминаний.\n\n"
            f"Для начала, давай определим, как мне лучше обращаться?\n\n",
            reply_markup=start_markup,
            parse_mode="Markdown"
        ) 
    
    else:
        addressing, tone = data.split('|')
        bot.add_data(call.from_user.id, call.message.chat.id, tone=tone)
        bot.set_state(call.from_user.id, SettingsStates.timezone)
        return bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text='Отлично!\n\n' 
            'Осталось отправить часовой пояс по формату: +0 или -0 относительно UTC',
            reply_markup=None
        )


def final_sets(message: Message, bot: TeleBot):
    '''
        Последние установки параметров общения для пользователя
    '''
    if message.text.startswith('+') or message.text.startswith('-') and len(message.text) <= 3:
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            bot.delete_state(message.from_user.id, message.chat.id)
            try:
                print(UserProfile.objects.filter(user_id=message.from_user.id).count)
            except Exception as e:
                print('ОШИБКА: ', e)
            try:
                us = UserProfile.objects.update_or_create(
                    defaults={
                    'username': message.from_user.username,
                    'addressing': data['addressing'],
                    'tone': data['tone'],
                    'timezone': message.text
                    },
                    user_id=message.from_user.id,
                )
            except Exception as e:
                print('ОШИБКА:', e)

            return bot.send_message(
                chat_id=message.chat.id,
                text=f"👋 Привет! Я бот для создания напоминаний.\n\n"
                f"Теперь я понимаю много новых форматов:\n\n"
                f"📅 **Относительные даты:**\n"
                f"• 'завтра в 8:30 выпить витамины'\n"
                f"• 'послезавтра в 14:00 встреча'\n\n"
                f"📆 **Дни недели:**\n"
                f"• 'в субботу в 10:00 уборка'\n"
                f"• 'в понедельник в 9:00 работа'\n\n"
                f"🔄 **Циклические напоминания:**\n"
                f"• 'каждый день в 22:00 витамины'\n"
                f"• 'каждый понедельник в 8:00 спорт'\n"
                f"• 'каждое утро зарядка'\n"
                f"• 'каждый вечер прогулка'\n\n"
                f"⏰ **Обычные форматы:**\n"
                f"• 'через 2 часа сделать зарядку'\n"
                f"• 'в 15:30 позвонить маме'",
                reply_markup=main_markup,
                parse_mode="Markdown"
            ) 
    else:
        return bot.send_message(
            chat_id=message.chat.id,
            text='Некорректный часовой пояс'
        )