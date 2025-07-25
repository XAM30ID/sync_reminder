from datetime import datetime, timedelta
import dateparser
import re
from ..utils.timezone import get_now
from django.utils import timezone


def normalize_time_string(text: str) -> str:
    """
    Нормализация строки времени для лучшего распознавания
    """
    text_lower = text.lower()
    
    # Проверяем, есть ли в тексте дни недели с временными указаниями
    # Если есть, не заменяем временные указания
    weekday_with_time_pattern = r'(?:в\s*|на\s*)?(понедельник|вторник|среда|среду|четверг|пятница|пятницу|суббота|субботу|воскресенье)\s+(утром|утро|вечером|вечер|ночью|ночь|в\s*обед|обед)'
    has_weekday_with_time = re.search(weekday_with_time_pattern, text_lower)
    
    # Замены для лучшего распознавания
    replacements = {
        'полдень': '12:00',
        'полночь': '00:00',
        'послезавтра': 'after tomorrow',
        'после завтра': 'after tomorrow',
        # Добавляем больше вариантов дней недели
        'в понедельник': 'понедельник',
        'в вторник': 'вторник', 
        'в среду': 'среду',
        'в четверг': 'четверг',
        'в пятницу': 'пятницу',
        'в субботу': 'субботу',
        'в воскресенье': 'воскресенье',
        'на понедельник': 'понедельник',
        'на вторник': 'вторник',
        'на среду': 'среду', 
        'на четверг': 'четверг',
        'на пятницу': 'пятницу',
        'на субботу': 'субботу',
        'на воскресенье': 'воскресенье',
    }
    
    # Временные замены применяем только если нет дня недели с временным указанием
    if not has_weekday_with_time:
        time_replacements = {
            'вечера': 'pm',
            'вечером': 'pm',
            'днём': 'pm',
            'днем': 'pm',
            'утра': 'am',
            'утром': 'am',
            'ночи': 'am',
            'ночью': 'am',
        }
        replacements.update(time_replacements)
    
    # Специальная обработка для времени дня (только в контексте времени)
    # Заменяем "дня" на "pm" только если это не "через X дня"
    if not re.search(r'через\s+\d+\s+дня', text_lower):
        time_context_pattern = r'(\d{1,2}(?::\d{2})?\s*)дня'
        text_lower = re.sub(time_context_pattern, r'\1pm', text_lower)
    
    for old, new in replacements.items():
        text_lower = text_lower.replace(old, new)
    
    return text_lower

def get_weekday_number(day_name: str) -> int:
    """Получить номер дня недели (0 = понедельник)"""
    weekdays = {
        'понедельник': 0, 'пн': 0,
        'вторник': 1, 'вт': 1,
        'среда': 2, 'ср': 2, 'среду': 2,
        'четверг': 3, 'чт': 3,
        'пятница': 4, 'пт': 4, 'пятницу': 4,
        'суббота': 5, 'сб': 5, 'субботу': 5,
        'воскресенье': 6, 'вс': 6,
    }
    return weekdays.get(day_name.lower())

