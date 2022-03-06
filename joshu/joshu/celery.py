# from __future__ import absolute_import
import os

from celery import Celery
from celery.schedules import crontab
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'joshu.settings')

app = Celery('joshu')
app.config_from_object('django.conf:settings')

app.autodiscover_tasks()

app.conf.beat_schedule = {
    'bot_notify_task': {
        'task': 'telegram_bot.tasks.bot_notify_task',
        'schedule': crontab(minute='*/1'),  # change to `crontab(minute=0, hour=0)` if you want it to run daily at midnight
    },
}

# Load task modules from all registered Django app configs.

