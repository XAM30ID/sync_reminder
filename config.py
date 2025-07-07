from dotenv import load_dotenv
import os

# Загрузка переменных окружения
load_dotenv()

# Токены API
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
AI_MODEL = "openai/gpt-4o-mini"

# Настройки проверки напоминаний
REMINDER_CHECK_INTERVAL = 60  # секунды 