def calculate_next_weekday(target_weekday: int, time_str: str = None, force_next_week: bool = False) -> datetime:
    """Вычислить следующую дату для указанного дня недели"""
    now = get_now()
    current_weekday = now.weekday()
    
    # Вычисляем количество дней до следующего нужного дня
    days_ahead = target_weekday - current_weekday
    
    # Если force_next_week=True или сегодня уже указанный день недели, переносим на следующую неделю
    if force_next_week or days_ahead <= 0:  
        days_ahead += 7
    
    target_date = now + timedelta(days=days_ahead)
    
    # Если указано время, применяем его
    if time_str:
        # Сначала проверяем простые временные указания
        if 'вечером' in time_str or 'вечер' in time_str:
            target_date = target_date.replace(hour=19, minute=0, second=0, microsecond=0)
        elif 'утром' in time_str or 'утро' in time_str:
            target_date = target_date.replace(hour=9, minute=0, second=0, microsecond=0)
        elif 'ночью' in time_str or 'ночь' in time_str:
            target_date = target_date.replace(hour=22, minute=0, second=0, microsecond=0)
        elif 'в обед' in time_str or 'обед' in time_str:
            target_date = target_date.replace(hour=13, minute=0, second=0, microsecond=0)
        else:
            # Пытаемся извлечь время из строки
            time_match = re.search(r'(\d{1,2}):?(\d{2})?', time_str)
            if time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2)) if time_match.group(2) else 0
                
                # Проверяем на am/pm
                if 'pm' in time_str and hour < 12:
                    hour += 12
                elif 'am' in time_str and hour == 12:
                    hour = 0
                    
                target_date = target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
            else:
                # Если время не указано, устанавливаем на 9:00
                target_date = target_date.replace(hour=9, minute=0, second=0, microsecond=0)
    else:
        target_date = target_date.replace(hour=9, minute=0, second=0, microsecond=0)
    
    return target_date

