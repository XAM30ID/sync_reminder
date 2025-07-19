# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, '/home/p/pacmaknl/test-bot-reminder/sync_reminder/')
sys.path.insert(1, '/home/p/pacmaknl/test-bot-reminder/sync_reminder/venv/lib/python3.13/site-packages')
os.environ['DJANGO_SETTINGS_MODULE'] = 'sync_reminder.settings'
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()