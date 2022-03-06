import datetime
import hashlib
import random
from datetime import timedelta

from django.db import models
from django.dispatch import receiver
from django.db.models.signals import pre_save

from django.contrib.auth.models import (
    AbstractBaseUser,
    PermissionsMixin,
    BaseUserManager)

from django.conf import settings
from django.utils.timezone import now

from django.db.models.signals import post_save
from django.dispatch import receiver

from timezone_field import TimeZoneField


class UserManager(BaseUserManager):

    def create_user(self,
                    uid,
                    is_active=True,
                    is_staff=False,
                    is_admin=False,
                    email=None,
                    password=None):
        if not uid:
            raise ValueError('Users must have an uid')
        user = self.model(uid=uid)
        user.active = is_active
        user.staff = is_staff
        user.admin = is_admin
        user.email = email
        user.set_password(password)
        user = user.save(using=self._db)
        return user

    def create_staffuser(self, uid, email, password):
        """
        Creates and saves a staff user with the given email and password.
        """
        user = self.create_user(
            uid=uid,
            email=email,
            password=password,
            is_staff=True
        )
        return user

    def create_superuser(self, uid, email, password):
        """
        Creates and saves a superuser with the given email and password.
        """
        user = self.create_user(
            uid=uid,
            email=email,
            password=password,
            is_staff=True,
            is_admin=True
        )
        return user


class JoshuUser(AbstractBaseUser, PermissionsMixin):
    uid = models.CharField(
        verbose_name='uid identifier',
        max_length=255,
        unique=True,
        null=True,
    )
    password = models.CharField(max_length=128, blank=True)
    displayName = models.CharField(max_length=100, blank=True)
    email = models.EmailField(max_length=150, blank=True)
    active = models.BooleanField(default=True)
    staff = models.BooleanField(default=False)  # a admin user; non super-user
    admin = models.BooleanField(default=False)  # a superuser
    telegram_ch_admin = models.BooleanField(default=False)  # a admin user telegram channel

    created_at = models.DateTimeField(auto_now_add=True, auto_now=False)
    updated_at = models.DateTimeField(auto_now_add=False, auto_now=True)

    task_sinhro = models.DateTimeField(null=True, default='1970-01-01T00:00:00+03:00',
                                       verbose_name="Последняя дата синхронизации задач")
    task_folder_sinhro = models.DateTimeField(null=True, default='1970-01-01T00:00:00+03:00',
                                              verbose_name="Последняя дата синхронизации групп задач")
    chat_id = models.CharField(max_length=128, blank=True)
    # telegram auth key
    bot_link_key = models.CharField(max_length=128, blank=True)
    bot_link_key_expires = models.DateTimeField(null=True, default='1970-01-01T00:00:00+03:00',
                                                verbose_name="Дата окончания действия ссылки аутентификации на телеграм бот")
    user_time_zone = models.IntegerField(default=0, verbose_name='Сдвиг часового пояса в секундах')  # по умолч 0

    user_time_zone_character = models.BooleanField(default=True,
                                                   verbose_name='Признак положительного сдвига часового пояса для пользователя')
    # ^^^ True если признак часового пояса со знаком + ^^^
    # declare tz of user (default is set to UTC)
    tz = TimeZoneField(default='Europe/London')

    objects = UserManager()

    USERNAME_FIELD = 'uid'
    REQUIRED_FIELDS = ['email']

    def get_full_name(self):
        # The user is identified by their uid address
        return self.uid

    def get_short_name(self):
        # The user is identified by their uid address
        return self.uid

    def __str__(self):
        return self.uid

    def has_perm(self, perm, obj=None):
        # The user have a specific permission always
        return True

    def has_module_perms(self, app_label):
        # The user have permissions to view the app `app_label` always
        return True

    @staticmethod
    def gen_telegram_link(instance):
        # generate hash challenge for bot telegram (from unique field uid)
        salt = hashlib.sha1(str(random.random()).encode('utf8')).hexdigest()[:8]
        instance.bot_link_key = hashlib.sha1((instance.uid + salt).encode('utf8')).hexdigest()[6:16]
        instance.bot_link_key_expires = now() + timedelta(hours=48)
        instance.chat_id = ''

    def is_bot_link_key_expired(self):
        if now() <= self.bot_link_key_expires:
            return False
        else:
            return True

    @staticmethod
    def clr_telegram_chat_id(instance):
        # unlink telegram from api
        instance.chat_id = ''

    @property
    def is_staff(self):
        return self.staff

    @property
    def is_admin(self):
        return self.admin

    @property
    def is_active(self):
        return self.active


class TaskFolder(models.Model):
    fid = models.AutoField(primary_key=True)
    id = models.PositiveIntegerField(verbose_name='ID группы задач')
    title = models.CharField(verbose_name='Имя группы задач', max_length=50)
    color = models.CharField(verbose_name='Color', max_length=50)

    createDate = models.DateTimeField(null=True, verbose_name="Создана")
    edit = models.DateTimeField(null=True, verbose_name="Дата редактирования")

    title_edit = models.BooleanField(default=False)  # режим редактирования true - задачке вводится текст title

    task_folder_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='Cоздатель группы задач',
        on_delete=models.CASCADE,
        related_name='task_group_owner',
        to_field='uid',
        null=True
    )

    class Meta:
        verbose_name_plural = 'Названия групп задач'
        verbose_name = 'Название группы задач'
        ordering = ['title']

    def __str__(self):
        return self.title


