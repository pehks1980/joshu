import telebot_calendar
from emoji import emojize
from joshuAPI.models import JoshuUser, Task, TaskFolder
from telebot import types

from joshu import settings
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


# class simple cmds
class BotHandler:

    def __init__(self, chat_id, cmd, current_user, bot):
        self.bot = bot
        self.cmd = cmd
        self.chat_id = chat_id
        self.current_user = current_user

    # вывод меню чат бота при старте
    @staticmethod
    def display_menu(markup):
        # markup = types.ReplyKeyboardMarkup()
        markup.add('Календарь', f'Списки {e_folder}', f'Создать список {e_folder}')
        markup.add(f'Делаю {e_calendar}')
        markup.add(f'Задачи {e_clipboard}', f'Создать задачу {e_clipboard}')
        markup.add('Показать все')
        return markup

    # вывод меню чат бота при нажатии показать все
    @staticmethod
    def display_menu_all(markup):
        # markup = types.ReplyKeyboardMarkup()
        markup.add('Календарь', 'Списки')
        markup.add(f'Делаю {e_folder}')
        markup.add(f'Задачи {e_clipboard}')
        markup.add(f'Срочно {e_redcircle}', f'Важно {e_yellowcircle}')
        markup.add(f'Желательно {e_bluecircle}', f'Жду {e_clock}')
        markup.add(f'Привычки {e_star}')
        markup.add('Основное меню')
        markup.add('Помощь', 'Выход')
        return markup

    # функция печатает меню чат бота и приветствие если /start
    def display_start(self):
        chat_id = self.chat_id
        message = self.cmd

        markup = types.ReplyKeyboardMarkup()

        markup = BotHandler.display_menu(markup)

        if message == '/start':
            # if we have chat_id print full_name of user
            user_qs = JoshuUser.objects.filter(chat_id=chat_id, active=True).order_by('-id')

            if user_qs.exists():
                markup.add(user_qs[0].displayName)
                self.bot.send_message(
                    chat_id=chat_id,
                    text=f'Приветствую {user_qs[0].displayName}!\nВыберите опцию {e_option}',
                    reply_markup=markup
                )
        else:
            self.bot.send_message(
                chat_id=chat_id,
                text=f'Приветствую вас!\nВыберите опцию {e_option}',
                reply_markup=markup
            )

    # функция выводит календарь при нажатии на кнопку меню
    def get_calendary(self):
        chat_id = self.chat_id

        self.bot.send_message(
            chat_id,
            text="Пожалуйста, выберите дату: ",
            reply_markup=telebot_calendar.create_calendar()
        )

    # функци выводит расширенное меню при нажатии 'показать все'
    def show_all(self):
        chat_id = self.chat_id

        markup = types.ReplyKeyboardMarkup()

        markup = BotHandler.display_menu_all(markup)

        self.bot.send_message(
            chat_id=chat_id,
            text=f'Выберите опцию {e_option}',
            reply_markup=markup
        )

    def get_tasks(self):
        #BOT_TASKS_PER_PAGE = 3
        chat_id = self.chat_id
        current_user = self.current_user

        current_task = Task.objects.filter(task_user=current_user).order_by('-dateTime')
        if current_task:
            current_task_co = current_task.count()
            self.bot.send_message(chat_id=chat_id, text=f'Всего Ваших задач: {current_task_co}')
            self.get_tasks_paged(current_task, 0, BOT_TASKS_PER_PAGE,
                                 current_task_co)
        else:
            self.bot.send_message(chat_id=chat_id, text=f'Список задач пуст')

    def get_tasks_0_priority(self):
        self.get_tasks_by_priority('0')

    def get_tasks_1_priority(self):
        self.get_tasks_by_priority('1')

    def get_tasks_2_priority(self):
        self.get_tasks_by_priority('2')

    def get_tasks_3_priority(self):
        self.get_tasks_by_priority('3')

    def get_tasks_by_priority(self, priority):
        #BOT_TASKS_PER_PAGE = 3
        chat_id = self.chat_id
        current_user = self.current_user
        current_task = Task.objects.filter(task_user=current_user, priority=priority).order_by('-dateTime')

        dct_choice = [
            {'val': '0', 'msg': 'Срочно'},
            {'val': '1', 'msg': 'Важно'},
            {'val': '2', 'msg': 'Желательно'},
            {'val': '3', 'msg': 'Жду'},
        ]

        priority_text = list(filter(lambda x: x['val'] == priority, dct_choice))

        if current_task:
            current_task_co = current_task.count()
            self.bot.send_message(chat_id=chat_id,
                                  text=f"Всего задач приоритетом ({priority_text[0]['msg']}): {current_task_co}")
            self.get_tasks_paged(current_task, 0, BOT_TASKS_PER_PAGE,
                                 current_task_co, cb_func='get_tasks_more_priority', priority=priority)
        else:
            self.bot.send_message(chat_id=chat_id, text=f"Список задач приоритетом ({priority_text[0]['msg']}) пуст")

    # выводит пользователю список с пагинатором, список хранится в current_task
    # strart_idx page_length - параметры для пагинатора индекс и длина странички
    # новый параметр cb_func подсовывает свое название функции колбека чтобы пагинатор работал от всех источников задач
    def get_tasks_paged(self, current_task, start_idx, page_length, current_task_cnt,
                        cb_func='get_tasks_more', priority=None):
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
            # проверям достигли дна (послед страничка пагинатора)
            if start_idx + page_length < current_task_co:
                if priority is None:
                    # в случае пагинатора кнопки задачи
                    markup.row(types.InlineKeyboardButton(f'В меню', callback_data='display_start:'),
                               types.InlineKeyboardButton(
                                   f'Еще', callback_data=f'{cb_func}:'
                                                         f'{str(start_idx + page_length)}:'
                                                         f'{str(page_length)}'))
                else:
                    # в случае пагинатора кнопки приоритета
                    markup.row(types.InlineKeyboardButton(f'В меню', callback_data='display_start:'),
                               types.InlineKeyboardButton(
                                   f'Еще', callback_data=f'{cb_func}:'
                                                         f'{str(start_idx + page_length)}:'
                                                         f'{str(page_length)}:'
                                                         f'{str(priority)}'))
            else:
                markup.row(types.InlineKeyboardButton(f'В меню', callback_data='display_start:'))

            self.bot.send_message(chat_id=chat_id, text='Выберите задачу:', reply_markup=markup)
        else:
            self.bot.send_message(chat_id=chat_id, text=f'Список задач пуст')

    def get_task_folders(self):
        chat_id = self.chat_id
        current_user = self.current_user

        current_task_folder = TaskFolder.objects.filter(task_folder_user=current_user)
        if current_task_folder:
            current_task_cnt = current_task_folder.count()
            self.bot.send_message(chat_id=chat_id, text=f'Всего списков: {current_task_cnt}')

            markup = types.InlineKeyboardMarkup()
            for item_task_folder in current_task_folder:
                markup.add(types.InlineKeyboardButton(f'{item_task_folder.title}',
                                                      callback_data=f'task_folder:{str(item_task_folder.fid)}'))

            self.bot.send_message(chat_id=chat_id, text='Выберите список:', reply_markup=markup)
        else:
            self.bot.send_message(chat_id=chat_id, text=f'Список Папок пуст')

    def log_out_bot(self):
        chat_id = self.chat_id
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(f'Подтвердить и выйти', callback_data=f'logout:'))
        self.bot.send_message(chat_id=chat_id, text='Подтвердите выход из чатбота!', reply_markup=markup)

    def notify_test(self):
        self.bot.send_message(chat_id=self.chat_id, text='notify_bot_test')

    def create_new_taskfolder(self):
        taskfolder_markup = types.InlineKeyboardMarkup()
        taskfolder_markup.add(types.InlineKeyboardButton(
            f'Красный {e_redcircle}',
            callback_data=f'create_new_taskfolder:0'
        ))
        taskfolder_markup.add(types.InlineKeyboardButton(
            f'Желтый {e_yellowcircle}',
            callback_data=f'create_new_taskfolder:1'
        ))
        taskfolder_markup.add(types.InlineKeyboardButton(
            f'Зеленый {e_greencircle}',
            callback_data=f'create_new_taskfolder:2'
        ))
        taskfolder_markup.add(types.InlineKeyboardButton(
            f'Нет {e_x}',
            callback_data=f'predict:{self.cmd}'
        ))
        self.bot.send_message(
            chat_id=self.chat_id,
            text='Задайте цвет списку',
            reply_markup=taskfolder_markup
        )

    def create_new_task(self):
        task_markup = types.InlineKeyboardMarkup()
        task_markup.add(types.InlineKeyboardButton(
            f'Да - срочно {e_redcircle}',
            callback_data=f'create_new_task:0'
        ))
        task_markup.add(types.InlineKeyboardButton(
            f'Да - важно {e_yellowcircle}',
            callback_data=f'create_new_task:1'
        ))
        task_markup.add(types.InlineKeyboardButton(
            f'Да - желательно {e_bluecircle}',
            callback_data=f'create_new_task:2'
        ))
        task_markup.add(types.InlineKeyboardButton(
            f'Да - жду {e_clock}',
            callback_data=f'create_new_task:3'
        ))
        task_markup.add(types.InlineKeyboardButton(
            f'Нет {e_x}',
            callback_data=f'predict:{self.cmd}'
        ))
        self.bot.send_message(
            chat_id=self.chat_id,
            text='Введите приоритет задачки',
            reply_markup=task_markup
        )

    def unknown_function(self):
        self.bot.send_message(chat_id=self.chat_id, text=f'Я не смог найти обработчик комманды {self.cmd}')

        chart_bot = ChartBot()
        answer = chart_bot.create_answer(self.cmd)
        self.bot.send_message(chat_id=self.chat_id,
                              text=f'Ответ ChartBot: {answer}')

    def get_bot_dummy_func(self):
        self.bot.send_message(chat_id=self.chat_id, text=f'Coming soon! {self.cmd}')