def extract_time_and_text(text: str) -> tuple[str, str, str]:
    """
    Извлекает время, текст напоминания и тип повторения из сообщения
    Возвращает (time_str, reminder_text, repeat_type)
    """
    normalized_text = normalize_time_string(text)
    
    # Проверяем циклические напоминания
    repeat_patterns = [
        (r'каждый (понедельник|вторник|среду|четверг|пятницу|субботу|воскресенье)', 'weekly'),
        (r'каждую (неделю)', 'weekly'), 
        (r'каждый (день)', 'daily'),
        (r'каждое (утро)', 'daily_morning'),
        (r'каждый (вечер)', 'daily_evening'),
    ]
    
    repeat_type = None
    for pattern, r_type in repeat_patterns:
        if re.search(pattern, normalized_text, re.IGNORECASE):
            repeat_type = r_type
            break
    
    # Паттерны для поиска времени и дат
    time_patterns = [
        # Относительные даты с временем (например, "через 3 дня в 09:00")
        r'через (\d+)\s*(минут|час[ао]?в?|дн[ейяи]|день|дня|дни)\s*(?:в\s*)?(\d{1,2}(?::\d{2})?\s*(?:am|pm|утра|вечера|дня|ночи)?)',
        # Дни недели с временными указаниями - самый специфичный паттерн должен быть первым
        r'(?:в\s*|на\s*|эту\s*|этот\s*|это\s*|следующий\s*|следующую\s*)?(понедельник|вторник|среда|среду|четверг|пятница|пятницу|суббота|субботу|воскресенье)\s+(утром|утро|вечером|вечер|ночью|ночь|в\s*обед|обед)',
        # Относительные даты с временем
        r'(завтра|послезавтра|после завтра|after tomorrow)\s*(?:в\s*)?(\d{1,2}(?::\d{2})?\s*(?:am|pm|утра|вечера|дня|ночи)?|13:00|обед)',
        # Дни недели с цифровым временем (более строгий паттерн - только цифры и 13:00/обед)
        r'(?:в\s*|на\s*|эту\s*|этот\s*|это\s*|следующий\s*|следующую\s*)?(понедельник|вторник|среда|среду|четверг|пятница|пятницу|суббота|субботу|воскресенье)\s*(?:в\s*)?(\d{1,2}(?::\d{2})?\s*(?:am|pm|утра|вечера|дня|ночи)?|13:00)',
        # Дни недели с "в обед" - отдельный паттерн
        r'(?:в\s*|на\s*|эту\s*|этот\s*|это\s*|следующий\s*|следующую\s*)?(понедельник|вторник|среда|среду|четверг|пятница|пятницу|суббота|субботу|воскресенье)\s*в\s*обед',
        # Циклические напоминания с временем
        r'каждый\s*(понедельник|вторник|среда|среду|четверг|пятница|пятницу|суббота|субботу|воскресенье)\s*(?:в\s*)?(\d{1,2}(?::\d{2})?\s*(?:am|pm|утра|вечера|дня|ночи)?|13:00|обед|утро|вечер|ночь)',
        # Обычные паттерны времени
        r'в (\d{1,2}(?::\d{2})?\s*(?:am|pm|утра|вечера|дня|ночи)?|13:00|обед|утро|вечер|ночь)',
        r'через (\d+)\s*(минут|час[ао]?в?|дн[ейяи]|день|дня|дни)',
        # Дни недели в начале строки (новый паттерн)
        r'^(?:эту\s*|этот\s*|это\s*|следующий\s*|следующую\s*)?(понедельник|вторник|среда|среду|четверг|пятница|пятницу|суббота|субботу|воскресенье)(?:\s+(?:в\s*)?(\d{1,2}(?::\d{2})?\s*(?:am|pm|утра|вечера|дня|ночи)?|13:00|обед|утро|вечер|ночь))?',
        # Дни недели без времени (более гибкие)
        r'(?:в\s*|на\s*|эту\s*|этот\s*|это\s*|следующий\s*|следующую\s*)?(понедельник|вторник|среда|среду|четверг|пятница|пятницу|суббота|субботу|воскресенье)(?!\s*\d)',
        # Относительные даты без времени
        r'(завтра|послезавтра|после завтра|after tomorrow)(?!\s*\d)',
        # Циклические без времени
        r'(каждую неделю|каждый день|каждое утро|каждый вечер)',
        # Циклические напоминания без времени с днями недели
        r'каждый\s*(понедельник|вторник|среда|среду|четверг|пятница|пятницу|суббота|субботу|воскресенье)(?!\s*\d)',
        # Новые паттерны для обеда и других времен дня
        r'(в обед|обед|обеденное время)',
        r'(утром|утро|с утра)',
        r'(вечером|вечер)',
        r'(ночью|ночь)',
        # Следующая неделя
        r'(на следующей неделе|следующую неделю|через неделю)\s*(?:в\s*)?(понедельник|вторник|среда|среду|четверг|пятница|пятницу|суббота|субботу|воскресенье)?\s*(?:в\s*)?(\d{1,2}(?::\d{2})?\s*(?:am|pm|утра|вечера|дня|ночи)?|13:00|обед|утро|вечер|ночь)?',
    ]
    
    for pattern in time_patterns:
        if normalized_text.lower().strip() == 'через час':
            normalized_text = 'через 1 час'
        match = re.search(pattern, normalized_text, re.IGNORECASE)
        if match:
            time_str = match.group(0)
            # Удаляем найденное время из текста и очищаем от лишних пробелов
            reminder_text = re.sub(pattern, '', normalized_text, 1).strip()
            # Дополнительно очищаем текст от артефактов
            reminder_text = clean_reminder_text(reminder_text, time_str)
            return time_str, reminder_text, repeat_type
    return None, text, repeat_type