# Напоминаем в чат - бот
# За    день = 1440
# За    час = 60
# За    10 минут = 10
# синхронизированно с TASK: PRIORITY_CHOISES 0, 1, ... index's
NOTIFY_TIMES = [1440, 60, 10, 0]  # 0 - момент наступления
# информирование когда время задачи task.dateTime наступило. (overdue = true)
# в конце информирования устанавливается флаг overdue_done = true
OVERDUE_TIMES = [5, 10, 60, 1440, 1440 * 2]


class Task(models.Model):
    tid = models.AutoField(primary_key=True)
    id = models.PositiveIntegerField(verbose_name='ID задачи')
    text = models.CharField(verbose_name='Описание задачи', max_length=200, null=True)
    PRIORITY_CHOISES = (
        ('0', 'Срочно'),
        ('1', 'Не срочно'),
        ('2', 'Совсем не срочно'),
        ('3', 'Без ограничения срока реализиции')
    )
    priority = models.CharField(
        verbose_name='Статус задачи',
        choices=PRIORITY_CHOISES,
        max_length=1,
        default=1
    )
    # Поле "dateTime" нельзя выводить в чат-бот напрямую! Только с учетом сдвига часового пояса для пользователя
    # Поле "dateTime" без изменеий отдаем только на фронт через АПИ!
    dateTime = models.DateTimeField(verbose_name='Срок исполнения задачи', max_length=50, null=True)
    folderId = models.PositiveIntegerField(verbose_name='ID группы задачи')
    task_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='Cоздатель задачи',
        on_delete=models.CASCADE,
        related_name='task_owner',
        to_field='uid',
        null=True
    )
    STATUS_CHOISES = (
        ('0', 'Выполнена'),
        ('1', 'Жду'),
        ('2', 'Создана'),
        ('3', 'На сегодня'),
        ('4', 'Повторяемая'),
    )

    status = models.CharField(
        verbose_name='Cтатус задачи',
        choices=STATUS_CHOISES,
        max_length=1,
        default=2
    )
    createDate = models.DateTimeField(null=True, verbose_name="Создана")
    edit = models.DateTimeField(null=True, verbose_name="Дата редактирования")

    shed_time = models.PositiveIntegerField(null=True, blank=True)  # in mins
    last_fired_at = models.DateTimeField(auto_now_add=True, blank=True)
    enabled = models.BooleanField(default=True)  # уведомления вкл выкл (по задачно)
    overdue = models.BooleanField(default=False)  # тру когда время задачи наступило и она уже пошла.
    overdue_done = models.BooleanField(default=False)  # тру все уведомлялки после наступления срока прошли.

    dateTimeEdit = models.CharField(verbose_name='Редактирование Срока исполнения', max_length=200, null=True)
    text_edit = models.BooleanField(default=False)  # режим редактирования true - задачке вводится текст

    class Meta:
        verbose_name_plural = 'Задачи'
        verbose_name = 'Задача'
        ordering = ['dateTime']

    def __str__(self):
        return f'{self.text[:50]}. Срок исполнения: {self.dateTime} '

    # # вычисление следующего порога уведомлений
    # def get_next_shed_time(self):
    #     for time in NOTIFY_TIMES:
    #         if self.shed_time > time:
    #             return time

    # автоматическая подстройка уведомлений на случай если время задачки меньше порога уведомления
    # (иначе будут приходить все сообщения по порядку)
    @staticmethod
    def adjust_notify_time(task_inst):
        # check current time
        # if dateTime is null - exit and do nothing
        if task_inst.dateTime is None:
            return -1
        # разница со времени срока наступления задачки
        diff_time = task_inst.dateTime - now()
        # convert secs to mins float - для более высокой точности
        diff_time_mins = float(diff_time.total_seconds() / 60)
        # print (f'diff_time={diff_time_mins}')

        if diff_time_mins < 0:
            task_inst.overdue = True
            # task is overdrawn
            # calculate next time to get next time period for event notification
            for i in range(len(OVERDUE_TIMES)):
                if abs(diff_time_mins) < OVERDUE_TIMES[i]:
                    task_inst.shed_time = OVERDUE_TIMES[i]
                    # print(f'task -shed_time={task_inst.shed_time}')
                    task_inst.overdue_done = False
                    return -1

            # it is more then biggest value
            # finish notifications
            task_inst.overdue_done = True
            return -1

        # здесь срок задачки еще не наступил
        task_inst.overdue = False
        task_inst.overdue_done = False
        # чем ниже приоритет тем меньше уведомлений 0 - все информ., ... 3 - информ только при наступлении
        for i in range(int(task_inst.priority), len(NOTIFY_TIMES)):
            if diff_time_mins > NOTIFY_TIMES[i]:
                task_inst.shed_time = NOTIFY_TIMES[i]
                # print(f'task +shed_time={task_inst.shed_time}')
                return task_inst.shed_time

        # fail safe return
        #task_inst.overdue = True
        task_inst.shed_time = 0
        # print(f'task +-shed_time={task_inst.shed_time}')
        return -1


# signal setup
# called when new task is created
@receiver(post_save, sender=Task)
def create_task_notifier(sender, instance, created, **kwargs):
    if created:
        shed_time = Task.adjust_notify_time(instance)
        instance.save()
        # print('create_shed_time=', shed_time)


# called when existed task is updated
@receiver(pre_save, sender=Task)
def update_task_notifier(sender, instance, **kwargs):
    if instance.tid:
        shed_time = Task.adjust_notify_time(instance)
        # print ('update_shed_time=',shed_time)
