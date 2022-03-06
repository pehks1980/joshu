import datetime
import re

import telebot
from django.utils.timezone import make_aware
from emoji import emojize
from joshuAPI.models import JoshuUser, Task, TaskFolder

from joshu import settings
from .bothand import BotHandler
from .bothandcb import BotCbHandler

#Настройки Токен для бот апи
BOT_TOKEN = settings.BOT_TOKEN


e_option = emojize(':arrow_down:', use_aliases=True)
e_calendar = emojize(':calendar:', use_aliases=True)
e_clipboard = emojize(':clipboard:', use_aliases=True)
e_folder = emojize(':file_folder:', use_aliases=True)
e_redcircle = emojize(':red_circle:', use_aliases=True)
e_bluecircle = emojize(':blue_circle:', use_aliases=True)
e_yellowcircle = emojize(':yellow_circle:', use_aliases=True)
e_whitecircle = emojize(':white_circle:', use_aliases=True)
e_greencircle = emojize(':green_circle:', use_aliases=True)
e_clock = emojize(':clock4:', use_aliases=True)
e_star = emojize(':star:', use_aliases=True)
e_x = emojize(':x:', use_aliases=True)


class JoshuBot:

    def __init__(self, token=BOT_TOKEN):
        # print('telebot_init_here')
        # init telebot instance and put it in the class view
        self.bot = telebot.TeleBot(token)

    def telebot_stop(self):
        self.bot.stop_bot()

    # verify and update user db with chat_id (authenticate)
    def verify_bot_key(self, bot_key, chat_id):
        try:
            # check if we already have such chat_id in user db to ensure rule: one user one bot
            user_with_such_chat_id_qs = JoshuUser.objects.filter(chat_id=chat_id, active=True)
            if not user_with_such_chat_id_qs.exists():
                # no active users with such chat_id in the db
                # find user with bot_key
                user_with_bot_key_qs = JoshuUser.objects.filter(bot_link_key=bot_key, active=True)
                if user_with_bot_key_qs.exists():
                    # found user.bot_link_key == bot_key
                    # check if it's empty (just in case)
                    if user_with_bot_key_qs[0].chat_id == '':
                        # check if link is not expired yet
                        if not user_with_bot_key_qs[0].is_bot_link_key_expired():
                            # update chat_id with additional 'get' as queryset can't update field...
                            user = JoshuUser.objects.get(bot_link_key=bot_key)
                            user.chat_id = str(chat_id)
                            user.save(update_fields=['chat_id'])
                            print(f'bot user auth successful, chat_id was updated')
                            return True
                        else:
                            print(f'bot_link expired: {user_with_bot_key_qs[0]}')
                            return False
                    else:
                        print(f'chat_id already exists for user: {user_with_bot_key_qs[0]}')
                        return False
            else:
                print(f'chat_id already exists for user: {user_with_such_chat_id_qs[0]}')
                return False

        except Exception as e:
            print(f'error activation user : {e.args}')

    # выцепляем по паттерну regex команду активации /start xxxxxx
    def get_bot_link_key(self, text):
        link_pattern = '^/start.([0-9a-z]{10})$'
        if re.search(link_pattern, text):
            return re.search(link_pattern, text).group(1)
        else:
            return None

    # выцепляем команду типа /start xxxxxxx
    def bot_authenticate(self, cmd, chat_id):
        try:
            bot_link_key = self.get_bot_link_key(cmd)
            if bot_link_key:
                if self.verify_bot_key(bot_link_key, chat_id):
                    self.bot.send_message(chat_id=chat_id, text=f'Активация пройдена успешно.')
                    # self.display_start(chat_id=chat_id, message='/start')
                    return True
                else:
                    self.bot.send_message(chat_id=chat_id,
                                          text=f'Ошибка активации, выполните генерацию ссылки повторно.')
                    return False

        except Exception as e:
            print(f'auth_cmd error: {e.args}')

    # returns true if any one of users task has dateTimeEdit field is not Null
    def is_bot_edit_dt_mode(self, current_user):
        task_qs = Task.objects.filter(task_user=current_user, dateTimeEdit__isnull=False)
        if task_qs.exists():
            return task_qs[0].tid
        return 0

    # returns true if any one of users task has text_edit == true
    def is_bot_edit_text_mode(self, current_user):
        task_qs = Task.objects.filter(task_user=current_user, text_edit=True)
        if task_qs.exists():
            return task_qs[0].tid
        return 0

    # returns true if any one of users taskfolder has title_edit == true
    def is_bot_edit_title_mode(self, current_user):
        taskfolder_qs = TaskFolder.objects.filter(task_folder_user=current_user, title_edit=True)
        if taskfolder_qs.exists():
            return taskfolder_qs[0].fid
        return 0

    # sets new text to selected task quits edit mode
    def set_task_text(self, chat_id, edit_task_id, cmd):
        # cmd is text of the task
        # get task object put new text and clear text_edit flag, save task
        task = Task.objects.get(tid=edit_task_id)
        task.text = cmd
        task.text_edit = False
        task.save()
        self.send_message(chat_id, f"Текст задачки {task.id} успешно введен!")

    # sets new text to selected task quits edit mode
    def set_taskfolder_title(self, chat_id, edit_taskfolder_id, cmd):
        # cmd is text of the taskfolder
        # get taskfolder object put new text and clear title_edit flag, save taskfolder
        taskfolder = TaskFolder.objects.get(fid=edit_taskfolder_id)
        taskfolder.title = cmd
        taskfolder.title_edit = False
        taskfolder.save()
        self.send_message(chat_id, f"Текст списка {taskfolder.id} успешно введен!")

    # sets new dateTime to selected task
    def set_task_dt(self, chat_id, edit_task_id, text):
        task = Task.objects.get(tid=edit_task_id)
        # check if we have time 'xx xx' for new task which needs to be set
        link_pattern = r'^([а-яА-ЯёЁ/a-zA-Z_0-9]+) *([а-яА-ЯёЁ/a-zA-Z_0-9]*)'

        if re.search(link_pattern, text):
            if re.search(link_pattern, text).group(2):
                # group1 - hour #group2 - minute

                _hour = re.search(link_pattern, text).group(1)
                _min = re.search(link_pattern, text).group(2)
                # validate hour minute
                if _hour.isdigit() and _min.isdigit():
                    task_hour = int(_hour)
                    task_min = int(_min)

                    if 60 > task_min >= 0 and 24 > task_hour >= 0:
                        # set dateTime to a task here
                        # first collect dateTimeEdit date + hour + min
                        # set full date (aware)
                        year = str(task.dateTimeEdit).split(sep=':')[2]
                        month = str(task.dateTimeEdit).split(sep=':')[1]
                        day = str(task.dateTimeEdit).split(sep=':')[0]

                        date_time = datetime.datetime(year=int(year), month=int(month), day=int(day),
                                                      hour=task_hour,
                                                      minute=task_min)

                        task.dateTime = make_aware(date_time, timezone=task.task_user.tz)

                        self.send_message(chat_id=chat_id,
                                          text=f'Время задачки id={task.id} установлено {date_time.strftime("%d.%m.%Y %H:%M")}')
                    else:
                        self.send_message(chat_id=chat_id,
                                          text=f'Ошибка! Время задачки id={task.id} не установлено ')

                    # set dateTime
                    # set dateTimeEdit field to None
                    task.dateTimeEdit = None
                    task.save()
                    return True
        return False

    # handle simple bot commands
    def handle(self, cmd, chat_id, current_user):
        # check if we have any edited task fileds - text or dateTime
        edit_text_task_id = self.is_bot_edit_text_mode(current_user)

        if edit_text_task_id:
            # found task in text edit mode (text_edit == true)
            self.set_task_text(chat_id, edit_text_task_id, cmd)
            return

        edit_dt_task_id = self.is_bot_edit_dt_mode(current_user)

        if edit_dt_task_id:
            # found task dateTimeEdit is Date is set (notNull)
            self.set_task_dt(chat_id, edit_dt_task_id, cmd)
            return

        edit_taskfolder_id = self.is_bot_edit_title_mode(current_user)

        if edit_taskfolder_id:
            # found taskfolder in text edit mode (title_edit = true)
            self.set_taskfolder_title(chat_id, edit_taskfolder_id, cmd)
            return

        # command (default) mode
        bot_handler = BotHandler(chat_id, cmd, current_user, self.bot)

        # pattern:function
        cmd_pattern = self.search_handler_for_cmd(cmd)
        # print(f'cmd {cmd}, pat {cmd_pattern}')

        functions = {
            '/start': bot_handler.display_start,
            'Календарь': bot_handler.get_calendary,
            'Показать все': bot_handler.show_all,
            'Задачи': bot_handler.get_tasks,
            'Создать задачу': bot_handler.create_new_task,
            'Списки': bot_handler.get_task_folders,
            'Создать список': bot_handler.create_new_taskfolder,
            'Выход': bot_handler.log_out_bot,
            'Делаю': bot_handler.get_bot_dummy_func,
            'Срочно': bot_handler.get_tasks_0_priority,
            'Важно': bot_handler.get_tasks_1_priority,
            'Желательно': bot_handler.get_tasks_2_priority,
            'Жду': bot_handler.get_tasks_3_priority,
            'Привычки': bot_handler.get_bot_dummy_func,
            'Помощь': bot_handler.get_bot_dummy_func,
            'Основное меню': bot_handler.display_start,
        }

        print(f'raw cmd: {cmd}, cmd_pattern (function command): {cmd_pattern}')
        functions.get(cmd_pattern, bot_handler.unknown_function)()

    # search callback message for method name which goes as func_name:args:args...
    # func name must be as regex pattern below...
    # source calendar_1.8034: returns match calendar_1
    def search_handler_for_callback(self, text):
        link_pattern = r'^([a-z_0-9]+).*\d*:'
        if re.search(link_pattern, text):
            return re.search(link_pattern, text).group(1)
        else:
            return None

    # search cmd message for method name which goes as func_name word to avoid emojis!!!.
    # func name must be as regex pattern below...
    def search_handler_for_cmd(self, text):
        link_pattern = r'^([а-яА-ЯёЁ/a-zA-Z_0-9]+) *([а-яА-ЯёЁ/a-zA-Z_0-9]*)'
        if re.search(link_pattern, text):
            if re.search(link_pattern, text).group(2):
                return re.search(link_pattern, text).group(1) + ' ' + re.search(link_pattern, text).group(2)
            return re.search(link_pattern, text).group(1)
        else:
            return None

    # handle bot commands made from inline tools
    def callback_handle(self, chat_id, current_user, callback_data):
        bot_cb_handler = BotCbHandler(chat_id, current_user, callback_data, self.bot)

        callback_data_pattern = self.search_handler_for_callback(callback_data)

        functions = {'calendar': bot_cb_handler.calendar_button_handler,
                     'task_folder': bot_cb_handler.taskfolder_button_handler,
                     'logout': bot_cb_handler.confirm_log_out,
                     'show_task': bot_cb_handler.show_task,
                     'predict': bot_cb_handler.predict,
                     'create_new_task': bot_cb_handler.new_task,
                     'create_new_taskfolder': bot_cb_handler.new_taskfolder,
                     'display_start': bot_cb_handler.display_start,
                     'set_task_dt': bot_cb_handler.set_task_dt_first,
                     'calendar_1': bot_cb_handler.set_task_dt_date,
                     'set_task_text': bot_cb_handler.set_task_text,
                     'del_task_confirm': bot_cb_handler.del_task_confirm,
                     'del_task': bot_cb_handler.del_task,
                     'enable_notify': bot_cb_handler.enable_notify,
                     'del_taskfolder': bot_cb_handler.del_taskfolder,
                     'del_taskfolder_confirm': bot_cb_handler.del_taskfolder_confirm,
                     'set_taskfolder_title': bot_cb_handler.set_taskfolder_title,
                     'remove_from_taskfolder_confirm': bot_cb_handler.remove_from_taskfolder_confirm,
                     'remove_from_taskfolder': bot_cb_handler.remove_from_taskfolder,
                     'add_to_taskfolder': bot_cb_handler.add_to_taskfolder,
                     'add_to_taskfolder_confirm_1': bot_cb_handler.add_to_taskfolder_confirm_1,
                     'add_to_taskfolder_confirm_2': bot_cb_handler.add_to_taskfolder_confirm_2,
                     'get_tasks_more': bot_cb_handler.get_tasks_more,
                     'get_tasks_more_priority': bot_cb_handler.get_tasks_more_priority,
                     'get_tasks_more_date': bot_cb_handler.get_tasks_more_date,
                     'get_tasks_more_folder': bot_cb_handler.get_tasks_more_folder,
                     }

        print(
            f'raw callback: {callback_data}, callback_data_pattern (call_back function command): {callback_data_pattern}')
        functions.get(callback_data_pattern, bot_cb_handler.unknown_function)()

    def send_message(self, chat_id, text, reply_markup=None):
        self.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)

    def answer_callback_query(self, callback_query_id):
        self.bot.answer_callback_query(callback_query_id=callback_query_id)