def parse_reminder_time(text: str, user) -> tuple[datetime, datetime, str, str]:
    """
    Парсит время и текст напоминания из сообщения
    Возвращает кортеж (время_напоминания, время_предварительного_напоминания, текст_напоминания, тип_повторения)
    """
    time_str, reminder_text, repeat_type = extract_time_and_text(text)
    if not time_str:
        return None, None, text, None
    
    now = get_now(user=user)
    reminder_time = None
    # Обработка "через X минут/часов/дней"
    # Сначала проверяем полный паттерн с временем
    relative_with_time_match = re.match(r'через (\d+)\s*(минут|час[ао]?в?|дн[ейяи]|день|дня|дни)\s*(?:в\s*)?(\d{1,2}(?::\d{2})?\s*(?:am|pm|утра|вечера|дня|ночи)?)', time_str, re.IGNORECASE)
    if relative_with_time_match:
        number = int(relative_with_time_match.group(1))
        unit = relative_with_time_match.group(2)
        time_part = relative_with_time_match.group(3)
        
        if 'час' in unit:
            reminder_time = now + timedelta(hours=number)
        elif 'дн' in unit or 'день' in unit or 'дня' in unit or 'дни' in unit:
            # Добавляем дни к текущей дате
            target_date = now + timedelta(days=number)
            
            # Парсим указанное время
            if user.pk:
                utc_offset = int(user.timezone[1:])
            else:
                utc_offset = 3
            offset = timedelta(hours=utc_offset)
            custom_timezone = timezone.get_fixed_timezone(offset=offset)
            parsed_time = dateparser.parse(time_part, settings={
                'PREFER_DATES_FROM': 'future',
                'TIMEZONE': str(custom_timezone),
                'RETURN_AS_TIMEZONE_AWARE': False,
            })
            if parsed_time:
                reminder_time = target_date.replace(
                    hour=parsed_time.hour,
                    minute=parsed_time.minute,
                    second=0,
                    microsecond=0
                )
            else:
                # Если не удалось распарсить время, устанавливаем 9:00
                reminder_time = target_date.replace(hour=9, minute=0, second=0, microsecond=0)
        else:
            reminder_time = now + timedelta(minutes=number)
    
    # Если не нашли полный паттерн, проверяем обычный
    elif not reminder_time:
        relative_match = re.match(r'через (\d+)\s*(минут|час[ао]?в?|дн[ейяи]|день|дня|дни)', time_str, re.IGNORECASE)
        if relative_match:
            number = int(relative_match.group(1))
            unit = relative_match.group(2)
            
            if 'час' in unit:
                reminder_time = now + timedelta(hours=number)
            elif 'дн' in unit or 'день' in unit or 'дня' in unit or 'дни' in unit:
                # Добавляем дни к текущей дате
                target_date = now + timedelta(days=number)
                
                # Проверяем, есть ли время в строке
                time_match = re.search(r'в\s*(\d{1,2}(?::\d{2})?\s*(?:am|pm|утра|вечера|дня|ночи)?)', time_str)
                if time_match:
                    time_part = time_match.group(1)
                    if user.pk:
                        utc_offset = int(user.timezone[1:])
                    else:
                        utc_offset = 3
                    offset = timedelta(hours=utc_offset)
                    custom_timezone = timezone.get_fixed_timezone(offset=offset)
                    parsed_time = dateparser.parse(time_part, settings={
                        'PREFER_DATES_FROM': 'future',
                        'TIMEZONE': str(custom_timezone),
                        'RETURN_AS_TIMEZONE_AWARE': False,
                    })
                    if parsed_time:
                        reminder_time = target_date.replace(
                            hour=parsed_time.hour,
                            minute=parsed_time.minute,
                            second=0,
                            microsecond=0
                        )
                    else:
                        # Если не удалось распарсить время, устанавливаем 9:00
                        reminder_time = target_date.replace(hour=9, minute=0, second=0, microsecond=0)
                else:
                    # Если времени нет, устанавливаем 9:00
                    reminder_time = target_date.replace(hour=9, minute=0, second=0, microsecond=0)
            else:
                reminder_time = now + timedelta(minutes=number)
    
    # Обработка "завтра", "послезавтра"
    elif 'завтра' in time_str or 'after tomorrow' in time_str:
        # Проверяем и в исходном тексте, и в time_str для корректного определения "послезавтра"
        is_day_after_tomorrow = (
            'послезавтра' in text.lower() or 
            'после завтра' in text.lower() or 
            'after tomorrow' in time_str or
            'послезавтра' in time_str.lower()
        )
        
        if is_day_after_tomorrow:
            target_date = now + timedelta(days=2)
        else:
            target_date = now + timedelta(days=1)
        
        # Извлекаем время если есть
        time_match = re.search(r'(\d{1,2}(?::\d{2})?\s*(?:am|pm|утра|вечера|дня|ночи)?)', time_str)
        if time_match:
            time_part = time_match.group(1)
            if user.pk:
                utc_offset = int(user.timezone[1:])
            else:
                utc_offset = 3
            offset = timedelta(hours=utc_offset)
            custom_timezone = timezone.get_fixed_timezone(offset=offset)
            parsed_time = dateparser.parse(time_part, settings={
                'PREFER_DATES_FROM': 'future',
                'TIMEZONE': str(custom_timezone),
                'RETURN_AS_TIMEZONE_AWARE': False,
            })
            if parsed_time:
                reminder_time = target_date.replace(
                    hour=parsed_time.hour,
                    minute=parsed_time.minute,
                    second=0,
                    microsecond=0
                )
        
        if not reminder_time:
            reminder_time = target_date.replace(hour=9, minute=0, second=0, microsecond=0)
    
    # Обработка дней недели
    elif any(day in time_str.lower() for day in ['понедельник', 'вторник', 'среду', 'четверг', 'пятницу', 'субботу', 'воскресенье']):
        # Находим день недели (более гибкий поиск)
        weekday_match = re.search(r'(?:в\s*|на\s*|эту\s*|этот\s*|это\s*|следующий\s*|следующую\s*)?(понедельник|вторник|среду|четверг|пятницу|субботу|воскресенье)', time_str, re.IGNORECASE)
        if weekday_match:
            full_match = weekday_match.group(0)
            day_name = weekday_match.group(1)
            target_weekday = get_weekday_number(day_name)
            
            # Проверяем, есть ли указание на "следующий/следующую"
            force_next_week = 'следующий' in full_match.lower() or 'следующую' in full_match.lower()
            
            if target_weekday is not None:
                target_date = calculate_next_weekday(target_weekday, force_next_week=force_next_week)
                
                # Сначала проверяем простые временные указания
                if 'вечером' in time_str or 'вечер' in time_str:
                    reminder_time = target_date.replace(hour=19, minute=0, second=0, microsecond=0)
                elif 'утром' in time_str or 'утро' in time_str:
                    reminder_time = target_date.replace(hour=9, minute=0, second=0, microsecond=0)
                elif 'ночью' in time_str or 'ночь' in time_str:
                    reminder_time = target_date.replace(hour=22, minute=0, second=0, microsecond=0)
                elif 'в обед' in time_str or 'обед' in time_str:
                    reminder_time = target_date.replace(hour=13, minute=0, second=0, microsecond=0)
                else:
                    # Извлекаем время если есть более сложные паттерны
                    time_match = re.search(r'(\d{1,2}(?::\d{2})?\s*(?:am|pm|утра|вечера|дня|ночи)?)', time_str)
                    if time_match:
                        time_part = time_match.group(1)
                        reminder_time = calculate_next_weekday(target_weekday, time_part, force_next_week=force_next_week)
                    else:
                        # Если время не указано, устанавливаем на 9:00
                        reminder_time = target_date.replace(hour=9, minute=0, second=0, microsecond=0)
    
    # Дополнительная проверка для дней недели без предлогов (в начале строки)
    if not reminder_time:
        # Проверяем, начинается ли строка с дня недели
        weekday_start_match = re.match(r'^(?:эту\s*|этот\s*|это\s*|следующий\s*|следующую\s*)?(понедельник|вторник|среда|среду|четверг|пятница|пятницу|суббота|субботу|воскресенье)', time_str, re.IGNORECASE)
        if weekday_start_match:
            full_match = weekday_start_match.group(0)
            day_name = weekday_start_match.group(1)
            target_weekday = get_weekday_number(day_name)
            
            # Проверяем, есть ли указание на "следующий/следующую"
            force_next_week = 'следующий' in full_match.lower() or 'следующую' in full_match.lower()
            
            if target_weekday is not None:
                target_date = calculate_next_weekday(target_weekday, force_next_week=force_next_week)
                
                # Сначала проверяем простые временные указания
                if 'вечером' in time_str or 'вечер' in time_str:
                    reminder_time = target_date.replace(hour=19, minute=0, second=0, microsecond=0)
                elif 'утром' in time_str or 'утро' in time_str:
                    reminder_time = target_date.replace(hour=9, minute=0, second=0, microsecond=0)
                elif 'ночью' in time_str or 'ночь' in time_str:
                    reminder_time = target_date.replace(hour=22, minute=0, second=0, microsecond=0)
                elif 'в обед' in time_str or 'обед' in time_str:
                    reminder_time = target_date.replace(hour=13, minute=0, second=0, microsecond=0)
                else:
                    # Извлекаем время если есть более сложные паттерны
                    time_match = re.search(r'(\d{1,2}(?::\d{2})?\s*(?:am|pm|утра|вечера|дня|ночи)?)', time_str)
                    if time_match:
                        time_part = time_match.group(1)
                        reminder_time = calculate_next_weekday(target_weekday, time_part, force_next_week=force_next_week)
                    else:
                        # Если время не указано, устанавливаем на 9:00
                        reminder_time = target_date.replace(hour=9, minute=0, second=0, microsecond=0)
    
    # Обычный парсинг времени (только если время еще не установлено)
    if not reminder_time:        
        if user.pk:
            utc_offset = int(user.timezone[1:])
        else:
            utc_offset = 3
        offset = timedelta(hours=utc_offset)
        custom_timezone = timezone.get_fixed_timezone(offset=offset)
        settings = {
            'PREFER_DATES_FROM': 'future',
            'TIMEZONE': str(custom_timezone),
            'RETURN_AS_TIMEZONE_AWARE': False,
            'PREFER_DAY_OF_MONTH': 'first',
            'DATE_ORDER': 'DMY'
        }
        reminder_time = timezone.make_aware(dateparser.parse(time_str, settings=settings), timezone=custom_timezone)
        print(dateparser)
        if reminder_time and reminder_time < now:
            reminder_time += timedelta(days=1)
    
    # Обработка циклических напоминаний без конкретного времени
    if not reminder_time and repeat_type:
        if repeat_type == 'daily_morning':
            reminder_time = now.replace(hour=8, minute=0, second=0, microsecond=0)
            if reminder_time <= now:
                reminder_time += timedelta(days=1)
            repeat_type = 'daily'  # Меняем на обычный daily
        elif repeat_type == 'daily_evening':
            reminder_time = now.replace(hour=20, minute=0, second=0, microsecond=0)
            if reminder_time <= now:
                reminder_time += timedelta(days=1)
            repeat_type = 'daily'  # Меняем на обычный daily
        elif repeat_type == 'weekly' and 'каждую неделю' in time_str:
            # Устанавливаем на следующий понедельник в 9:00
            reminder_time = calculate_next_weekday(0, None)  # 0 = понедельник
        elif repeat_type == 'daily' and 'каждый день' in time_str:
            # Устанавливаем на завтра в 9:00
            reminder_time = now.replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=1)
    
    if not reminder_time:
        return None, None, text, None
    
    # Создаем время для предварительного напоминания (за 15 минут)
    pre_reminder_time = reminder_time - timedelta(minutes=15)
        
    if user.pk:
        utc_offset = int(user.timezone[1:])
    else:
        utc_offset = 3
    offset = timedelta(hours=utc_offset)
    custom_timezone = timezone.get_fixed_timezone(offset=offset)
    return timezone.make_naive(reminder_time, timezone=custom_timezone), timezone.make_naive(pre_reminder_time, timezone=custom_timezone), reminder_text, repeat_type

