import os
import base64
import json
from datetime import datetime

import dotenv
import openai
from ..utils.timezone import get_moscow_now, format_moscow_time

dotenv.load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")

def get_current_datetime_info():
    """Получает текущую дату и время для ИИ"""
    now = get_moscow_now()
    weekdays = ['понедельник', 'вторник', 'среда', 'четверг', 'пятница', 'суббота', 'воскресенье']
    current_weekday = weekdays[now.weekday()]
    
    return f"""
ТЕКУЩАЯ ДАТА И ВРЕМЯ (Москва):
- Дата: {now.strftime('%d.%m.%Y')}
- Время: {now.strftime('%H:%M')}
- День недели: {current_weekday}
- Полная дата: {format_moscow_time(now)}

ВАЖНО: Используй эту информацию для правильного вычисления относительных дат!
"""

ASSISTANT_PROMPT = """Ты - ИИ-помощник бота для напоминаний и задач. Твоя задача - анализировать сообщения пользователей и определять, хочет ли пользователь:
1. Создать напоминание 
2. Удалить напоминание
3. Создать задачу 
4. Удалить задачу
5. Просто пообщаться или задать вопрос

КРИТИЧЕСКИ ВАЖНО: НИКОГДА не говори "не могу установить напоминания или задачи" или "не могу создавать напоминания или задачи"! ТЫ МОЖЕШЬ И ДОЛЖНА помогать с напоминаниями и задачами!

ВСЕГДА отвечай в одном из трех форматов:

1. Если пользователь хочет создать напоминание, отвечай ТОЛЬКО в JSON формате:
{
  "type": "reminder",
  "text": "КОРОТКОЕ название задачи БЕЗ временных указаний",
  "time": "время в естественном формате"
}

2. Если пользователь хочет удалить напоминание, отвечай ТОЛЬКО в JSON формате:
{
  "type": "delete",
  "item": "reminder",
  "text": "ключевые слова для поиска напоминания"
}

3. Если пользователь хочет создать задачу, отвечай ТОЛЬКО в JSON формате:
{
  "type": "task",
  "text": "КОРОТКОЕ название задачи БЕЗ временных указаний",
  "time": "время в естественном формате"
}

4. Если пользователь хочет удалить задачу, отвечай ТОЛЬКО в JSON формате:
{
  "type": "delete",
  "item": "task",
  "text": "ключевые слова для поиска напоминания"
}

5. Если пользователь просто общается или задает вопросы, отвечай обычным текстом.

КРИТИЧЕСКИ ВАЖНО для поля "text" в создании напоминаний и задач - создавай КОРОТКИЕ, ПОНЯТНЫЕ названия:
✅ ПРАВИЛЬНО:
- "напомни мне пожалуйста через 10 дней побрить кота" → "Побрить кота"
- "завтра в 15:00 нужно сходить к врачу на прием" → "Прием у врача"
- "каждый день в 22:00 принимать витамины" → "Принимать витамины"
- "послезавтра в обед покормить рыбок" → "Покормить рыбок"
- "в среду в 2 дня встреча с коллегами" → "Встреча с коллегами"

Тебе нужно различать напоминания и задачи. Если в сообщениях чётко упомянуто слово задача, то это будет задача, если слово напоминание, то это напоминание.
Если по смыслу тяжело понять, то выбирай напоминание.

❌ НЕПРАВИЛЬНО:
- "напомни мне пожалуйста побрить кота" (оставляешь лишние слова)
- "завтра побрить кота" (включаешь временные указания)
- "нужно побрить кота" (оставляешь служебные слова)

КРИТИЧЕСКИ ВАЖНО для поля "time" - понимай ЛЮБЫЕ формы времени:
✅ Понимай и правильно интерпретируй:
- "послезавтра" = через 2 дня от сегодня
- "в эту среду" = ближайшая среда
- "в среду в 2" = в ближайшую среду в 14:00 (если контекст дневной)
- "в среду в 2 ночи" = в ближайшую среду в 02:00
- "послезавтра в обед" = через 2 дня в 13:00
- "через неделю в пятницу" = в пятницу через неделю
- "на следующей неделе в понедельник" = понедельник следующей недели

ПРАВИЛА для времени дня:
- "в обед" = 13:00
- "утром" = 09:00 (если не указано точное время)
- "вечером" = 19:00 (если не указано точное время)
- "ночью" = 22:00 (если не указано точное время)
- "в 2" в дневном контексте = 14:00
- "в 2 ночи" = 02:00
- "в 2 дня" = 14:00

КРИТИЧЕСКИ ВАЖНО для удаления напоминаний и задач - понимай запросы на удаление:
✅ Примеры запросов на удаление:
- "удали напоминание про кота" → {"type": "delete", "item": "reminder", "text": "кот"}
- "убери напоминание о встрече" → {"type": "delete", "item": "reminder", "text": "встреча"}
- "отмени задачу принимать витамины" → {"type": "delete", "item": "task", "text": "витамины"}
- "удали все напоминания про врача" → {"type": "delete", "item": "reminder", "text": "врач"}
- "убери задачу покормить рыбок" → {"type": "delete", "item": "task", "text": "рыбки"}
- "отмени завтрашнее напоминание про собаку" → {"type": "delete", "item": "reminder", "text": "собака"}
- "удали задачи на завтра" → {"type": "delete", "item": "task", "text": "завтра"}

Ключевые слова для определения удаления:
- "удали", "убери", "отмени", "удалить", "убрать", "отменить"
- "удали напоминание", "убери напоминание", "отмени напоминание"
- "удали задачу", "убери задачу", "отмени задачу"
- "не нужно больше напоминать"

Примеры правильной обработки:
- "послезавтра в обед покормить кота" → text: "Покормить кота", time: "послезавтра в 13:00"
- "в эту среду в 2 встреча" → text: "Встреча", time: "в среду в 14:00"
- "через неделю в пятницу утром к врачу" → text: "К врачу", time: "через неделю в пятницу в 09:00"

ОСОБЕННО ВАЖНО: Если пользователь хочет создать напоминание или задачу, но НЕ указал время:
1. Понять, что это запрос на напоминание или задачу
2. Попросить уточнить время в дружелюбном тоне
3. НИКОГДА НЕ отказываться создавать напоминание

Примеры запросов БЕЗ ВРЕМЕНИ (обязательно помоги, но попроси уточнить):
- "Напомни покормить кота" → "Конечно! На какое время поставить задачу покормить кота? Например: 'завтра в 8 утра' или 'каждый день в 18:00'"
- "Поставь напоминание встреча" → "Хорошо! Когда напомнить о встрече? Укажите время, например: 'в понедельник в 15:30' или 'завтра в 14:00'"

ЗАПОМНИ: Ты ВСЕГДА можешь помочь с напоминаниями и задачами! Просто попроси уточнить время, если его нет."""
ANALYTIC_PROMPT = 'settings.ANALYTIC_PROMPT'

