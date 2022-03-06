from celery_progress.backend import ProgressRecorder
from joshu import settings
from joshu.celery import app
from joshuAPI.models import JoshuUser
from main.models import AdmBotMessage, DataSendMessage
from telegram_bot.bot import JoshuBot


BOT_TOKEN = settings.BOT_TOKEN


""" ================= !!! ПРИ ЛЮБЫХ ИЗМЕНЕНИЯХ В ЭТОМ ФАЙЛЕ, ПЕРЕЗАПУСКАЕМ SELERY !!! ================="""
"""
sudo /etc/init.d/celeryd restart
sudo /etc/init.d/celeryd start
sudo /etc/init.d/celeryd stop
sudo /etc/init.d/celeryd status
"""


@app.task
def send_messages(messages_pk):
    pattern = '[\d]+'
    recipient = JoshuUser.objects.filter(chat_id__iregex=pattern)   # пользователи с ботом
    joshubot = JoshuBot(BOT_TOKEN)

    current_message = AdmBotMessage.objects.get(pk=messages_pk)  # само сообщение

    progress_recorder = ProgressRecorder(send_messages)

    # maintenance_source = [i for i in range(10)]
    total = len(recipient)

    for i, item_recipient in enumerate(recipient):
        chat_id = item_recipient.chat_id
        try:
            joshubot.send_message(chat_id=chat_id, text=current_message.description)
        except:
            pass
        
        progress_recorder.set_progress(i, total, )

    # сохраняем дату и время отправки
    save_message_dttm = DataSendMessage.objects.create(message=current_message)
    save_message_dttm.save()

    return 'Work "send_messages" is complete'