def clean_reminder_text(text: str, time_str: str) -> str:
    """
    Очищает текст напоминания от временных меток и лишних слов
    """
    # Удаляем найденную временную строку
    cleaned = text.replace(time_str, '').strip()
    
    # Удаляем дублированные временные указания
    time_artifacts = [
        'after tomorrow', 'завтра', 'послезавтра', 'после завтра',
        'понедельник', 'вторник', 'среда', 'среду', 'четверг', 
        'пятница', 'пятницу', 'суббота', 'субботу', 'воскресенье',
        'каждый день', 'каждую неделю', 'каждое утро', 'каждый вечер',
        'следующий', 'следующую', 'следующий понедельник', 'следующую пятницу',
        'следующий вторник', 'следующую среду', 'следующий четверг',
        'следующую субботу', 'следующее воскресенье'
    ]
    
    # Удаляем временные артефакты из текста
    cleaned_lower = cleaned.lower()
    for artifact in time_artifacts:
        # Удаляем если стоит отдельным словом или в начале
        pattern = rf'\b{re.escape(artifact)}\b'
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE).strip()
    
    # Удаляем артефакты после замены (отдельные буквы и короткие слова)
    words = cleaned.split()
    words = [word for word in words if len(word) > 1 or word.lower() in ['я', 'в', 'с', 'к', 'о', 'у']]
    cleaned = ' '.join(words)
    
    # Удаляем служебные слова в начале
    service_words_start = ['напомни', 'напомнить', 'поставь', 'поставить', 'создай', 'создать', 'добавь', 'добавить']
    service_phrases_start = ['напомни мне', 'напомнить мне', 'поставь напоминание', 'создай напоминание']
    
    # Удаляем вводные фразы и слова в начале
    intro_phrases = [
        'слушай неплохо было бы мне помнить',
        'слушай неплохо было бы',
        'неплохо было бы мне помнить', 
        'неплохо было бы',
        'мне нужно помнить',
        'нужно помнить',
        'я хочу помнить',
        'хочу помнить',
        'хотелось бы помнить',
        'надо помнить',
        'стоит помнить',
        'слушай',
        'кстати',
        'между прочим',
        'мне нужно',
        'нужно',
        'надо'
    ]
    
    # Сначала удаляем длинные вводные фразы
    cleaned_lower = cleaned.lower()
    for phrase in intro_phrases:
        if cleaned_lower.startswith(phrase):
            cleaned = cleaned[len(phrase):].strip()
            cleaned_lower = cleaned.lower()
            break
    
    # Затем удаляем длинные служебные фразы
    for phrase in service_phrases_start:
        if cleaned_lower.startswith(phrase):
            cleaned = cleaned[len(phrase):].strip()
            cleaned_lower = cleaned.lower()
            break
    
    # Затем удаляем отдельные служебные слова
    for word in service_words_start:
        if cleaned_lower.startswith(word):
            cleaned = cleaned[len(word):].strip()
            cleaned_lower = cleaned.lower()
            break
    
    # Удаляем вежливые слова
    polite_words = ['пожалуйста', 'пожалуйста,', 'будь добр', 'будь добра']
    for word in polite_words:
        cleaned = cleaned.replace(word, '').strip()
    
    # Удаляем артефакты после нормализации
    artifacts_to_remove = ['am', 'pm', 'каждый', 'каждую', 'мне']
    
    for artifact in artifacts_to_remove:
        # Удаляем артефакт если он в начале или стоит отдельным словом
        if cleaned.startswith(artifact):
            cleaned = cleaned[len(artifact):].strip()
        # Удаляем отдельно стоящие артефакты
        words = cleaned.split()
        cleaned = ' '.join(word for word in words if word not in artifacts_to_remove)
    
    # Специальная обработка для одиночных предлогов в начале
    single_prepositions = ['в', 'на', 'с', 'к', 'от', 'до', 'для', 'под', 'над', 'за', 'при', 'через']
    words = cleaned.split()
    if len(words) > 1 and words[0].lower() in single_prepositions:
        cleaned = ' '.join(words[1:])
    
    # Убираем лишние пробелы и знаки препинания в начале
    cleaned = cleaned.strip(' .,!?:;')
    
    return cleaned.strip()

