from django.contrib import admin

from .models import Reminder, Task

admin.site.register([Reminder, Task])