from joshu.celery import app
from joshu.settings import ALLOWED_HOSTS
import logging
from django.core.mail import send_mail
from joshuAPI.models import JoshuUser, Task
from telegram_bot.bot import JoshuBot
from joshu import settings
from django.template.loader import render_to_string


BOT_TOKEN = settings.BOT_TOKEN


""" ================= !!! ПРИ ЛЮБЫХ ИЗМЕНЕНИЯХ В ЭТОМ ФАЙЛЕ, ПЕРЕЗАПУСКАЕМ CELERY !!! ================="""
"""
sudo /etc/init.d/celeryd restart
sudo /etc/init.d/celeryd start
sudo /etc/init.d/celeryd stop
sudo /etc/init.d/celeryd status
"""


@app.task
def send_email_delegating_task(pk, current_task_id, chat_bot=False):
    author = JoshuUser.objects.get(pk=pk)
    joshubot = JoshuBot(BOT_TOKEN)
    chat_id = author.chat_id
    current_task = Task.objects.get(tid=current_task_id)

    if ALLOWED_HOSTS[0] != '127.0.0.1':
        host = 'http://' + ALLOWED_HOSTS[0]
    else:
        host = 'http://127.0.0.1:8000'

    context = {
        'author': author,
        'host': host,
        'text_data': current_task.text,
        'dateTime': current_task.dateTime,
        'current_task': current_task
    }
    current_task.status = 1     # Изменяем статус задачи на "жду"
    current_task.save()

    subject = f'Делегирование задачи пользователя {author.displayName}'
    body_text = render_to_string('email/new_task.txt', context)

    # отправляем письмо на сторонний сервис
    email_sent = send_mail(
        subject,
        body_text,
        settings.EMAIL_HOST_USER,
        [settings.EMAIL_BOX],
        fail_silently=False,
    )

    if email_sent > 0:
        print("Delegating a task email sent successfully")
        if chat_bot:
            joshubot.send_message(chat_id=chat_id, text='Письмо с поставленной задачей отправлено на стронний сервис')
            joshubot.send_message(chat_id=chat_id, text='Ждите ответа на указанный в профиле почтовый ящик')

    # отправляем дубль письма создателю задачи
    context = {
        'author': author,
        'host': host,
        'text_data': current_task.text,
        'dateTime': current_task.dateTime,
        'current_task': current_task
    }
    body_text = render_to_string('email/new_task_return_author.txt', context)

    if chat_bot:
        joshubot.send_message(chat_id=chat_id, text=f'Отправляем дубль письма создателю задачи на {author.email}')
    email_sent = send_mail(
        subject,
        body_text,
        settings.EMAIL_HOST_USER,
        [author.email],
        fail_silently=False,
    )
    if email_sent > 0:
        logging.info(f"Email пользователю \'{author}\' отправлен.")
    else:
        logging.info(f"Ошибка отправки Email пользователю \'{author}\'.")