def parse_date_query(query_text: str, user):
    """
    Парсит запрос на удаление и определяет целевую дату
    Возвращает дату в формате 'YYYY-MM-DD' или None
    """
    query_lower = query_text.lower().strip()
    current_time = get_now(user=user)
    
    # Сегодня
    if any(word in query_lower for word in ['сегодня', 'сегодняшние', 'на сегодня']):
        return current_time.strftime('%Y-%m-%d')
    
    # Завтра
    if any(word in query_lower for word in ['завтра', 'завтрашние', 'на завтра']):
        tomorrow = current_time + timedelta(days=1)
        return tomorrow.strftime('%Y-%m-%d')
    
    # Вчера
    if any(word in query_lower for word in ['вчера', 'вчерашние', 'на вчера']):
        yesterday = current_time - timedelta(days=1)
        return yesterday.strftime('%Y-%m-%d')
    
    # Послезавтра
    if any(word in query_lower for word in ['послезавтра', 'на послезавтра']):
        day_after_tomorrow = current_time + timedelta(days=2)
        return day_after_tomorrow.strftime('%Y-%m-%d')
    
    # Дни недели
    weekdays = {
        'понедельник': 0, 'пн': 0,
        'вторник': 1, 'вт': 1,
        'среда': 2, 'ср': 2, 'среду': 2,
        'четверг': 3, 'чт': 3,
        'пятница': 4, 'пт': 4, 'пятницу': 4,
        'суббота': 5, 'сб': 5, 'субботу': 5,
        'воскресенье': 6, 'вс': 6
    }
    
    for weekday_name, weekday_num in weekdays.items():
        if weekday_name in query_lower:
            # Находим ближайший день недели
            days_ahead = weekday_num - current_time.weekday()
            if days_ahead <= 0:  # Если сегодня или прошло, берем следующую неделю
                days_ahead += 7
            target_date = current_time + timedelta(days=days_ahead)
            return target_date.strftime('%Y-%m-%d')
    
    # Конкретные даты (например, "15 января", "31.12")
    # Паттерн для дат вида "15 января" или "15.01"
    date_patterns = [
        r'(\d{1,2})\s+(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)',
        r'(\d{1,2})\.(\d{1,2})(?:\.(\d{2,4}))?',
        r'(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?'
    ]
    
    months_dict = {
        'января': 1, 'февраля': 2, 'марта': 3, 'апреля': 4,
        'мая': 5, 'июня': 6, 'июля': 7, 'августа': 8,
        'сентября': 9, 'октября': 10, 'ноября': 11, 'декабря': 12
    }
    
    for pattern in date_patterns:
        match = re.search(pattern, query_lower)
        if match:
            try:
                if 'января' in pattern or 'февраля' in pattern:  # Месяц словом
                    day = int(match.group(1))
                    month = months_dict[match.group(2)]
                    year = current_time.year
                    
                    # Если дата уже прошла в этом году, берем следующий год
                    target_date = datetime(year, month, day)
                    if target_date.date() < current_time.date():
                        target_date = datetime(year + 1, month, day)
                    
                    return target_date.strftime('%Y-%m-%d')
                
                else:  # Числовой формат
                    day = int(match.group(1))
                    month = int(match.group(2))
                    year = int(match.group(3)) if match.group(3) else current_time.year
                    
                    # Если год двузначный, делаем его четырехзначным
                    if year < 100:
                        year += 2000
                    
                    target_date = datetime(year, month, day)
                    return target_date.strftime('%Y-%m-%d')
                    
            except (ValueError, KeyError):
                continue
    
    return None 