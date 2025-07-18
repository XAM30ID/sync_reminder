import os
import pytz

from django.db import models
from django.core.files.storage import FileSystemStorage

from main.settings import BASE_DIR


fs = FileSystemStorage(location=f"{BASE_DIR}/media")

class UserProfile(models.Model):
    '''
        Модель для хранения информации о пользователе
    '''
    user_id = models.IntegerField(verbose_name='ID пользователя в Telegram', primary_key=True)
    username = models.TextField(verbose_name='Ник пользователя в Telegram', blank=True)
    addressing = models.CharField(verbose_name='Обращение', choices={'ty': 'Ты', 'vy': 'Вы'})
    tone = models.CharField(verbose_name='Тон общения', choices={'business': 'Деловой', 'friendly': 'Дружелюбный', 'neutral': 'Нейтральный'})
    timezone = models.CharField(verbose_name='Часовой пояс', default='+3', help_text='Разница с UTC в формате "±0"')

    def __str__(self):
        return f'Пользователь {self.username}'
    
    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'


class Reminder(models.Model):
    '''
        Модель напоминания
    '''
    REPEAT_TYPES = {
        'daily': 'Каждый день',
        'weekly': 'Каждую неделю',
    }
    
    user = models.ForeignKey(to=UserProfile, verbose_name='Пользователь', on_delete=models.CASCADE)
    text = models.TextField(verbose_name='Текст напоминания')
    reminder_time = models.DateTimeField(verbose_name='Дата и время напоминания')
    pre_reminder_time = models.DateTimeField(verbose_name='Дата и время напоминания заранее')
    is_pre_reminder_sent = models.BooleanField(verbose_name='Напоминание заранее отправлено')
    is_main_reminder_sent = models.BooleanField(verbose_name='Напоминание отправлено')
    created_at = models.DateTimeField(verbose_name='Создано')
    repeat_type = models.TextField(verbose_name='Повторение', choices=REPEAT_TYPES, null=True, blank=True)
    repeat_time = models.DateTimeField(verbose_name='Дата и время повторения', null=True, blank=True)

    def __str__(self):
        return f'Напоминание пользователя от {self.reminder_time} {self.user.username} {self.text}'
    
    class Meta:
        verbose_name = 'Напоминание'
        verbose_name_plural = 'Напоминания'


class Task(models.Model):
    '''
        Модель задачи
    '''
    REPEAT_TYPES = {
        'daily_morning': 'Каждое утро',
        'daily_evening': 'Каждый вечер',
        'daily': 'Каждый день',
        'weekly': 'Каждую неделю',
    }
    
    user = models.ForeignKey(to=UserProfile, verbose_name='Пользователь', on_delete=models.CASCADE)
    text = models.TextField(verbose_name='Текст задачи')
    reminder_time = models.DateTimeField(verbose_name='Дата и время напоминания')
    pre_reminder_time = models.DateTimeField(verbose_name='Дата и время напоминания заранее')
    is_completed = models.BooleanField(verbose_name='Задача завершена')
    is_transfered = models.BooleanField(verbose_name='Задача перенесена')
    transfer_time = models.DateTimeField(verbose_name='Время переноса', null=True, blank=True)
    is_pre_reminder_sent = models.BooleanField(verbose_name='Напоминание заранее отправлено')
    is_main_reminder_sent = models.BooleanField(verbose_name='Напоминание отправлено')
    created_at = models.DateTimeField(verbose_name='Создано')
    repeat_type = models.TextField(verbose_name='Повторение', choices=REPEAT_TYPES, null=True, blank=True)
    repeat_time = models.DateTimeField(verbose_name='Дата и время повторения', null=True, blank=True)

    def __str__(self):
        return f'Задача пользователя {self.user_id}'
    
    class Meta:
        verbose_name = 'Задача'
        verbose_name_plural = 'Задачи'
    

# Путь для стартового файла
def start_message_path(instance, filename):
    return os.path.join(f'images/start_file.{filename.split('.')[-1]}')


class GeneralInfo(models.Model):
    '''
        Модель общей информации
    '''
    start_message = models.TextField(verbose_name='Текст стартового сообщения')
    file = models.FileField(verbose_name='Файл', help_text='При необходимости. Будет отправляться, как сжатое изображение', null=True, blank=True, storage=fs, upload_to=start_message_path)
    
    def __str__(self):
        return f'Общая информация'
    
    class Meta:
        verbose_name = 'Общая информация'
        verbose_name_plural = 'Общая информация'

