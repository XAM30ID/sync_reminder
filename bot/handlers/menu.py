from ..utils.timezone import get_moscow_now, format_moscow_time
from telebot.types import KeyboardButton, ReplyKeyboardMarkup, CallbackQuery, Message, InputMediaPhoto, User
from telebot import TeleBot

main_markup = ReplyKeyboardMarkup(resize_keyboard=True)
main_markup.add(KeyboardButton(text='📝 Напоминание'))
main_markup.add(KeyboardButton(text='📋 Мои напоминания'))

def cmd_start(message: Message, bot: TeleBot):
    """Обработчик команды /start"""
    current_time = format_moscow_time(get_moscow_now(), "%d.%m.%Y %H:%M")
    return bot.send_message(
        chat_id=message.chat.id,
        text=f"👋 Привет! Я бот для создания напоминаний.\n\n"
        f"🕐 Текущее время (МСК): {current_time}\n\n"
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