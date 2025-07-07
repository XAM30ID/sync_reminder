import logging
import telebot

from django.conf import settings

# Получение комманд
commands = settings.BOT_COMMANDS

# Инициализация бота
bot = telebot.TeleBot(
    settings.BOT_TOKEN,
    threaded=False,
    skip_pending=True,
)

# Установка комманд для бота
bot.set_my_commands(commands)

logging.info(f'@{bot.get_me().username} started')

logger = telebot.logger
logger.setLevel(logging.INFO)

logging.basicConfig(level=logging.INFO, filename="ai_log.log", filemode="w")