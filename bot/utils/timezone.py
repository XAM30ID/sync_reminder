from datetime import datetime, timedelta
from django.utils import timezone

from ..models import UserProfile


def get_now(user: UserProfile=None) -> datetime:
    """Получить текущее время в московском часовом поясе без timezone info"""
    if user.pk:
        utc_offset = int(user.timezone[1:])
    else:
        utc_offset = 3
    offset = timedelta(hours=utc_offset)
    custom_timezone = timezone.get_fixed_timezone(offset=offset)
    now = datetime.now(custom_timezone)
    return now

def format_moscow_time(dt: datetime, format_str: str = "%d.%m.%Y %H:%M") -> str:
    """Форматировать время в московском часовом поясе"""
    return dt.strftime(format_str) 