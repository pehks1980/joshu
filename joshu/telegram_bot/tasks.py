import logging
from datetime import datetime

from django.utils.timezone import now
from telebot import types
from joshu import settings
from joshu.celery import app
from joshuAPI.models import Task, JoshuUser
from telegram_bot.bot import JoshuBot
from logs.server_log_config import server_app_info, server_app_error

BOT_TOKEN = settings.BOT_TOKEN

""" ================= !!! ПРИ ЛЮБЫХ ИЗМЕНЕНИЯХ В ЭТОМ ФАЙЛЕ, ПЕРЕЗАПУСКАЕМ CELERY и CELERYBEAT !!! ================="""
"""
sudo systemctl daemon-reload
sudo systemctl restart celery.service
sudo systemctl restart celerybeat.service
Последовательность команд перезапуска НЕ МЕНЯТЬ (celerybeat.service работает через celery.service)!

- Log -
sudo nano /var/log/celery/beat.log  # celerybeat
sudo nano /var/log/syslog           # системный
"""


# beating -
# celery -A joshu worker -l info -E -B #-B for beat

@app.task
def send_asinc_messages(chat_id, text, task_id=None, tid=None):
    joshubot = JoshuBot(BOT_TOKEN)

    try:
        joshubot.send_message(chat_id=chat_id, text=text)
        if task_id and tid:
            """
                Кнопка под напоминалкой
                """
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton(f'Посмотреть задачку id={task_id}', callback_data=f'show_task:{tid}'))
            markup.add(types.InlineKeyboardButton(f'Выключение уведомлений задачи id={task_id}',
                                                  callback_data=f'enable_notify:{tid}:0'))
            # joshubot.send_message(chat_id=chat_id, text='Выберите действие:', reply_markup=markup)
            joshubot.send_message(chat_id=chat_id, text='Выберите действие:', reply_markup=markup)
            logging.info(f"send_messages chat_id: <{chat_id}> is complete.")
    except:
            pass
    return 'Work "send_messages" is complete'


"""
def turn_notify_off_button(chat_id, task_id, tid):

    # Кнопка под напоминалкой

    # joshubot = JoshuBot(settings.BOT_TOKEN)
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(f'Посмотреть задачку id={task_id}', callback_data=f'show_task:{tid}'))
    markup.add(types.InlineKeyboardButton(f'Выключение уведомлений задачи id={task_id}',
                                          callback_data=f'enable_notify:{tid}:0'))
    # joshubot.send_message(chat_id=chat_id, text='Выберите действие:', reply_markup=markup)
    send_asinc_messages(chat_id=chat_id, text='Выберите действие:', reply_markup=markup)
"""


@app.task
def bot_notify_task():
    print('scheduler calling')
    server_app_info('scheduler calling')

    jobs = Task.objects.filter(enabled=True)  # на всякий случай
    # joshubot = JoshuBot(settings.BOT_TOKEN)

    for job in jobs:
        if job.dateTime is not None and job.shed_time is not None:
            # check the time to when to fire
            diff_time = job.dateTime - now()
            # convert secs to mins float
            diff_time_mins = float(diff_time.total_seconds() / 60)
            # it is local datetime (all server datetime is UTC, if you have tz you can calculate to local datetime)
            local_dateTime = job.dateTime.astimezone(job.task_user.tz)

            print(
                f' job for task id = {job.id} has {job.shed_time} mins period param, overdue = {job.overdue},  '
                f'overdue_done = {job.overdue_done} time difference : {diff_time_mins} (mins), current time {now()},'
                f' dateTime is {job.dateTime}, (lcl dateTime {local_dateTime}), '
                f'(notify last time fired : {job.last_fired_at}) '
            )
            try:
                if job.overdue:
                    # datetime_mins is negative and it has time since beginning of the task
                    if abs(diff_time_mins) >= job.shed_time and not job.overdue_done:
                        # get next time period in overdue (in signal)
                        # update time of last fire
                        job.last_fired_at = now()
                        job.save()

                        # notify chat_bot
                        if job.task_user.chat_id != '':
                            text = f'Напоминалка о задаче id = {job.id}  срок исполнения {local_dateTime} задачи истек.'
                            # joshubot.send_message(chat_id=job.task_user.chat_id, text=text)
                            # turn_notify_off_button(chat_id=job.task_user.chat_id, text=text, None, task_id=job.id, tid=job.tid)
                            send_asinc_messages.delay(chat_id=job.task_user.chat_id, text=text, task_id=job.id, tid=job.tid)

                elif job.shed_time == 0:
                    if diff_time_mins <= 0.2:
                        # time of task is due now, fire notification and set overdue flag (in signal)
                        job.last_fired_at = now()
                        job.save()
                        # notify chat_bot
                        if job.task_user.chat_id != '':
                            text = f'Напоминалка о задаче id = {job.id}  срок исполнения {local_dateTime} задача началась.'
                            """
                            joshubot.send_message(chat_id=job.task_user.chat_id, text=text)
                            turn_notify_off_button(chat_id=job.task_user.chat_id, task_id=job.id,
                                                   tid=job.tid)
                            """
                            send_asinc_messages.delay(chat_id=job.task_user.chat_id, text=text, task_id=job.id, tid=job.tid)

                elif diff_time_mins <= job.shed_time:
                    # each notify period is about to end here:
                    # set new nex_time_period, new shed_time (in signal)
                    shed_time = job.shed_time
                    job.last_fired_at = now()
                    job.save()
                    # fire notification to this user chatbot
                    # get task and information related
                    # notify chat_bot
                    if job.task_user.chat_id != '':
                        if shed_time > 60:
                            text = f'Напоминалка о задаче id = {job.id}  срок исполнения {local_dateTime} остался 1 день.'
                        else:
                            text = f'Напоминалка о задаче id = {job.id}  срок исполнения {local_dateTime} осталось {shed_time} минут.'
                        """        
                        joshubot.send_message(chat_id=job.task_user.chat_id, text=text)
                        turn_notify_off_button(chat_id=job.task_user.chat_id, task_id=job.id,
                                               tid=job.tid)
                        """
                        send_asinc_messages.delay(chat_id=job.task_user.chat_id, text=text, task_id=job.id, tid=job.tid)

            except:
                server_app_error(
                    f'Error! scheduler data: diff_time_mins={diff_time_mins}, job.shed_time={job.shed_time}')

    print('scheduler finished')
    server_app_info('scheduler finished')
    # joshubot.telebot_stop()
    return None

