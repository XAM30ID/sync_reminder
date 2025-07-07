from datetime import datetime, timezone, timedelta

# Московский часовой пояс (UTC+3)
MOSCOW_TZ = timezone(timedelta(hours=3))

def get_moscow_now() -> datetime:
    """Получить текущее время в московском часовом поясе без timezone info"""
    return datetime.now(MOSCOW_TZ).replace(tzinfo=None)

def format_moscow_time(dt: datetime, format_str: str = "%d.%m.%Y %H:%M") -> str:
    """Форматировать время в московском часовом поясе"""
    return dt.strftime(format_str) 