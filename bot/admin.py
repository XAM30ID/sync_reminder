from django.contrib import admin

from .models import Reminder, Task, UserProfile

admin.site.register([Reminder, Task, UserProfile])