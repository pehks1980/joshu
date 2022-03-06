import json
import telebot
from django.http import JsonResponse, HttpResponseBadRequest
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from telebot_calendar import CallbackData

from joshu import settings
from joshuAPI.models import JoshuUser
from .bot import JoshuBot

BOT_TOKEN = settings.BOT_TOKEN

calendar_1 = CallbackData("calendar_1", "action", "year", "month", "day")


class TelegramBotView(View):

    def __init__(self):
        super(TelegramBotView, self).__init__()

    def taskfolder_cb(self, message, chat_id):
        print(f'chat_id {chat_id}, message= {message}')
        self.bot.send_message(chat_id=chat_id, text=f'нажатие на кнопку.. {message}')

    def post(self, request):
        # make instance of telegram bot api as joshubot
        joshubot = JoshuBot(BOT_TOKEN)

        try:
            try:
                payload = json.loads(request.body.decode('utf-8'))

            except ValueError:
                return HttpResponseBadRequest('Invalid request body')

            if "message" in payload:
                if 'text' in payload['message']:
                    """----- Текстовая команда -----"""
                    chat_id = payload['message']['chat']['id']
                    cmd = payload['message'].get('text')
                    # check for auth command /start xxxxx to authenticate user and bot (chat_id)
                    # will return true if auth successful and do nothing if chat_id already connected with user
                    if joshubot.bot_authenticate(cmd, chat_id):
                        cmd = '/start'
                    user = JoshuUser.objects.filter(chat_id=chat_id, active=True)
                    if user:
                        current_user = user[0]
                        joshubot.handle(cmd, chat_id, current_user)
                    else:
                        joshubot.send_message(chat_id=chat_id,
                                              text='Для авторизации пожалуйста используйте уникальную ссылку в Joshu-приложении')

            elif "callback_query" in payload:
                if 'from' in payload['callback_query']:
                    if 'id' in payload['callback_query']['from']:
                        chat_id = payload['callback_query']['from']['id']
                        callback_query_id = payload['callback_query']['id']
                        user = JoshuUser.objects.filter(chat_id=chat_id, active=True)
                        if user:
                            current_user = user[0]
                            if 'data' in payload['callback_query']:
                                """----- Обработка кнопок -----"""
                                # joshubot.send_message(chat_id=chat_id, text='----- Обработка кнопок -----')
                                data_key = payload['callback_query']['data']
                                # handle of callback response
                                joshubot.callback_handle(chat_id, current_user, data_key)
                                # joshubot.send_message(chat_id=chat_id, text=f'Вы нажали \"{data_key}\"')
                                # finish cb with special 'api cb ack' to avoid 'clock wait on the button'
                                joshubot.answer_callback_query(callback_query_id)
                        else:

                            joshubot.send_message(chat_id=chat_id,
                                                  text='Для авторизации пожалуйста используйте уникальную '
                                                       'ссылку в Joshu-приложении')
                            joshubot.answer_callback_query(callback_query_id)

        # will print reason of problem
        except telebot.apihelper.ApiException as e:
            print(f'some telebot problem occured..{e}')

        return JsonResponse({}, status=200)

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(TelegramBotView, self).dispatch(request, *args, **kwargs)