openai.base_url = "https://api.vsegpt.ru:6070/v1/"


class BaseAIAPI:
    def __init__(self, ) -> None:
        self._ASSISTANT_PROMPT: str = ASSISTANT_PROMPT
        self.chat_history: dict = {}
        self._TEMPERATURE = 0.7

    def clear_chat_history(self, chat_id: int) -> None:
        self.chat_history.pop(chat_id)

    def parse_ai_response(self, response_text: str) -> dict:
        """
        Парсит ответ ИИ и определяет тип ответа
        Возвращает словарь с типом ответа и данными
        """
        response_text = response_text.strip()
        # ОТЛАДКА: выводим сырой ответ ИИ
        print(f"=== СЫРОЙ ОТВЕТ ИИ ===")
        if '{' in response_text:
            print(f"'{response_text[response_text.index('{'):response_text.index('}') + 1]}'")
        else:
            print(f"'{response_text}'")
        print("====================")

        # Пытаемся распарсить как JSON
        try:
            parsed_json = json.loads(response_text)
            if parsed_json.get('type') == 'reminder':
                result = {
                    'type': 'reminder',
                    'reminder_text': parsed_json.get('text', ''),
                    'time_text': parsed_json.get('time', '')
                }
                # ОТЛАДКА: выводим распарсенный результат
                print(f"=== РАСПАРСЕННЫЙ JSON (REMINDER) ===")
                print(f"text: '{result['reminder_text']}'")
                print(f"time: '{result['time_text']}'")
                print("===================================")
                return result
            elif parsed_json.get('type') == 'task':
                result = {
                    'type': 'task',
                    'reminder_text': parsed_json.get('text', ''),
                    'time_text': parsed_json.get('time', '')
                }
                # ОТЛАДКА: выводим распарсенный результат
                print(f"=== РАСПАРСЕННЫЙ JSON (REMINDER) ===")
                print(f"text: '{result['reminder_text']}'")
                print(f"time: '{result['time_text']}'")
                print("===================================")
                return result
            elif parsed_json.get('type') == 'delete':
                result = {
                    'type': 'delete',
                    'search_text': parsed_json.get('text', '')
                }
                # ОТЛАДКА: выводим распарсенный результат
                print(f"=== РАСПАРСЕННЫЙ JSON (DELETE) ===")
                print(f"search_text: '{result['search_text']}'")
                print("==================================")
                return result
        except json.JSONDecodeError as e:
            pass
        
        # Если не JSON или не напоминание/удаление, возвращаем как обычный ответ
        return {
            'type': 'conversation',
            'message': response_text
        }


