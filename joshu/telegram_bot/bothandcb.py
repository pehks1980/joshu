import datetime
import re

import telebot_calendar
from emoji import emojize
from joshuAPI.models import JoshuUser, Task, TaskFolder
from telebot import types

from joshu import settings
from .bothand import BotHandler
from .prediction import ChartBot
from .utility import text_massage_about_the_task

BOT_TOKEN = settings.BOT_TOKEN
# Пагинатор и кнопка еще количество задачек на 1 страничке
BOT_TASKS_PER_PAGE = 3

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


# class for callback handlers
class BotCbHandler:

    def __init__(self, chat_id, current_user, callback_data, bot):
        self.bot = bot
        self.callback_data = callback_data
        self.chat_id = chat_id
        self.current_user = current_user

    # обработка кнопки меню Календарь (после выбора даты)
    def calendar_button_handler(self):
        # BOT_TASKS_PER_PAGE = 3
        year = str(self.callback_data).split(sep=':')[2]
        month = str(self.callback_data).split(sep=':')[3]
        day = str(self.callback_data).split(sep=':')[4]

        date = datetime.date(year=int(year), month=int(month), day=int(day))
        self.bot.send_message(
            chat_id=self.chat_id,
            text=f'Выбрана дата: {date.strftime("%d.%m.%Y")}'
        )
        current_task = Task.objects.filter(task_user=self.current_user, dateTime__isnull=False).order_by('-dateTime')
        current_task_list = []

        if current_task.exists():
            for item_task in current_task:
                local_dateTime = item_task.dateTime.astimezone(item_task.task_user.tz)

                if local_dateTime.strftime("%d.%m.%Y") == date.strftime("%d.%m.%Y"):
                    current_task_list.append(item_task)

            if current_task_list:
                self.bot.send_message(chat_id=self.chat_id, text=f'В этот день существует задач: {len(current_task_list)} ')
                # self.get_tasks_paged(current_task_list, 0, BOT_TASKS_PER_PAGE, len(current_task_list))
                self.get_tasks_paged(current_task_list, 0, BOT_TASKS_PER_PAGE, len(current_task_list),
                                     cb_func='get_tasks_more_date', date=f'{year}:{month}:{day}')
            else:
                markup = types.InlineKeyboardMarkup()
                markup.row(types.InlineKeyboardButton(f'В меню', callback_data=f'display_start:'))
                self.bot.send_message(chat_id=self.chat_id, text='Нет задач на выбранную дату', reply_markup=markup)

        print(f'chat_id {self.chat_id}, cb_message= {self.callback_data}')

    # Обработка кнопки Списки
    def taskfolder_button_handler(self):
        # get folder by fid!
        fid = str(self.callback_data).split(sep=':')[1]
        current_folder = TaskFolder.objects.filter(task_folder_user=self.current_user, fid=fid)

        if current_folder.exists():
            # cубменю списка
            self.submenu_taskfolder_opts(current_folder[0])
            # задачки из этого списка
            current_tasks = Task.objects.filter(task_user=self.current_user,
                                                folderId=current_folder[0].id).order_by('-dateTime')
            if current_tasks:
                current_task_co = current_tasks.count()
                self.bot.send_message(chat_id=self.chat_id,
                                    text=f'задач в списке "{current_folder[0].title}": {current_task_co}')
                self.get_tasks_paged(current_tasks, 0, BOT_TASKS_PER_PAGE, current_task_co,
                                     cb_func='get_tasks_more_folder', fid=fid)
            else:
                self.bot.send_message(chat_id=self.chat_id, text=f'В списке "{current_folder[0].title}" нет задач')
            # put submenu opts for taskfolder below

        else:
            self.bot.send_message(chat_id=self.chat_id, text=f'список отсуствует')

    # внести задачку в список
    def add_to_taskfolder(self):
        chat_id = self.chat_id
        current_user = self.current_user
        tid = str(self.callback_data).split(sep=':')[1]

        current_task_folder = TaskFolder.objects.filter(task_folder_user=current_user)
        if current_task_folder:
            # current_task_cnt = current_task_folder.count()
            self.bot.send_message(chat_id=chat_id, text=f'Добавление задачки в список')

            markup = types.InlineKeyboardMarkup()
            for item_task_folder in current_task_folder:
                markup.add(types.InlineKeyboardButton(f'{item_task_folder.title}',
                                                      callback_data=f'add_to_taskfolder_confirm_1:{tid}:{str(item_task_folder.fid)}'))

            self.bot.send_message(chat_id=chat_id, text='Выберите список:', reply_markup=markup)
        else:
            self.bot.send_message(chat_id=chat_id, text=f'Список Папок пуст')

    # внести задачку в список (подтверждение)
    def add_to_taskfolder_confirm_1(self):
        tid = str(self.callback_data).split(sep=':')[1]
        fid = str(self.callback_data).split(sep=':')[2]
        # task = Task.objects.get(tid=tid)
        taskfolder = TaskFolder.objects.get(fid=fid)
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton(f'Подтвердить добавить задачку в список: {taskfolder.title}',
                                       callback_data=f'add_to_taskfolder_confirm_2:{tid}:{fid}'))

        self.bot.send_message(chat_id=self.chat_id, text=f'Выберите действие:', reply_markup=markup)

    # внести задачку в список (добавление после подтверждения)
    def add_to_taskfolder_confirm_2(self):
        tid = str(self.callback_data).split(sep=':')[1]
        fid = str(self.callback_data).split(sep=':')[2]
        task = Task.objects.get(tid=tid)
        taskfolder = TaskFolder.objects.get(fid=fid)
        # задает соотвествие id у фолдера - уст. связь 'фолдер - таск'
        task.folderId = taskfolder.id
        task.save()
        self.bot.send_message(chat_id=self.chat_id, text=f'Задачка успешно добавлена в список {taskfolder.title}.')

    # Обработка кнопки подтверждения выхода
    def confirm_log_out(self):
        JoshuUser.clr_telegram_chat_id(self.current_user)
        self.current_user.save()
        self.bot.send_message(chat_id=self.chat_id, text=f'Пользователь удален из чатбота.')

    # отключение уведомлений
    def task_notify_off(self):
        tid = str(self.callback_data).split(sep=':')[1]
        task = Task.objects.get(tid=tid)
        if task:
            task.enabled = False
            task.save(update_fields=['enabled'])
            self.bot.send_message(chat_id=self.chat_id, text=f'Уведомление задачи id={task.id} выключено.')
        else:
            self.bot.send_message(chat_id=self.chat_id, text=f'Запись о задаче {tid} не найдена')

    # обработка 'умной' кнопки вкл выкл уведомлений задачки
    def enable_notify(self):
        tid = str(self.callback_data).split(sep=':')[1]
        task = Task.objects.get(tid=tid)
        flag = str(self.callback_data).split(sep=':')[2]  # '1' - enable '0' - disable

        if task:
            if flag == '1':
                # enable_notifications
                task.enabled = True
                self.bot.send_message(chat_id=self.chat_id, text=f'Уведомления id={task.id} включены.')
            else:
                # disable_notifications
                task.enabled = False
                self.bot.send_message(chat_id=self.chat_id, text=f'Уведомления id={task.id} выключены.')

            task.save(update_fields=['enabled'])
        else:
            self.bot.send_message(chat_id=self.chat_id, text=f'Запись о задаче {tid} не найдена')

    # удаление задачки confirmation first
    def del_task_confirm(self):
        tid = str(self.callback_data).split(sep=':')[1]
        task = Task.objects.get(tid=tid)
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton(f'Подтвердить удаление',
                                       callback_data=f'del_task:{task.tid}'))

        self.bot.send_message(chat_id=self.chat_id, text=f'Удаление задачи id={task.id}:', reply_markup=markup)

    # удаление Списка(Папки) confirmation first
    def del_taskfolder_confirm(self):
        fid = str(self.callback_data).split(sep=':')[1]
        taskfolder = TaskFolder.objects.get(fid=fid)
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton(f'Подтвердить удаление',
                                       callback_data=f'del_taskfolder:{taskfolder.fid}'))

        self.bot.send_message(chat_id=self.chat_id, text=f'Удаление списка id={taskfolder.id}:', reply_markup=markup)

    # удаление Cписка(Папки) по fid
    def del_taskfolder(self):
        fid = int(self.callback_data.split(sep=':')[1])
        taskfolder = TaskFolder.objects.get(fid=fid)

        if taskfolder:
            # get tasks with such id (of this user!!)
            tasks = Task.objects.filter(task_user=self.current_user, folderId=taskfolder.id)
            if tasks:
                for task in tasks:
                    # for every task which was in that folder set folderId = 0 (no folder state)
                    task.folderId = 0
                    task.save()
                # delete folder finally
                taskfolder.delete()
                self.bot.send_message(chat_id=self.chat_id, text=f'Cписок успешно удален.')

    # удаление задачки по tid
    def del_task(self):
        tid = str(self.callback_data).split(sep=':')[1]
        task = Task.objects.get(tid=tid)
        task.delete()
        self.bot.send_message(chat_id=self.chat_id, text=f'Задачка успешно удалена.')

    # убрать задачку из списка (подтвердить)
    def remove_from_taskfolder_confirm(self):
        tid = str(self.callback_data).split(sep=':')[1]
        task = Task.objects.get(tid=tid)
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton(f'Подтвердить удаление из списка',
                                       callback_data=f'remove_from_taskfolder:{task.tid}'))

        self.bot.send_message(chat_id=self.chat_id, text=f'Удаление задачи id={task.id} из списка:',
                              reply_markup=markup)

    # убрать задачку из списка
    def remove_from_taskfolder(self):
        tid = str(self.callback_data).split(sep=':')[1]
        task = Task.objects.get(tid=tid)
        task.folderId = 0
        task.save()
        self.bot.send_message(chat_id=self.chat_id, text=f'Задачка успешно удалена из списка')

    # просмотр задачки
    def show_task(self):
        tid = str(self.callback_data).split(sep=':')[1]
        task = Task.objects.select_related().get(tid=tid)
        if task:
            text = f'Текст задачи : {task.text}\n'

            dct_choice = [
                {'val': '0', 'msg': 'Срочно'},
                {'val': '1', 'msg': 'Важно'},
                {'val': '2', 'msg': 'Желательно'},
                {'val': '3', 'msg': 'Жду'},
            ]

            priority_text = list(filter(lambda x: x['val'] == task.priority, dct_choice))

            text += f'Приоритет : {priority_text[0]["msg"]}\n'

            # get task folder title if task.folderId != 0
            taskfolder = None
            if task.folderId != 0:
                try:
                    taskfolder = TaskFolder.objects.get(task_folder_user=self.current_user, id=task.folderId)
                    text += f'Список: {taskfolder.title}\n'
                except:
                    text += f'Список: Не найден\n'
            else:
                text += f'Список: Не задан\n'

            if task.dateTime != None:

                text += f'Cрок исполнения: {task.dateTime.astimezone(task.task_user.tz)}\n'

                if task.overdue:
                    text += ' Cтатус - просрочена '
                else:
                    text += ' Cтатус - ожидание исполнения '

                if task.enabled:
                    text += ' Уведомления - вкл. \n'
                else:
                    text += ' Уведомления - выкл. \n'

            text += text_massage_about_the_task(task)

            self.bot.send_message(chat_id=self.chat_id,
                                  text=text)

            self.submenu_task_opts(task, taskfolder)
        else:
            self.bot.send_message(chat_id=self.chat_id, text=f'Запись о задаче {tid} не найдена')

    # подменю что можно сделать с задачкой
    def submenu_task_opts(self, task, taskfolder=None):
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton(f'задать текст задачке id={task.id}',
                                       callback_data=f'set_task_text:{task.tid}'))
        markup.add(
            types.InlineKeyboardButton(f'задать срок задачке id={task.id}', callback_data=f'set_task_dt:{task.tid}'))
        markup.add(
            types.InlineKeyboardButton(f'удалить задачку id={task.id}', callback_data=f'del_task_confirm:{task.tid}'))

        if task.enabled:
            markup.add(
                types.InlineKeyboardButton(f'выключить уведомления id={task.id}',
                                           callback_data=f'enable_notify:{task.tid}:0'))
        else:
            markup.add(
                types.InlineKeyboardButton(f'включить уведомления id={task.id}',
                                           callback_data=f'enable_notify:{task.tid}:1'))
        if taskfolder:
            markup.add(
                types.InlineKeyboardButton(f'удалить задачку id={task.id} из списка {taskfolder.title}',
                                           callback_data=f'remove_from_taskfolder_confirm:{task.tid}'))
        else:
            markup.add(
                types.InlineKeyboardButton(f'добавить задачку id={task.id} в список',
                                           callback_data=f'add_to_taskfolder:{task.tid}'))

        self.bot.send_message(chat_id=self.chat_id, text='Выберите действие:', reply_markup=markup)

    # подменю что можно сделать со списком папкой
    def submenu_taskfolder_opts(self, taskfolder):
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton(f'задать текст списку id={taskfolder.id}',
                                       callback_data=f'set_taskfolder_title:{taskfolder.fid}'))
        markup.add(
            types.InlineKeyboardButton(f'удалить список id={taskfolder.id}',
                                       callback_data=f'del_taskfolder_confirm:{taskfolder.fid}'))

        self.bot.send_message(chat_id=self.chat_id, text='Выберите действие:', reply_markup=markup)

    # cервисная функция вызывается если не обнаружено никаких колбек команд
    def unknown_function(self):
        self.bot.send_message(chat_id=self.chat_id, text='Я получил нажатие, но не смог найти обработчик')

    # обработка кнопки меню в чат боте
    def display_start(self):
        markup = types.ReplyKeyboardMarkup()
        markup = BotHandler.display_menu(markup)
        self.bot.send_message(
            chat_id=self.chat_id,
            text=f'Выберите опцию {e_option}',
            reply_markup=markup
        )

    # функция Чарт бота (болталки)
    def predict(self):
        text = str(self.callback_data).split(sep=':')[1]
        chart_bot = ChartBot()
        answer = chart_bot.create_answer(text)
        self.bot.send_message(chat_id=self.chat_id, text=answer)

    # функция кнопки Еще пагинатор задачек при нажатии на Задачи
    def get_tasks_more(self):
        current_user = self.current_user
        start_idx = int(self.callback_data.split(sep=':')[1])
        page_length = int(self.callback_data.split(sep=':')[2])
        # get all tasks
        current_task = Task.objects.filter(task_user=current_user).order_by('-dateTime')
        self.get_tasks_paged(current_task, start_idx, page_length, current_task.count())
        # функция кнопки Еще пагинатор задачек при нажатии на Задачи

    # функция кнопки Еще пагинатор задачек при нажатии на Приоритет
    def get_tasks_more_priority(self):
        current_user = self.current_user
        start_idx = int(self.callback_data.split(sep=':')[1])
        page_length = int(self.callback_data.split(sep=':')[2])
        priority = int(self.callback_data.split(sep=':')[3])
        # get all tasks
        current_task = Task.objects.filter(task_user=current_user, priority=priority).order_by('-dateTime')
        # current_task = Task.objects.filter(task_user=current_user).order_by('-dateTime')
        self.get_tasks_paged(current_task, start_idx, page_length,
                             current_task.count(), cb_func='get_tasks_more_priority', priority=priority)

    # функция кнопки Еще пагинатор задачек при нажатии на Список
    def get_tasks_more_folder(self):
        current_user = self.current_user
        start_idx = int(self.callback_data.split(sep=':')[1])
        page_length = int(self.callback_data.split(sep=':')[2])
        fid = int(self.callback_data.split(sep=':')[3])
        # get folder and extract tasks from this folder
        current_folder = TaskFolder.objects.filter(task_folder_user=current_user, fid=fid)
        if current_folder.exists():
            # print tasks which is in this folder
            current_task = Task.objects.filter(task_user=current_user,
                                               folderId=current_folder[0].id).order_by('-dateTime')
            self.get_tasks_paged(current_task, start_idx, page_length,
                                 current_task.count(), cb_func='get_tasks_more_folder', fid=fid)

    # функция кнопки Еще пагинатор задачек при нажатии на Дату в календаре
    def get_tasks_more_date(self):
        current_user = self.current_user
        # сперва берем как обычно индекс и длину странички
        start_idx = int(self.callback_data.split(sep=':')[1])
        page_length = int(self.callback_data.split(sep=':')[2])
        # берем дату
        year = str(self.callback_data).split(sep=':')[3]
        month = str(self.callback_data).split(sep=':')[4]
        day = str(self.callback_data).split(sep=':')[5]
        # дата в формате для сравнения
        date = datetime.date(year=int(year), month=int(month), day=int(day))
        # делаем нужную выборку с учетом пагинатора и даты задачек
        current_task = Task.objects.filter(task_user=current_user, dateTime__isnull=False).order_by('-dateTime')
        current_task_list = []

        if current_task.exists():
            for item_task in current_task:
                local_dateTime = item_task.dateTime.astimezone(item_task.task_user.tz)

                if local_dateTime.strftime("%d.%m.%Y") == date.strftime("%d.%m.%Y"):
                    current_task_list.append(item_task)

            if current_task_list:
                # self.bot.send_message(chat_id=self.chat_id, text=f'В этот день существует задач: {len(current_task_list)} ')
                self.get_tasks_paged(current_task_list, start_idx, page_length, len(current_task_list),
                                     cb_func='get_tasks_more_date', date=f'{year}:{month}:{day}')

    # выводит пользователю список с пагинатором, список хранится в current_task
    # strart_idx page_length - параметры для пагинатора индекс и длина странички
    # cb_func - имя функции колбека, которую подсунуть в кнопку, также если надо приоритет и дата
    # что нажали то и будет пагинироваться кнопкой Еще
    def get_tasks_paged(self, current_task, start_idx, page_length, current_task_cnt
                        , cb_func='get_tasks_more', priority=None, date='', fid=None):
        chat_id = self.chat_id
        # get tasks only for this page
        current_task_list = current_task[start_idx:start_idx + page_length]
        if current_task_list:
            # current_task_list_co = len(current_task_list)
            current_task_co = current_task_cnt  # .count()
            # self.bot.send_message(chat_id=chat_id, text=f'Еще Ваших задач: {current_task_list_co}')
            markup = types.InlineKeyboardMarkup()

            # выводим  page_length первых задач
            limit = page_length
            for item_task in current_task_list:
                limit -= 1

                self.bot.send_message(
                    chat_id=chat_id,
                    text=text_massage_about_the_task(item_task)  # выводим текст про задачу и срок исполнения
                )
                markup.add(
                    types.InlineKeyboardButton(f'{item_task.id}', callback_data=f'show_task:{str(item_task.tid)}'),
                    row_width=5)
                if limit == 0:
                    break

            if start_idx + page_length < current_task_co:
                if date != '':
                    # в случае пагинатора кнопки даты календаря
                    markup.row(types.InlineKeyboardButton(f'В меню', callback_data='display_start:'),
                               types.InlineKeyboardButton(
                                   f'Еще', callback_data=f'{cb_func}:'  # get_tasks_more_date
                                                         f'{str(start_idx + page_length)}:'
                                                         f'{str(page_length)}:'
                                                         f'{str(date)}'))  # date='2021:2:25'

                elif priority is not None:
                    # в случае пагинатора кнопки приоритета
                    markup.row(types.InlineKeyboardButton(f'В меню', callback_data='display_start:'),
                               types.InlineKeyboardButton(
                                   f'Еще', callback_data=f'{cb_func}:'  # get_tasks_more_priority
                                                         f'{str(start_idx + page_length)}:'
                                                         f'{str(page_length)}:'
                                                         f'{str(priority)}'))
                elif fid is not None:
                    # в случае пагинатора кнопки задачи
                    markup.row(types.InlineKeyboardButton(f'В меню', callback_data='display_start:'),
                               types.InlineKeyboardButton(
                                   f'Еще', callback_data=f'{cb_func}:'  # get_tasks_more_folder
                                                         f'{str(start_idx + page_length)}:'
                                                         f'{str(page_length)}:'
                                                         f'{str(fid)}'))
                elif priority is None:
                    # в случае пагинатора кнопки задачи
                    markup.row(types.InlineKeyboardButton(f'В меню', callback_data='display_start:'),
                               types.InlineKeyboardButton(
                                   f'Еще', callback_data=f'{cb_func}:'  # get_tasks_more
                                                         f'{str(start_idx + page_length)}:'
                                                         f'{str(page_length)}'))

            else:
                markup.row(types.InlineKeyboardButton(f'В меню', callback_data='display_start:'))

            self.bot.send_message(chat_id=chat_id, text='Выберите задачу:', reply_markup=markup)
        else:
            self.bot.send_message(chat_id=chat_id, text=f'Список задач пуст')

    # Функция 1 ввода времени срока задачки dateTime - выводит календарь для выбора даты
    def set_task_dt_first(self):
        tid = str(self.callback_data).split(sep=':')[1]
        chat_id = self.chat_id
        # set tid as suffix (_1) in name for calendar so it will be used later in set_task_dt_date()
        self.bot.send_message(
            chat_id,
            text="Пожалуйста, выберите дату: ",
            reply_markup=telebot_calendar.create_calendar(name=f'calendar_1.{tid}')
        )

    # Функция 2 ввода времени срока задачки dateTime - получает выбранную в календаре дату и просит ввести время час мин
    def set_task_dt_date(self):
        # get tid, date from callback data

        tid = re.search(r'^[a-z_0-9]+.(\d+):', self.callback_data).group(1)

        year = str(self.callback_data).split(sep=':')[2]
        month = str(self.callback_data).split(sep=':')[3]
        day = str(self.callback_data).split(sep=':')[4]

        date = datetime.date(year=int(year), month=int(month), day=int(day))
        self.bot.send_message(
            chat_id=self.chat_id,
            text=f'Выбрана дата: {date.strftime("%d.%m.%Y")}'
        )
        try:
            task = Task.objects.get(task_user=self.current_user, tid=tid)
        except Task.DoesNotExist:
            task = None

        if task:
            task.dateTimeEdit = date.strftime("%d:%m:%Y")
            task.save()
            self.bot.send_message(
                chat_id=self.chat_id,
                text=f'Введите время: час мин'
            )

    # функция для ввода текста задачки
    def set_task_text(self):
        tid = str(self.callback_data).split(sep=':')[1]
        chat_id = self.chat_id
        try:
            task = Task.objects.get(task_user=self.current_user, tid=tid)
        except Task.DoesNotExist:
            task = None

        if task:
            self.bot.send_message(
                chat_id,
                text=f"Пожалуйста, введите текст задачки {task.id} "
            )
            task.text_edit = True
            task.save()

    # функция для ввода текста списка
    def set_taskfolder_title(self):
        fid = str(self.callback_data).split(sep=':')[1]
        chat_id = self.chat_id
        try:
            taskfolder = TaskFolder.objects.get(task_folder_user=self.current_user, fid=fid)
        except TaskFolder.DoesNotExist:
            taskfolder = None

        if taskfolder:
            self.bot.send_message(
                chat_id,
                text=f"Пожалуйста, введите название списка {taskfolder.id} "
            )
            taskfolder.title_edit = True
            taskfolder.save()

    # функция создания новой задачки
    def new_task(self):
        task_priority = str(self.callback_data).split(sep=':')[1]
        # 1 check if task id is in use already
        # get the latest id
        task_qs = Task.objects.filter(task_user=self.current_user).order_by('-id')

        if task_qs.exists():
            # check if id is not used should be here, BUT now we just add + 1 to latest id
            task_id = task_qs[0].id + 1
        else:
            # no tasks yet create task id = 1
            task_id = 1

        # task_text = f" Текст задачки id={task_id} приоритетом {task_priority}"
        task_text = f" Задайте поле текста задачки id={task_id} приоритетом {task_priority}"

        new_task = Task(
            id=task_id,
            text=task_text,
            priority=task_priority,
            folderId=0,
            status='2',
            task_user=self.current_user
        )

        new_task.save()
        self.bot.send_message(chat_id=self.chat_id, text='Задача успешно поставлена')
        self.submenu_task_opts(new_task)

    # функция создания нового списка
    def new_taskfolder(self):
        taskfolder_color_index = str(self.callback_data).split(sep=':')[1]
        tf_color_list = ['red', 'yellow', 'green']

        # 1 check if taskfolder id is in use already
        # get the latest id
        taskfolder_qs = TaskFolder.objects.filter(task_folder_user=self.current_user).order_by('-id')

        if taskfolder_qs.exists():
            # check if id is not used should be here, BUT now we just add + 1 to latest id
            taskfolder_id = taskfolder_qs[0].id + 1
        else:
            # no tasks yet create taskfolder id = 1
            taskfolder_id = 1

        # task_text = f" Текст задачки id={task_id} приоритетом {task_priority}"
        taskfolder_title = f" Новый список id={taskfolder_id} "

        new_taskfolder = TaskFolder(
            id=taskfolder_id,
            title=taskfolder_title,
            color=tf_color_list[int(taskfolder_color_index)],
            task_folder_user=self.current_user
        )

        new_taskfolder.save()
        self.bot.send_message(chat_id=self.chat_id, text='Новый список успешно создан.')
        self.submenu_taskfolder_opts(new_taskfolder)