class OpenAIAPI(BaseAIAPI):
    """API for working with https://vsegpt.ru/Docs/API"""

    def __init__(self, ) -> None:
        super().__init__()

    def _get_or_create_user_chat_history(self, chat_id: int, new_user_message: str = "",
                                         tone=None, addressing=None) -> list:
        
        sets_text = ''
        if not tone is None:
            sets_text += f'ОБЯЗАТЕЛЬНО ВЕДИ ДИАЛОГ В СЛЕДУЮЩЕМ СТИЛЕ: {tone}\n\n'
        if not addressing is None:
            sets_text += f'ОБРАЩАЙСЯ ТОЛЬКО НА {addressing}'

        if not self.chat_history.get(chat_id, False):
            self.chat_history[chat_id] = []
            # Добавляем системный промпт с текущей датой и временем
            system_prompt = self._ASSISTANT_PROMPT + "\n\n" + sets_text
            self.chat_history[chat_id].append({"role": "system", "content": system_prompt})
            self.chat_history[chat_id].append({"role": "user", "content": new_user_message})
            return self.chat_history[chat_id]
        if sets_text != '':
            self.chat_history[chat_id].append({"role": "system", "content": sets_text})
        self.chat_history[chat_id].append({"role": "user", "content": new_user_message})
        chat_history = self.chat_history[chat_id]
        return chat_history

    def get_response(self, chat_id: int, text: str, model: str, max_token: int =1024,
            tone=None, addressing=None) -> dict:
        """
        Make request to AI and write answer to message_history.
        Usually working in chats with AI.
        """
        # ОТЛАДКА: выводим исходное сообщение пользователя
        print(f"=== СООБЩЕНИЕ ПОЛЬЗОВАТЕЛЯ ===")
        print(f"'{text}'")
        print("=============================")
        
        user_chat_history = self._get_or_create_user_chat_history(chat_id, text, tone, addressing)

        try:
            response = (
                openai.chat.completions.create(
                    model=model,
                    messages=user_chat_history,
                    temperature=self._TEMPERATURE,
                    n=1,
                    max_tokens=max_token, )
            )

            answer = {"message": response.choices[0].message.content, "total_cost": response.usage.total_cost}
            self.chat_history[chat_id].append({"role": "assistant", "content": answer["message"]})

            return answer

        except Exception as e:
            #self.clear_chat_history(chat_id)
            print(e)

    def add_txt_to_user_chat_history(self, chat_id: int, text: str) -> None:
        try:
            self._get_or_create_user_chat_history(chat_id, text)
        except Exception as e: 
            #logger.error(f'Error occurred while adding text: {e} to user chat history')
            print("Error occurred while adding text to user chat history")